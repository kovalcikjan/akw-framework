"""Faze 1C: Merge all raw keyword files and perform initial deduplication.

Reads all CSV/XLSX files from data/raw/, merges them into a single dataset,
performs exact + lowercase deduplication, and outputs keywords_raw.csv.

Usage:
    python src/merge_sources.py
    python src/merge_sources.py --raw-dir data/raw --output data/interim/keywords_raw.csv
"""

import argparse
import logging
import re
import sys
from pathlib import Path

import pandas as pd
import yaml
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Expected column name mappings (source files may use different names)
COLUMN_ALIASES: dict[str, list[str]] = {
    "keyword": ["keyword", "keywords", "query", "search_query", "term", "kw", "klicove_slovo", "klic"],
    "volume": [
        "volume", "search_volume", "sv", "avg_monthly_searches",
        "hledanost", "search volume",
    ],
    "kd": ["kd", "keyword_difficulty", "difficulty", "seo_difficulty"],
    "position": ["position", "pos", "rank", "ranking", "pozice"],
    "url": ["url", "landing_page", "page", "ranking_url"],
    "source": ["source", "zdroj"],
}


def load_params(project_root: Path) -> dict:
    """Load params.yaml from project root."""
    params_path = project_root / "params.yaml"
    if not params_path.exists():
        log.warning("params.yaml not found, using defaults")
        return {}
    with open(params_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def detect_source_name(filepath: Path) -> str:
    """Infer source name from filename.

    Examples:
        ahrefs_export.csv -> ahrefs
        gsc_keywords.xlsx -> gsc
        competitor_example.com.csv -> competitor_example.com
        marketing_miner_suggestions.csv -> marketing_miner
    """
    stem = filepath.stem.lower()
    # Remove common suffixes
    stem = re.sub(r"[_-]?(export|keywords|data|final|v\d+)$", "", stem)
    return stem or filepath.stem.lower()


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map various column names to standard schema."""
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    rename_map: dict[str, str] = {}
    for standard_name, aliases in COLUMN_ALIASES.items():
        if standard_name in df.columns:
            continue
        for alias in aliases:
            if alias in df.columns:
                rename_map[alias] = standard_name
                break

    if rename_map:
        df = df.rename(columns=rename_map)

    return df


def read_file(filepath: Path) -> pd.DataFrame:
    """Read CSV or XLSX file with encoding detection."""
    suffix = filepath.suffix.lower()

    if suffix == ".xlsx":
        return pd.read_excel(filepath, engine="openpyxl")
    elif suffix == ".xls":
        return pd.read_excel(filepath, engine="xlrd")
    elif suffix in (".csv", ".tsv", ".txt"):
        # Try UTF-8 first, fall back to cp1250 (common for Czech data)
        for encoding in ["utf-8", "utf-8-sig", "cp1250", "latin-1"]:
            try:
                sep = "\t" if suffix == ".tsv" else ","
                df = pd.read_csv(filepath, encoding=encoding, sep=sep)
                if len(df.columns) == 1 and ";" in str(df.columns[0]):
                    df = pd.read_csv(filepath, encoding=encoding, sep=";")
                return df
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
        raise ValueError(f"Cannot read {filepath} with any supported encoding")
    else:
        raise ValueError(f"Unsupported file format: {suffix}")


def merge_sources(raw_dir: Path) -> pd.DataFrame:
    """Read and merge all files from raw directory."""
    supported = {".csv", ".tsv", ".txt", ".xlsx", ".xls"}
    files = sorted(
        f for f in raw_dir.iterdir()
        if f.suffix.lower() in supported and not f.name.startswith(".")
    )

    if not files:
        log.error("No supported files found in %s", raw_dir)
        sys.exit(1)

    log.info("Found %d files in %s", len(files), raw_dir)

    frames: list[pd.DataFrame] = []
    for filepath in tqdm(files, desc="Reading files"):
        log.info("  Reading: %s", filepath.name)
        df = read_file(filepath)
        df = normalize_columns(df)

        if "keyword" not in df.columns:
            # Auto-detect: look for column containing "key" or "klic" (CPP pattern)
            candidates = [c for c in df.columns if any(s in c.lower() for s in ["key", "klic", "query", "term"])]
            if candidates:
                df = df.rename(columns={candidates[0]: "keyword"})
                log.info("    Auto-detected keyword column: '%s'", candidates[0])
            else:
                log.warning("    SKIP: no 'keyword' column found (columns: %s)", list(df.columns))
                continue

        # Add source if not present
        if "source" not in df.columns:
            df["source"] = detect_source_name(filepath)

        # Coerce volume to numeric
        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)

        frames.append(df)
        log.info("    OK: %d keywords", len(df))

    if not frames:
        log.error("No valid keyword files found")
        sys.exit(1)

    merged = pd.concat(frames, ignore_index=True)
    log.info("Merged total: %d keywords from %d files", len(merged), len(frames))
    return merged


def initial_dedup(df: pd.DataFrame) -> pd.DataFrame:
    """Exact + lowercase deduplication with volume summing."""
    before = len(df)

    # Normalize keyword
    df["keyword"] = df["keyword"].astype(str).str.strip()
    df["keyword_normalized"] = df["keyword"].str.lower().str.strip()
    df["keyword_normalized"] = df["keyword_normalized"].str.replace(r"\s+", " ", regex=True)

    # Remove empty keywords
    df = df[df["keyword_normalized"].str.len() > 0].copy()

    # Group by normalized keyword, aggregate
    agg_rules: dict[str, str | tuple] = {
        "keyword": "first",  # keep first occurrence (original case)
        "source": lambda x: "|".join(sorted(set(x.dropna().astype(str)))),
    }

    # Optional columns - aggregate if present
    if "volume" in df.columns:
        agg_rules["volume"] = "sum"
    if "kd" in df.columns:
        agg_rules["kd"] = "first"
    if "position" in df.columns:
        agg_rules["position"] = "min"  # best position
    if "url" in df.columns:
        agg_rules["url"] = "first"

    deduped = df.groupby("keyword_normalized", as_index=False).agg(agg_rules)

    after = len(deduped)
    removed = before - after
    log.info(
        "Initial dedup: %d -> %d (-%d, %.1f%% removed)",
        before, after, removed, (removed / before * 100) if before > 0 else 0,
    )

    return deduped


def print_summary(df: pd.DataFrame) -> None:
    """Print summary statistics."""
    log.info("=" * 50)
    log.info("SUMMARY")
    log.info("=" * 50)
    log.info("Total keywords: %d", len(df))

    if "source" in df.columns:
        # Count keywords per source (sources can be pipe-separated)
        source_counts: dict[str, int] = {}
        for sources_str in df["source"]:
            for s in str(sources_str).split("|"):
                s = s.strip()
                if s:
                    source_counts[s] = source_counts.get(s, 0) + 1
        log.info("Sources:")
        for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
            log.info("  %-30s %d", src, count)

    if "volume" in df.columns:
        vol = df["volume"]
        log.info("Volume: min=%d, max=%d, median=%.0f, mean=%.0f", vol.min(), vol.max(), vol.median(), vol.mean())

        # Volume buckets
        buckets = [0, 10, 50, 100, 500, 1000, 5000, float("inf")]
        labels = ["0-10", "10-50", "50-100", "100-500", "500-1K", "1K-5K", "5K+"]
        df["_vol_bucket"] = pd.cut(vol, bins=buckets, labels=labels, right=False)
        log.info("Volume distribution:")
        for label in labels:
            count = (df["_vol_bucket"] == label).sum()
            log.info("  %-10s %d", label, count)
        df.drop(columns=["_vol_bucket"], inplace=True)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Merge raw keyword files")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("data/interim/keywords_raw.csv"))
    args = parser.parse_args()

    # Ensure output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Merge
    df = merge_sources(args.raw_dir)

    # Dedup
    df = initial_dedup(df)

    # Sort by volume descending
    if "volume" in df.columns:
        df = df.sort_values("volume", ascending=False).reset_index(drop=True)

    # Reorder columns
    col_order = ["keyword", "keyword_normalized", "source", "volume", "kd", "position", "url"]
    cols = [c for c in col_order if c in df.columns]
    extra = [c for c in df.columns if c not in cols]
    df = df[cols + extra]

    # Save
    df.to_csv(args.output, index=False, encoding="utf-8-sig")
    log.info("Saved to %s", args.output)

    # Summary
    print_summary(df)


if __name__ == "__main__":
    main()
