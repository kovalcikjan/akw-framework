"""Faze 3: Cleaning + Deduplication.

Text normalization, exact/diacritics/word-order dedup, filtering.
Static diacritics map (not NFD). Canonical selection scoring (mBank pattern).
XLSX multi-sheet output + CSV for pipeline. Cluster report for audit trail.

Outputs:
  - data/interim/keywords_clean.xlsx (5 sheets: Final, All, Merged, Clusters, Summary)
  - data/interim/keywords_clean.csv (flat export for pipeline)
  - data/interim/keywords_removed.csv (dedup merges)
  - data/interim/keywords_filtered_out.csv (filtered by volume/length/blacklist)

Usage:
    python src/cleaning.py
    python src/cleaning.py --input data/interim/keywords_raw.csv
    python src/cleaning.py --output data/interim/keywords_clean.xlsx
"""

import argparse
import logging
import re
import sys
from pathlib import Path

import pandas as pd
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Static diacritics map for Czech/Slovak (mBank pattern — safer than NFD)
DIACRITICS_MAP = str.maketrans(
    "áäčďéěíĺľňóôŕřšťúůýžÁÄČĎÉĚÍĹĽŇÓÔŔŘŠŤÚŮÝŽ",
    "aacdeeillnoorrsuuyzAACDEEILLNOORRSUUYZ",
)


