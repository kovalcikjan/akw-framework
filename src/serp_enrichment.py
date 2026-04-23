"""
Faze 6.5: SERP Enrichment

Doplnuje ke kategorizovanemu datasetu pozice klienta + konkurence, KD a SERP features.
Ma dva mody:

  --from-csv  (default)  Mapuje existujici sloupce z data/interim/<input>.csv
                         na standardni schema podle params.yaml: enrichment.
                         Pouzivane pro projekty s Marketing Miner exportem, ktery
                         SERP data uz obsahuje.

  --from-api             Placeholder — budouci implementace pro Marketing Miner /
                         Ahrefs API. Zatim vyhazuje NotImplementedError.

Vystupni standardni schema:
  position_client, position_<competitor_domain>, best_competitor_position,
  best_competitor_domain, kd, serp_features, has_featured_snippet, top_10_domains

Vse z predchozi faze (5 nebo 6) zustava.
"""
from __future__ import annotations

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


def load_params(project_root: Path) -> dict:
    path = project_root / "params.yaml"
    if not path.exists():
        log.warning("params.yaml not found at %s — using defaults", path)
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def parse_position(value) -> float | None:
    """Parsuje pozici z SERP dat. Vraci float nebo None.

    Akceptuje:
      - cislo (int, float)
      - string s cislem ("21", "15.5")
      - "21+" / "100+" / "N+" → None (nerankuje)
      - "AdWords", "featured", textove hodnoty → None
      - NaN, None, "" → None
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    if s.endswith("+"):
        return None
    # pokusim se o numerickou konverzi
    try:
        return float(s)
    except ValueError:
        return None


def clean_position_column(series: pd.Series, position_max_valid: float) -> pd.Series:
    """Aplikuje parse_position + clamp na sloupec."""
    parsed = series.apply(parse_position)
    # clamp — vse nad position_max_valid = None
    parsed = parsed.apply(
        lambda p: p if (p is not None and 0 < p <= position_max_valid) else None
    )
    return parsed


def extract_serp_features(value) -> str:
    """Prevede SERP Feature string z MM na pipe-separated standardni format.

    Vstup priklady:
      "related search (Page One Extra),images (Page One Extra)"
      "AdWords (header),featured snippet"
      ""
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip()
    if not s:
        return ""
    # rozdeli podle carky, odstrani poznamky v zavorkach, normalizuje
    features = []
    for part in s.split(","):
        clean = re.sub(r"\s*\([^)]*\)", "", part).strip().lower()
        if not clean:
            continue
        # normalizace nazvu features
        mapping = {
            "related search": "related_search",
            "images": "images",
            "adwords": "adwords",
            "featured snippet": "featured_snippet",
            "video": "video",
            "local pack": "local_pack",
            "shopping": "shopping",
            "people also ask": "paa",
            "paa": "paa",
            "knowledge panel": "knowledge_panel",
        }
        features.append(mapping.get(clean, clean.replace(" ", "_")))
    # dedup pri zachovani poradi
    seen = set()
    dedup = []
    for f in features:
        if f not in seen:
            seen.add(f)
            dedup.append(f)
    return "|".join(dedup)


