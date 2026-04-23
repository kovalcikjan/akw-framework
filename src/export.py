"""
Faze 11: Export & Deliverables

Finalni klientsky package. Konsoliduje vystupy fazi 7-10 do jednoho
klientskeho XLSX s executive summary a action plan.

Vstup:  data/interim/keywords_scored.csv (nebo keywords_mapped.csv pokud faze 10 bezela)
        + data/output/07_dashboard.xlsx, 08_gap.xlsx, 09_scoring.xlsx, 10_*.xlsx
Vystup: data/output/11_FINAL_<client>_<date>.xlsx
        (optional) Google Sheets sync pres --to-sheets <id>
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


AUDIT_COLS = [
    "keyword_normalized", "keyword_no_diacritics", "all_variants", "variant_count",
    "source", "relevance_source", "relevance_confidence", "review_flag",
    "categorization_source", "categorization_confidence",
    "categorization_reason", "categorization_issue",
    "cluster_key",
]


def load_params(project_root: Path) -> dict:
    path = project_root / "params.yaml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def filter_client_columns(df: pd.DataFrame, keep_scoring_reason: bool = True) -> pd.DataFrame:
    """Skryje audit/debug sloupce z klientskeho vystupu."""
    drop = [c for c in AUDIT_COLS if c in df.columns]
    if not keep_scoring_reason and "scoring_reason" in df.columns:
        drop.append("scoring_reason")
    return df.drop(columns=drop, errors="ignore")


def build_executive_summary(df: pd.DataFrame, client_name: str) -> pd.DataFrame:
    """Top metriky + key numbers pro klienta."""
    rows = [
        ["Klient", client_name],
        ["Datum analyzy", date.today().isoformat()],
        ["Celkovy pocet KW (relevantni)", len(df)],
    ]
    if "volume" in df.columns:
        vol = pd.to_numeric(df["volume"], errors="coerce")
        rows.append(["Total monthly search volume", int(vol.sum())])
    if "priority_tier" in df.columns:
        tc = df["priority_tier"].value_counts()
        for t in ["P1", "P2", "P3", "P4"]:
            rows.append([f"Priority {t}", int(tc.get(t, 0))])
    if "gap_type" in df.columns:
        gt = df["gap_type"].value_counts()
        rows.append(["Quick wins", int(gt.get("quick_win", 0))])
        rows.append(["Close gaps", int(gt.get("close_gap", 0))])
        rows.append(["Content gaps", int(gt.get("content_gap", 0))])
        rows.append(["Defended pozice", int(gt.get("defended", 0))])
    if "priority" in df.columns:
        rows.append(["Money keywords", int((df["priority"] == "money_keyword").sum())])
    if "position_client" in df.columns:
        pc = pd.to_numeric(df["position_client"], errors="coerce")
        rows.append(["% KW s rankujici pozici klienta",
                     round(pc.notna().mean() * 100, 1)])
    if "gap_traffic_potential" in df.columns:
        gtp = pd.to_numeric(df["gap_traffic_potential"], errors="coerce").fillna(0)
        rows.append(["Odhad celkoveho gap trafficu (visits/month)", int(gtp.sum())])

    return pd.DataFrame(rows, columns=["Metrika", "Hodnota"])


def build_action_plan(df: pd.DataFrame) -> pd.DataFrame:
    """Seradi podle priority tier + gap_type — co resit prvni."""
    if "priority_tier" not in df.columns:
        return df.copy()

    tier_order = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
    gap_order = {
        "quick_win": 0,
        "close_gap": 1,
        "content_gap": 2,
        "defended": 3,
        "monitor": 4,
        "no_opportunity": 5,
    }

    tmp = df.copy()
    tmp["_tier_sort"] = tmp["priority_tier"].map(tier_order).fillna(9)
    tmp["_gap_sort"] = tmp.get("gap_type", pd.Series("", index=tmp.index)).map(
        gap_order
    ).fillna(9)
    score_sort = pd.to_numeric(tmp.get("priority_score"), errors="coerce").fillna(0)

    ordered = tmp.assign(_score_sort=-score_sort).sort_values(
        ["_tier_sort", "_gap_sort", "_score_sort"]
    )
    return ordered.drop(columns=["_tier_sort", "_gap_sort", "_score_sort"], errors="ignore")


def build_methodology(params: dict) -> pd.DataFrame:
    """Methodology sheet — transparentnost pro klienta."""
    rows = [["Sekce", "Popis"]]
    rows.append(["Framework verze", "AKW Framework faze 0-11"])
    rows.append(["", ""])
    rows.append(["FAZE 4: Relevance", "Rule-based + AI klasifikace ANO/NE/MOZNA"])
    rows.append(["FAZE 5: Kategorizace", "Intent (INFO/COMM/TRANS/NAV), funnel, produkt, brand"])
    rows.append(["FAZE 8: Competitive Gap", "Quick wins, close gaps, content gaps, defended"])
    rows.append(["FAZE 9: Scoring", "Transparentni model se 3 komponentami (BV+RP+TP)"])

    # scoring weights — default values MUSI odpovidat scoring.py DEFAULT_*
    DEFAULT_WEIGHTS = {"business_value": 0.40, "ranking_probability": 0.35, "traffic_potential": 0.25}
    DEFAULT_TIERS = {"P1": 7.5, "P2": 5.0, "P3": 2.5}
    sc = params.get("scoring") or {}
    weights = {**DEFAULT_WEIGHTS, **(sc.get("weights") or {})}
    for k in ["business_value", "ranking_probability", "traffic_potential"]:
        rows.append([f"  Vaha {k}", weights[k]])
    tiers_cfg = sc.get("tier_thresholds") or sc.get("tiers") or {}
    tiers = {**DEFAULT_TIERS, **tiers_cfg}
    for t in ["P1", "P2", "P3"]:
        rows.append([f"  Tier {t} threshold", tiers[t]])

    rows.append(["", ""])
    rows.append(["Priority tiers", "P1 = immediate, P2 = next quarter, P3 = nice-to-have, P4 = archive"])
    rows.append(["Gap types", "quick_win (pos 4-20 + konkurent top 3), close_gap, content_gap, defended"])

    return pd.DataFrame(rows[1:], columns=rows[0])


def main() -> int:
    parser = argparse.ArgumentParser(description="Faze 11: Export & Deliverables")
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--input", type=Path, default=None,
                        help="Vstupni CSV (default: keywords_mapped.csv nebo keywords_scored.csv)")
    parser.add_argument("--output", type=Path, default=None,
                        help="Vystupni XLSX (default: 11_FINAL_<client>_<date>.xlsx)")
    parser.add_argument("--to-sheets", type=str, default=None,
                        help="Google Sheets spreadsheet ID — on-demand sync (vyzaduje google_sheets_helper.py)")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    interim_dir = project_root / "data" / "interim"
    output_dir = project_root / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # input priority
    input_path = args.input
    if input_path is None:
        for cand in ["keywords_mapped.csv", "keywords_scored.csv"]:
            p = interim_dir / cand
            if p.exists():
                input_path = p
                break
    if input_path is None or not input_path.exists():
        log.error("Nenalezen keywords_mapped.csv ani keywords_scored.csv v %s", interim_dir)
        return 1

    params = load_params(project_root)
    client_name = (params.get("export") or {}).get("client_name") \
        or (params.get("client") or {}).get("name") \
        or "client"
    # safe filename
    safe_client = "".join(c if c.isalnum() else "_" for c in client_name).strip("_")
    today_str = date.today().isoformat()

    output_path = args.output or (output_dir / f"11_FINAL_{safe_client}_{today_str}.xlsx")

    log.info("Input:  %s", input_path)
    log.info("Output: %s", output_path)

    df = pd.read_csv(input_path, encoding="utf-8-sig", low_memory=False)
    log.info("Nacteno %d radku", len(df))

    export_cfg = params.get("export") or {}
    per_segment = bool(export_cfg.get("per_segment_sheets", True))
    include_methodology = bool(export_cfg.get("include_methodology_sheet", True))

    df_client = filter_client_columns(df, keep_scoring_reason=True)

    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        # 01 Executive Summary
        exec_sum = build_executive_summary(df, client_name)
        exec_sum.to_excel(writer, sheet_name="01_Executive_Summary", index=False)

        # 02 Action Plan
        action = build_action_plan(df_client)
        action.to_excel(writer, sheet_name="02_Action_Plan", index=False)

        # 03 Full Keyword List
        df_client.to_excel(writer, sheet_name="03_Full_Keyword_List", index=False)

        # 04 Per Segment
        if per_segment and "produkt" in df_client.columns:
            for prod, subset in df_client.groupby("produkt"):
                if pd.isna(prod) or not str(prod).strip():
                    continue
                safe_prod = str(prod).replace("/", "_")[:25]
                sheet = f"04_{safe_prod}"
                subset.sort_values(
                    "priority_score" if "priority_score" in subset.columns else "volume",
                    ascending=False,
                ).to_excel(writer, sheet_name=sheet, index=False)

        # 05 Quick Wins
        if "gap_type" in df_client.columns:
            qw = df_client[df_client["gap_type"] == "quick_win"]
            if "gap_traffic_potential" in qw.columns:
                qw = qw.sort_values("gap_traffic_potential", ascending=False)
            qw.to_excel(writer, sheet_name="05_Quick_Wins", index=False)

            # 06 Content Gaps
            cg = df_client[df_client["gap_type"] == "content_gap"]
            if "priority_score" in cg.columns:
                cg = cg.sort_values("priority_score", ascending=False)
            cg.to_excel(writer, sheet_name="06_Content_Gaps", index=False)

        # 07 Content Plan (pokud faze 10 bezela)
        content_plan_path = output_dir / "10_content_mapping.xlsx"
        if content_plan_path.exists():
            try:
                url_plan = pd.read_excel(content_plan_path, sheet_name="URL_Plan")
                url_plan.to_excel(writer, sheet_name="07_Content_Plan", index=False)
            except Exception as e:
                log.warning("Nelze nacist URL_Plan z 10_content_mapping.xlsx: %s", e)

        # 08 Methodology
        if include_methodology:
            method = build_methodology(params)
            method.to_excel(writer, sheet_name="08_Methodology", index=False)

    log.info("=" * 50)
    log.info("EXPORT HOTOVO: %s", output_path)

    # optional Google Sheets sync
    if args.to_sheets:
        try:
            from google_sheets_helper import sync_xlsx_to_sheets  # type: ignore
            sync_xlsx_to_sheets(output_path, args.to_sheets)
            log.info("Google Sheets sync: spreadsheet %s", args.to_sheets)
        except ImportError:
            log.warning("google_sheets_helper.py neni k dispozici — Sheets sync preskocen. "
                        "Zkopiruj google_sheets_helper.py z Delonghi/src do frameworku.")
        except Exception as e:
            log.error("Google Sheets sync selhal: %s", e)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
