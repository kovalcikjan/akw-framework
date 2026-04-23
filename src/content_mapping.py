"""
Faze 10: Content Mapping (optional)

Akcni vrstva — priradi keywords do clusteru (1 cluster = 1 cilova URL),
urci url_status (existing/new/merge/update) a content_type.

Volitelna faze. Ridi se `params.yaml: content_mapping.enabled: true`.
Muze byt prepsano flagem `--enable`.

Vstup:  data/interim/keywords_scored.csv
Vystup: data/interim/keywords_mapped.csv + data/output/10_content_mapping.xlsx
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


DEFAULT_CONTENT_TYPES = {
    "TRANS_product": "product",
    "TRANS_category": "category",
    "TRANS_comparison": "comparison_lp",
    "COMM_comparison": "comparison",
    "COMM_guide": "guide",
    "INFO_blog": "blog",
    "INFO_faq": "faq",
    "NAV": "landing",
}


def load_params(project_root: Path) -> dict:
    path = project_root / "params.yaml"
    if not path.exists():
        log.warning("params.yaml not found at %s — using defaults", path)
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def slugify(text: str) -> str:
    """Jednoduchy slug generator (ASCII, lowercase, pomlcky)."""
    if not text:
        return ""
    trans = str.maketrans(
        "áäčďéěíĺľňóôŕřšťúůýžÁÄČĎÉĚÍĹĽŇÓÔŔŘŠŤÚŮÝŽ",
        "aacdeeillnoorrstuuyzAACDEEILLNOORRSTUUYZ",
    )
    s = text.translate(trans).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:80]


def _safe_str(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v)


def decide_content_type(intent, produkt, keyword, mapping: dict) -> str:
    """Mapping intent + produkt/keyword context → content_type."""
    intent = _safe_str(intent).upper()
    kw_lower = _safe_str(keyword).lower()
    prod_lower = _safe_str(produkt).lower()

    if intent == "NAV":
        return mapping.get("NAV", "landing")
    if intent == "TRANS":
        if any(p in kw_lower for p in ["vs", "srovnani", "porovnani"]):
            return mapping.get("TRANS_comparison", "comparison_lp")
        if prod_lower and prod_lower.startswith("_generic"):
            return mapping.get("TRANS_category", "category")
        return mapping.get("TRANS_product", "product")
    if intent == "COMM":
        if any(p in kw_lower for p in ["vs", "srovnani", "porovnani"]):
            return mapping.get("COMM_comparison", "comparison")
        return mapping.get("COMM_guide", "guide")
    if intent == "INFO":
        if any(p in kw_lower for p in ["co je", "jaky", "jaka", "proc"]):
            return mapping.get("INFO_faq", "faq")
        return mapping.get("INFO_blog", "blog")
    return "landing"


def build_cluster_key(row) -> str:
    """Skupinovaci klic — cluster_id (z faze 6) nebo produkt+intent fallback."""
    cid = row.get("cluster_id")
    if pd.notna(cid) and str(cid).strip() and str(cid) != "nan":
        return f"cluster_{cid}"
    prod = _safe_str(row.get("produkt")) or "_unknown"
    intent = _safe_str(row.get("intent")) or "_any"
    return f"{prod}__{intent.lower()}"


def is_own_url(url: str, client_domain: str) -> bool:
    if not url or not client_domain:
        return False
    url_l = str(url).lower()
    dom = client_domain.lower().replace("www.", "")
    return dom in url_l


def decide_url_status(rows: pd.DataFrame, client_domain: str) -> tuple[str, str]:
    """Rozhodne url_status pro cely cluster a vrati (status, target_url)."""
    url_col = None
    for cand in ["serp_url_llentab", "serp_url_client", "client_url", "url"]:
        if cand in rows.columns:
            url_col = cand
            break

    pos = pd.to_numeric(rows.get("position_client"), errors="coerce")
    ranking_rows = rows[pos.notna() & (pos <= 50)]

    if url_col and not ranking_rows.empty:
        own_urls = ranking_rows[url_col].dropna().astype(str)
        own_urls = [u for u in own_urls if is_own_url(u, client_domain)]
        unique_urls = set(own_urls)
        if len(unique_urls) > 1:
            return "merge", "; ".join(sorted(unique_urls)[:3])
        if len(unique_urls) == 1:
            # existing: cluster je cely pokryty stejnou URL?
            coverage = len(own_urls) / len(rows)
            if coverage < 0.5 and len(rows) > 3:
                return "update", next(iter(unique_urls))
            return "existing", next(iter(unique_urls))

    # new — potrebuji slug
    top_row = rows.sort_values("priority_score", ascending=False).iloc[0] if "priority_score" in rows.columns else rows.iloc[0]
    slug = slugify(str(top_row.get("keyword") or ""))
    return "new", f"/navrh/{slug}" if slug else "/navrh/"


def main() -> int:
    parser = argparse.ArgumentParser(description="Faze 10: Content Mapping (optional)")
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--output-csv", type=Path, default=None)
    parser.add_argument("--output-xlsx", type=Path, default=None)
    parser.add_argument("--enable", action="store_true",
                        help="Prepise params.yaml: content_mapping.enabled")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    interim_dir = project_root / "data" / "interim"
    output_dir = project_root / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    params = load_params(project_root)
    cm_cfg = params.get("content_mapping") or {}
    enabled = args.enable or bool(cm_cfg.get("enabled", False))
    if not enabled:
        log.info("Content Mapping je vypnuty (params.yaml: content_mapping.enabled: false). "
                 "Pro zapnuti pouzij --enable nebo nastavit v params.yaml.")
        return 0

    input_path = args.input or (interim_dir / "keywords_scored.csv")
    output_csv = args.output_csv or (interim_dir / "keywords_mapped.csv")
    output_xlsx = args.output_xlsx or (output_dir / "10_content_mapping.xlsx")

    if not input_path.exists():
        log.error("Nenalezen %s — spust nejdrive scoring.py", input_path)
        return 1

    log.info("Input:  %s", input_path)
    log.info("Output CSV:  %s", output_csv)
    log.info("Output XLSX: %s", output_xlsx)

    content_types_map = {**DEFAULT_CONTENT_TYPES, **(cm_cfg.get("content_types") or {})}
    client_domain = (params.get("client") or {}).get("domain", "") or ""

    df = pd.read_csv(input_path, encoding="utf-8-sig", low_memory=False)
    log.info("Nacteno %d radku", len(df))

    # filter — defaultne jen P1+P2+P3 (ne P4)
    if "priority_tier" in df.columns:
        pre = len(df)
        df = df[df["priority_tier"].isin(["P1", "P2", "P3"])].copy()
        log.info("Filter priority_tier in (P1,P2,P3): %d → %d", pre, len(df))

    # 1. cluster_key pro group
    df["cluster_key"] = df.apply(build_cluster_key, axis=1)

    # 2. per-cluster rozhodovani
    mapped_rows = []
    for cluster_key, group in df.groupby("cluster_key"):
        # primary = highest priority_score
        if "priority_score" in group.columns:
            group_sorted = group.sort_values("priority_score", ascending=False)
        else:
            group_sorted = group.copy()
        primary = group_sorted.iloc[0]
        secondary_list = group_sorted.iloc[1:]["keyword"].tolist()

        # content_type — priradit podle primary keyword
        intent = primary.get("intent")
        produkt = primary.get("produkt")
        kw = primary.get("keyword")
        ctype = decide_content_type(intent, produkt, kw, content_types_map)

        # url_status + target_url
        url_status, target_url = decide_url_status(group_sorted, client_domain)

        # zapis pro vsechny KW v clusteru
        for idx, row in group_sorted.iterrows():
            is_primary = row["keyword"] == primary["keyword"]
            mapped_rows.append({
                **row.to_dict(),
                "target_url": target_url,
                "url_status": url_status,
                "content_type": ctype,
                "primary_cluster": cluster_key,
                "is_primary_kw": is_primary,
                "secondary_keywords": "|".join(secondary_list) if is_primary else "",
            })

    mapped_df = pd.DataFrame(mapped_rows)
    mapped_df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    # XLSX
    display_cols = [
        c for c in [
            "keyword", "volume", "intent", "produkt", "priority_tier", "priority_score",
            "gap_type", "recommended_action",
            "target_url", "url_status", "content_type", "primary_cluster",
            "is_primary_kw", "secondary_keywords",
        ]
        if c in mapped_df.columns
    ]

    # URL_Plan — 1 radek per cluster (jen primary)
    url_plan_cols = [
        c for c in [
            "primary_cluster", "keyword", "secondary_keywords",
            "target_url", "url_status", "content_type",
            "intent", "produkt", "priority_tier", "priority_score",
            "gap_type", "recommended_action",
        ]
        if c in mapped_df.columns
    ]
    url_plan = mapped_df[mapped_df["is_primary_kw"]][url_plan_cols].sort_values(
        "priority_score", ascending=False
    )

    with pd.ExcelWriter(output_xlsx, engine="xlsxwriter") as writer:
        url_plan.to_excel(writer, sheet_name="URL_Plan", index=False)
        for status in ["new", "existing", "merge", "update"]:
            subset = mapped_df[mapped_df["url_status"] == status][display_cols].sort_values(
                "priority_score", ascending=False
            )
            sheet_name = {
                "new": "New_Pages",
                "existing": "Optimize_Existing",
                "merge": "Merge_Candidates",
                "update": "Update_Existing",
            }[status]
            subset.to_excel(writer, sheet_name=sheet_name, index=False)

    # summary
    log.info("=" * 50)
    log.info("CONTENT MAPPING HOTOVO")
    cluster_count = mapped_df["primary_cluster"].nunique()
    log.info("  clusters: %d", cluster_count)
    us = mapped_df.drop_duplicates("primary_cluster")["url_status"].value_counts()
    for status in ["new", "existing", "merge", "update"]:
        log.info("  %-10s %d URLs", status, int(us.get(status, 0)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