def enrich_from_csv(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Namapuje existujici sloupce datasetu na standardni enrichment schema."""
    out = df.copy()
    position_max = float(config.get("position_max_valid", 100))

    # 1) position_client — primary + fallback
    primary_col = config.get("client_position_column")
    fallback_col = config.get("client_position_fallback")
    if primary_col and primary_col in out.columns:
        pos = clean_position_column(out[primary_col], position_max)
        if fallback_col and fallback_col in out.columns:
            fallback = clean_position_column(out[fallback_col], position_max)
            pos = pos.fillna(fallback)
        out["position_client"] = pos
        log.info("position_client: %d/%d KW rankuje (%.1f %%)",
                 pos.notna().sum(), len(out), pos.notna().mean() * 100)
    elif "position_client" not in out.columns:
        out["position_client"] = pd.NA
        log.warning("Nelze mapovat position_client — primary_col '%s' chybi", primary_col)

    # 2) competitor positions
    competitor_cols = config.get("competitor_columns", {}) or {}
    tracked_domains = []
    for domain, src_col in competitor_cols.items():
        if src_col not in out.columns:
            log.warning("Competitor sloupec '%s' (pro %s) neni v datasetu — preskakuji",
                        src_col, domain)
            continue
        col_name = f"position_{domain}"
        out[col_name] = clean_position_column(out[src_col], position_max)
        tracked_domains.append(domain)
        log.info("position_%s: %d/%d KW rankuje",
                 domain, out[col_name].notna().sum(), len(out))

    # 3) best_competitor_position + best_competitor_domain
    if tracked_domains:
        comp_cols = [f"position_{d}" for d in tracked_domains]
        comp_df = out[comp_cols].copy()
        has_any = comp_df.notna().any(axis=1)
        best_pos = pd.Series(pd.NA, index=out.index, dtype="Float64")
        best_dom = pd.Series(pd.NA, index=out.index, dtype="object")
        if has_any.any():
            valid = comp_df.loc[has_any]
            best_pos.loc[has_any] = valid.min(axis=1).astype("Float64")
            best_dom.loc[has_any] = valid.idxmin(axis=1).str.replace(
                "position_", "", regex=False
            )
        out["best_competitor_position"] = best_pos
        out["best_competitor_domain"] = best_dom
    else:
        out["best_competitor_position"] = pd.NA
        out["best_competitor_domain"] = pd.NA

    # 4) kd — pokud neni, vezmi z kd_column
    kd_col = config.get("kd_column", "kd")
    if "kd" not in out.columns and kd_col in out.columns:
        out["kd"] = pd.to_numeric(out[kd_col], errors="coerce")
    elif "kd" in out.columns:
        out["kd"] = pd.to_numeric(out["kd"], errors="coerce")

    # 5) SERP features
    serp_col = config.get("serp_features_column")
    if serp_col and serp_col in out.columns:
        out["serp_features"] = out[serp_col].apply(extract_serp_features)
        out["has_featured_snippet"] = out["serp_features"].str.contains(
            "featured_snippet", na=False
        )
    else:
        out["serp_features"] = ""
        out["has_featured_snippet"] = False

    # 6) top_10_domains — pokud neni source column, prazdne
    top10_col = config.get("top_10_domains_column")
    if top10_col and top10_col in out.columns:
        out["top_10_domains"] = out[top10_col].fillna("").astype(str)
    else:
        out["top_10_domains"] = ""

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Faze 6.5: SERP Enrichment")
    parser.add_argument("--project-root", type=Path, default=Path("."),
                        help="Korenovy adresar projektu (default: .)")
    parser.add_argument("--input", type=Path, default=None,
                        help="Vstupni CSV (default: data/interim/keywords_clustered.csv "
                             "nebo keywords_categorized.csv)")
    parser.add_argument("--output", type=Path, default=None,
                        help="Vystupni CSV (default: data/interim/keywords_enriched.csv)")
    parser.add_argument("--from-csv", action="store_true", default=True,
                        help="Mapuje existujici sloupce (default)")
    parser.add_argument("--from-api", action="store_true",
                        help="Volani externiho API (not implemented)")
    args = parser.parse_args()

    if args.from_api:
        raise NotImplementedError(
            "--from-api rezim je placeholder pro budouci Marketing Miner / Ahrefs integraci."
        )

    project_root = args.project_root.resolve()
    interim_dir = project_root / "data" / "interim"

    # najdi input
    if args.input:
        input_path = args.input
    elif (interim_dir / "keywords_clustered.csv").exists():
        input_path = interim_dir / "keywords_clustered.csv"
    elif (interim_dir / "keywords_categorized.csv").exists():
        input_path = interim_dir / "keywords_categorized.csv"
    elif (interim_dir / "keywords_categorized_full.csv").exists():
        input_path = interim_dir / "keywords_categorized_full.csv"
    else:
        log.error("Nenalezen vstupni dataset v %s — ocekavam keywords_clustered.csv "
                  "nebo keywords_categorized.csv", interim_dir)
        return 1

    output_path = args.output or (interim_dir / "keywords_enriched.csv")

    log.info("Input:  %s", input_path)
    log.info("Output: %s", output_path)

    params = load_params(project_root)
    enrichment_config = params.get("enrichment", {}) or {}

    if not enrichment_config:
        log.warning("params.yaml nema sekci 'enrichment' — pokousim se auto-detekovat "
                    "sloupce. Doporucuji doplnit enrichment config do params.yaml.")

    # default auto-detect — pokud enrichment neni v params, zkusi se typickych nazvu
    if not enrichment_config.get("client_position_column"):
        client_domain = (params.get("client", {}) or {}).get("domain", "")
        fallback_candidates = [
            f"serp_pos_{client_domain.split('.')[0]}" if client_domain else None,
            "serp_pos_client",
            "Google Position",
        ]
        df_preview = pd.read_csv(input_path, encoding="utf-8-sig", nrows=1)
        for cand in fallback_candidates:
            if cand and cand in df_preview.columns:
                enrichment_config["client_position_column"] = cand
                log.info("Auto-detekovan client_position_column: %s", cand)
                break

    df = pd.read_csv(input_path, encoding="utf-8-sig", low_memory=False)
    log.info("Nacteno %d radku, %d sloupcu", len(df), len(df.columns))

    # filter — default jen relevance=ANO (setri naklady)
    if "relevance" in df.columns:
        pre = len(df)
        df = df[df["relevance"] == "ANO"].copy()
        log.info("Filtr relevance=ANO: %d → %d KW", pre, len(df))

    enriched = enrich_from_csv(df, enrichment_config)
    enriched.to_csv(output_path, index=False, encoding="utf-8-sig")

    # summary
    log.info("=" * 50)
    log.info("ENRICHMENT HOTOVO")
    log.info("Vystup: %s (%d radku)", output_path, len(enriched))
    if "position_client" in enriched.columns:
        pc = pd.to_numeric(enriched["position_client"], errors="coerce")
        log.info("  position_client:       %d/%d (%.1f %%)",
                 pc.notna().sum(), len(enriched), pc.notna().mean() * 100)
    if "best_competitor_position" in enriched.columns:
        bcp = pd.to_numeric(enriched["best_competitor_position"], errors="coerce")
        log.info("  best_competitor_pos:   %d/%d (%.1f %%)",
                 bcp.notna().sum(), len(enriched), bcp.notna().mean() * 100)
    if "kd" in enriched.columns:
        kd = pd.to_numeric(enriched["kd"], errors="coerce")
        log.info("  kd:                    %d/%d (median=%.1f)",
                 kd.notna().sum(), len(enriched), kd.median() if kd.notna().any() else 0)
    if "has_featured_snippet" in enriched.columns:
        log.info("  has_featured_snippet:  %d KW", enriched["has_featured_snippet"].sum())

    return 0


if __name__ == "__main__":
    sys.exit(main())