def load_params(project_root: Path) -> dict:
    """Load params.yaml from project root."""
    params_path = project_root / "params.yaml"
    if not params_path.exists():
        log.warning("params.yaml not found, using defaults")
        return {}
    with open(params_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def remove_diacritics(text: str) -> str:
    """Remove diacritics using static char map (not NFD)."""
    return text.translate(DIACRITICS_MAP)


def has_diacritics(text: str) -> bool:
    """Check if text contains diacritics."""
    return text != remove_diacritics(text)


def canonical_score(keyword: str, volume: int = 0) -> tuple[bool, int, int]:
    """Score for canonical selection. Higher = better.

    Tuple comparison: (has_diacritics, volume, -length).
    mBank pattern: prefer diacritics > higher volume > shorter keyword.
    """
    return (has_diacritics(keyword), volume, -len(keyword))


def normalize_text(text: str) -> str:
    """Normalize keyword: lowercase, strip, collapse whitespace, keep +/-/&.

    Also normalizes number-letter combos: "200A" -> "200 a", "200 A" -> "200 a".
    """
    text = str(text).lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s+\-&]", "", text)
    # Normalize number-letter: "200a" -> "200 a", "200 a" already ok
    text = re.sub(r"(\d)([a-z])", r"\1 \2", text)
    text = re.sub(r"([a-z])(\d)", r"\1 \2", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_word_signature(text: str) -> str:
    """Word-order independent signature: sorted words without diacritics."""
    return " ".join(sorted(remove_diacritics(text).split()))


def _merge_sources(series: pd.Series) -> str:
    """Merge pipe-separated source strings."""
    all_sources: set[str] = set()
    for val in series.dropna().astype(str):
        for s in val.split("|"):
            s = s.strip()
            if s:
                all_sources.add(s)
    return "|".join(sorted(all_sources))


def _build_agg_rules(
    volume_strategy: str, extra_cols: list[str] | None = None
) -> dict[str, str | object]:
    """Build aggregation rules for groupby, dynamically based on available columns."""
    rules: dict[str, str | object] = {
        "keyword": "first",
        "source": _merge_sources,
    }
    col_rules = {
        "volume": "sum" if volume_strategy == "sum_volumes" else "max",
        "kd": "first",
        "position": "min",
        "url": "first",
    }
    if extra_cols:
        for col in extra_cols:
            if col in col_rules:
                rules[col] = col_rules[col]
    return rules


# --- Step 3.2: Exact dedup ---


def step_exact_dedup(
    df: pd.DataFrame, volume_strategy: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Exact dedup on keyword_normalized. Sums volumes, tracks removed."""
    before = len(df)

    extra = [c for c in ["volume", "kd", "position", "url"] if c in df.columns]
    agg_rules = _build_agg_rules(volume_strategy, extra)

    deduped = df.groupby("keyword_normalized", as_index=False).agg(agg_rules)

    # Track removed with merged_into
    first_occurrence = df.drop_duplicates(subset="keyword_normalized", keep="first").set_index("keyword_normalized")["keyword"]
    removed_mask = df.duplicated(subset="keyword_normalized", keep="first")
    removed = df[removed_mask].copy()
    removed["removal_reason"] = "exact_dedup"
    removed["merged_into"] = removed["keyword_normalized"].map(first_occurrence)

    log.info("Exact dedup: %d -> %d (-%d)", before, len(deduped), before - len(deduped))
    return deduped, removed


# --- Step 3.3: Diacritics dedup ---


def step_diacritics_dedup(
    df: pd.DataFrame, volume_strategy: str
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Diacritics dedup with canonical scoring and cluster report.

    Returns: (deduped_df, removed_df, cluster_report_df)
    """
    before = len(df)

    df["keyword_no_diacritics"] = df["keyword_normalized"].apply(remove_diacritics)

    # Canonical scoring: (has_diacritics, volume, -length)
    vol_col = "volume" if "volume" in df.columns else None
    df["_score"] = df.apply(
        lambda r: canonical_score(r["keyword_normalized"], int(r[vol_col]) if vol_col else 0),
        axis=1,
    )
    df = df.sort_values("_score", ascending=False)

    # Build cluster report BEFORE merging
    clusters: list[dict] = []
    for group_key, group in df.groupby("keyword_no_diacritics"):
        if len(group) > 1:
            canonical = group.iloc[0]
            variants = group["keyword_normalized"].tolist()
            clusters.append({
                "cluster_key": group_key,
                "cluster_type": "diacritics",
                "canonical": canonical["keyword_normalized"],
                "canonical_volume": int(canonical[vol_col]) if vol_col else 0,
                "variant_count": len(group),
                "all_variants": " | ".join(variants),
                "total_volume": int(group[vol_col].sum()) if vol_col else 0,
            })

    cluster_report = pd.DataFrame(clusters)

    # Track variants metadata
    variants_map = df.groupby("keyword_no_diacritics")["keyword_normalized"].apply(
        lambda x: "|".join(x.unique())
    ).to_dict()
    variant_counts = df.groupby("keyword_no_diacritics")["keyword_normalized"].nunique().to_dict()

    # Aggregate
    extra = [c for c in ["volume", "kd", "position", "url"] if c in df.columns]
    agg_rules = _build_agg_rules(volume_strategy, extra)
    agg_rules["keyword_normalized"] = "first"

    deduped = df.groupby("keyword_no_diacritics", as_index=False).agg(agg_rules)
    deduped["all_variants"] = deduped["keyword_no_diacritics"].map(variants_map)
    deduped["variant_count"] = deduped["keyword_no_diacritics"].map(variant_counts)

    # Track removed
    canonical_map = df.drop_duplicates(subset="keyword_no_diacritics", keep="first").set_index("keyword_no_diacritics")["keyword_normalized"]
    removed_mask = df.duplicated(subset="keyword_no_diacritics", keep="first")
    removed = df[removed_mask].copy()
    removed["removal_reason"] = "diacritics_dedup"
    removed["merged_into"] = removed["keyword_no_diacritics"].map(canonical_map)

    df.drop(columns=["_score"], inplace=True, errors="ignore")

    log.info("Diacritics dedup: %d -> %d (-%d)", before, len(deduped), before - len(deduped))
    if len(cluster_report) > 0:
        log.info("  Diacritics clusters: %d (avg %.1f variants)", len(cluster_report), cluster_report["variant_count"].mean())

    return deduped, removed, cluster_report


# --- Step 3.4: Word-order dedup ---


def step_word_order_dedup(
    df: pd.DataFrame, volume_strategy: str
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Word-order dedup using sorted word signature.

    Returns: (deduped_df, removed_df, cluster_report_df)
    """
    before = len(df)

    df["_word_sig"] = df["keyword_no_diacritics"].apply(get_word_signature)

    # Build cluster report
    clusters: list[dict] = []
    vol_col = "volume" if "volume" in df.columns else None
    for sig, group in df.groupby("_word_sig"):
        if len(group) > 1:
            best = group.iloc[0] if vol_col is None else group.loc[group[vol_col].idxmax()]
            clusters.append({
                "cluster_key": sig,
                "cluster_type": "word_order",
                "canonical": best["keyword_normalized"],
                "canonical_volume": int(best[vol_col]) if vol_col else 0,
                "variant_count": len(group),
                "all_variants": " | ".join(group["keyword_normalized"].tolist()),
                "total_volume": int(group[vol_col].sum()) if vol_col else 0,
            })

    cluster_report = pd.DataFrame(clusters)

    # Sort by volume desc to keep best
    if vol_col:
        df = df.sort_values(vol_col, ascending=False)

    extra = [c for c in ["volume", "kd", "position", "url"] if c in df.columns]
    agg_rules = _build_agg_rules(volume_strategy, extra)
    agg_rules["keyword_normalized"] = "first"
    agg_rules["keyword_no_diacritics"] = "first"
    if "all_variants" in df.columns:
        agg_rules["all_variants"] = lambda x: "|".join(
            sorted(set("|".join(x.dropna().astype(str)).split("|")))
        )
    if "variant_count" in df.columns:
        agg_rules["variant_count"] = "sum"

    deduped = df.groupby("_word_sig", as_index=False).agg(agg_rules)

    canonical_map = df.drop_duplicates(subset="_word_sig", keep="first").set_index("_word_sig")["keyword_normalized"]
    removed_mask = df.duplicated(subset="_word_sig", keep="first")
    removed = df[removed_mask].copy()
    removed["removal_reason"] = "word_order_dedup"
    removed["merged_into"] = removed["_word_sig"].map(canonical_map)

    deduped.drop(columns=["_word_sig"], inplace=True, errors="ignore")
    df.drop(columns=["_word_sig"], inplace=True, errors="ignore")

    log.info("Word-order dedup: %d -> %d (-%d)", before, len(deduped), before - len(deduped))
    return deduped, removed, cluster_report


# --- Step 3.5: Filtering ---


def step_filtering(
    df: pd.DataFrame,
    min_volume: int = 10,
    min_length: int = 3,
    max_length: int = 100,
    blacklist: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Filter by volume, length, blacklist. Returns (kept, filtered_out)."""
    before = len(df)
    filtered_frames: list[pd.DataFrame] = []

    # Volume filter
    if "volume" in df.columns and min_volume > 0:
        low = df[df["volume"] < min_volume].copy()
        low["filter_reason"] = f"volume < {min_volume}"
        filtered_frames.append(low)
        df = df[df["volume"] >= min_volume].copy()
        log.info("  Volume filter (<%d): removed %d", min_volume, len(low))

    # Length filters
    if min_length > 0:
        short = df[df["keyword_normalized"].str.len() < min_length].copy()
        short["filter_reason"] = f"length < {min_length}"
        filtered_frames.append(short)
        df = df[df["keyword_normalized"].str.len() >= min_length].copy()

    if max_length < 999:
        long = df[df["keyword_normalized"].str.len() > max_length].copy()
        long["filter_reason"] = f"length > {max_length}"
        filtered_frames.append(long)
        df = df[df["keyword_normalized"].str.len() <= max_length].copy()

    # Blacklist filter (substring match — "kurz" matches "kurzovy" too)
    if blacklist:
        bl = [b.lower().strip() for b in blacklist if b.strip()]
        if bl:
            pattern = "|".join(re.escape(b) for b in bl)
            regex = rf"({pattern})"
            mask = df["keyword_normalized"].str.contains(regex, regex=True, na=False)
            blocked = df[mask].copy()
            blocked["filter_reason"] = "blacklist: " + blocked["keyword_normalized"].str.extract(
                rf"({pattern})", expand=False
            ).fillna("unknown")
            filtered_frames.append(blocked)
            df = df[~mask].copy()
            log.info("  Blacklist filter: removed %d", len(blocked))

    filtered_out = pd.concat(filtered_frames, ignore_index=True) if filtered_frames else pd.DataFrame()
    log.info("Filtering total: %d -> %d (-%d)", before, len(df), before - len(df))
    return df, filtered_out


# --- XLSX multi-sheet output ---


def save_xlsx_report(
    final_df: pd.DataFrame,
    all_df: pd.DataFrame,
    removed_df: pd.DataFrame,
    cluster_reports: list[pd.DataFrame],
    summary: dict,
    output_path: Path,
) -> None:
    """Save XLSX with 5 sheets (mBank pattern)."""
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # Sheet 1: Final Keywords (clean, deduplicated)
        final_df.to_excel(writer, sheet_name="Final Keywords", index=False)

        # Sheet 2: All Keywords (with flags)
        if len(all_df) > 0:
            all_df.to_excel(writer, sheet_name="All Keywords", index=False)

        # Sheet 3: Merged Variants (removed during dedup)
        if len(removed_df) > 0:
            removed_df.to_excel(writer, sheet_name="Merged Variants", index=False)

        # Sheet 4: Variant Clusters (audit trail)
        clusters = pd.concat(cluster_reports, ignore_index=True) if cluster_reports else pd.DataFrame()
        if len(clusters) > 0:
            clusters = clusters.sort_values("total_volume", ascending=False)
            clusters.to_excel(writer, sheet_name="Variant Clusters", index=False)

        # Sheet 5: Summary
        summary_df = pd.DataFrame([summary])
        summary_df.to_excel(writer, sheet_name="Summary", index=False)

    log.info("Saved XLSX report: %s", output_path)


# --- Main ---


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Clean and deduplicate keywords")
    parser.add_argument("--input", type=Path, default=Path("data/interim/keywords_raw.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/interim/keywords_clean.xlsx"))
    parser.add_argument("--project-root", type=Path, default=Path("."))
    args = parser.parse_args()

    params = load_params(args.project_root)
    cleaning_cfg = params.get("cleaning", {})
    filters_cfg = params.get("filters", {})
    volume_strategy = cleaning_cfg.get("volume_strategy", "sum_volumes")
    word_order_dedup = cleaning_cfg.get("word_order_dedup", False)

    # Load
    if not args.input.exists():
        log.error("Input file not found: %s", args.input)
        sys.exit(1)

    df = pd.read_csv(args.input, encoding="utf-8-sig")
    initial_count = len(df)
    log.info("Loaded %d keywords from %s", initial_count, args.input)

    # Keep copy for "All Keywords" sheet
    all_removed: list[pd.DataFrame] = []
    cluster_reports: list[pd.DataFrame] = []

    # Step 3.1: Text normalization
    log.info("Step 3.1: Text normalization")
    df["keyword"] = df["keyword"].astype(str).str.strip()
    df["keyword_normalized"] = df["keyword"].apply(normalize_text)
    df = df[df["keyword_normalized"].str.len() > 0].copy()
    log.info("  After normalization: %d keywords", len(df))

    # Step 3.2: Exact dedup
    log.info("Step 3.2: Exact dedup")
    df, removed_exact = step_exact_dedup(df, volume_strategy)
    all_removed.append(removed_exact)

    # Step 3.3: Diacritics dedup
    log.info("Step 3.3: Diacritics dedup")
    df, removed_diacritics, diac_clusters = step_diacritics_dedup(df, volume_strategy)
    all_removed.append(removed_diacritics)
    if len(diac_clusters) > 0:
        cluster_reports.append(diac_clusters)

    # Step 3.4: Word-order dedup (optional)
    if word_order_dedup:
        log.info("Step 3.4: Word-order dedup (enabled)")
        df, removed_word_order, wo_clusters = step_word_order_dedup(df, volume_strategy)
        all_removed.append(removed_word_order)
        if len(wo_clusters) > 0:
            cluster_reports.append(wo_clusters)
    else:
        log.info("Step 3.4: Word-order dedup SKIPPED (set word_order_dedup: true to enable)")

    count_after_dedup = len(df)

    # Step 3.5: Filtering
    log.info("Step 3.5: Filtering")
    df, filtered_out = step_filtering(
        df,
        min_volume=filters_cfg.get("min_search_volume", 10),
        min_length=filters_cfg.get("min_length", 3),
        max_length=filters_cfg.get("max_length", 100),
        blacklist=filters_cfg.get("blacklist", []),
    )

    # Sort by volume
    if "volume" in df.columns:
        df = df.sort_values("volume", ascending=False).reset_index(drop=True)

    # Reorder columns
    col_order = [
        "keyword", "keyword_normalized", "keyword_no_diacritics",
        "source", "volume", "kd", "position", "url",
        "all_variants", "variant_count",
    ]
    cols = [c for c in col_order if c in df.columns]
    extra = [c for c in df.columns if c not in cols]
    df = df[cols + extra]

    # Combine removed
    removed_df = pd.concat(all_removed, ignore_index=True) if all_removed else pd.DataFrame()

    # Summary stats
    summary = {
        "input_keywords": initial_count,
        "after_normalization": initial_count,  # approx
        "exact_duplicates_removed": len(removed_exact) if len(removed_exact) > 0 else 0,
        "diacritics_variants_merged": len(removed_diacritics) if len(removed_diacritics) > 0 else 0,
        "word_order_variants_merged": len(all_removed[2]) if word_order_dedup and len(all_removed) > 2 else 0,
        "after_dedup": count_after_dedup,
        "filtered_out": len(filtered_out),
        "final_keywords": len(df),
        "kept_percent": round(len(df) / initial_count * 100, 1) if initial_count > 0 else 0,
        "total_volume": int(df["volume"].sum()) if "volume" in df.columns else 0,
        "volume_strategy": volume_strategy,
        "word_order_dedup_enabled": word_order_dedup,
    }

    # Save outputs
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Primary: XLSX multi-sheet
    xlsx_path = args.output.with_suffix(".xlsx")
    save_xlsx_report(df, df, removed_df, cluster_reports, summary, xlsx_path)

    # Secondary: CSV for pipeline
    csv_path = args.output.with_suffix(".csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    log.info("Saved CSV: %s (%d)", csv_path, len(df))

    # Removed keywords
    if len(removed_df) > 0:
        removed_path = args.output.parent / "keywords_removed.csv"
        removed_df.to_csv(removed_path, index=False, encoding="utf-8-sig")
        log.info("Saved removed: %s (%d)", removed_path, len(removed_df))

    # Filtered out keywords
    if len(filtered_out) > 0:
        filtered_path = args.output.parent / "keywords_filtered_out.csv"
        filtered_out.to_csv(filtered_path, index=False, encoding="utf-8-sig")
        log.info("Saved filtered-out: %s (%d)", filtered_path, len(filtered_out))

    # Summary
    log.info("=" * 50)
    log.info("CLEANING SUMMARY")
    log.info("=" * 50)
    log.info("Input:              %d keywords", initial_count)
    log.info("Exact dupes:        -%d", summary["exact_duplicates_removed"])
    log.info("Diacritics merged:  -%d", summary["diacritics_variants_merged"])
    log.info("Word-order merged:  -%d", summary["word_order_variants_merged"])
    log.info("After dedup:        %d", count_after_dedup)
    log.info("Filtered out:       -%d", len(filtered_out))
    log.info("Final output:       %d keywords (%.1f%% kept)", len(df), summary["kept_percent"])
    if "volume" in df.columns:
        log.info("Total volume:       %d", summary["total_volume"])


if __name__ == "__main__":
    main()
