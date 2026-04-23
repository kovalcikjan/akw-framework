"""
Faze 7: Dashboard

Deskriptivni vrstva nad zpracovanym datasetem. Odpovida na otazku
"jak data vypadaji" — struktura, distribuce, top listy, ranking distribuce.

Dashboard JE read-only vrstva. NEMENI main dataset, neprida sloupce.
NEOBSAHUJE priority P1-P4 ani doporuceni — to jsou faze 8, 9, 10.

Vystup: data/output/07_dashboard.xlsx (multi-sheet s pivoty + xlsxwriter grafy).
"""
from __future__ import annotations

import argparse
import logging
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


def ranking_bucket(pos) -> str:
    """Priradi pozici klienta do ranking bucketu."""
    if pd.isna(pos):
        return "nerankuje"
    p = float(pos)
    if p <= 3:
        return "top_3"
    if p <= 10:
        return "top_10"
    if p <= 20:
        return "pos_11_20"
    if p <= 50:
        return "pos_21_50"
    if p <= 100:
        return "pos_51_100"
    return "nerankuje"


BUCKET_ORDER = [
    "top_3",
    "top_10",
    "pos_11_20",
    "pos_21_50",
    "pos_51_100",
    "nerankuje",
]


def build_overview(df: pd.DataFrame) -> pd.DataFrame:
    """Overview sheet — klicove metriky."""
    rows = []
    rows.append(("Celkovy pocet KW", len(df)))
    if "volume" in df.columns:
        vol = pd.to_numeric(df["volume"], errors="coerce")
        rows.append(("Total volume", int(vol.sum())))
        rows.append(("Median volume", float(vol.median())))
    if "kd" in df.columns:
        kd = pd.to_numeric(df["kd"], errors="coerce")
        rows.append(("Median KD", float(kd.median()) if kd.notna().any() else 0))
    if "intent" in df.columns:
        for intent in ["TRANS", "COMM", "INFO", "NAV"]:
            pct = (df["intent"] == intent).mean() * 100
            rows.append((f"% intent {intent}", round(pct, 1)))
    if "priority" in df.columns:
        money = (df["priority"] == "money_keyword").sum()
        rows.append(("Money keywords", int(money)))
        rows.append(("Money keywords %", round(money / len(df) * 100, 1) if len(df) else 0))
    if "position_client" in df.columns:
        pc = pd.to_numeric(df["position_client"], errors="coerce")
        rows.append(("% KW s pozici klienta", round(pc.notna().mean() * 100, 1)))
        if pc.notna().any():
            rows.append(("Median pozice klienta", float(pc.median())))
    if "produkt" in df.columns:
        rows.append(("% KW s produktem", round(df["produkt"].notna().mean() * 100, 1)))
    return pd.DataFrame(rows, columns=["Metrika", "Hodnota"])


def build_dist(df: pd.DataFrame, row: str, col: str) -> pd.DataFrame:
    """Pivot count × row × col (NaN → '(prazdne)')."""
    if row not in df.columns or col not in df.columns:
        return pd.DataFrame()
    tmp = df[[row, col]].copy()
    tmp[row] = tmp[row].fillna("(prazdne)")
    tmp[col] = tmp[col].fillna("(prazdne)")
    pivot = (
        tmp.groupby([row, col])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    return pivot


def build_top_list(df: pd.DataFrame, metric_col: str, n: int = 100) -> pd.DataFrame:
    """TOP N podle metriky."""
    if metric_col not in df.columns:
        return pd.DataFrame()
    display_cols = [
        c for c in ["keyword", "volume", "kd", "intent", "funnel",
                    "produkt", "brand", "priority", "position_client"]
        if c in df.columns
    ]
    tmp = df[display_cols + ([metric_col] if metric_col not in display_cols else [])].copy()
    tmp[metric_col] = pd.to_numeric(tmp[metric_col], errors="coerce")
    return tmp.nlargest(n, metric_col)


def build_top_value(df: pd.DataFrame, n: int = 100) -> pd.DataFrame:
    """TOP N podle kombinovane hodnoty = volume × CPC (pokud CPC existuje)."""
    if "volume" not in df.columns:
        return pd.DataFrame()
    tmp = df.copy()
    vol = pd.to_numeric(tmp["volume"], errors="coerce").fillna(0)
    # hledej CPC sloupec — nekolik konvencí
    cpc_col = None
    for cand in ["cpc", "CPC", "Google CPC [CZK]", "Sklik CPC [CZK]"]:
        if cand in tmp.columns:
            cpc_col = cand
            break
    if cpc_col:
        cpc = pd.to_numeric(tmp[cpc_col], errors="coerce").fillna(0)
        tmp["_value"] = vol * cpc
    else:
        tmp["_value"] = vol  # fallback na samotne volume
        log.info("CPC sloupec nenalezen, Top_Value fallback na volume")
    display_cols = [
        c for c in ["keyword", "volume", cpc_col, "intent", "funnel",
                    "produkt", "priority", "position_client"]
        if c and c in tmp.columns
    ]
    return tmp.nlargest(n, "_value")[display_cols + ["_value"]].rename(
        columns={"_value": "value"}
    )


def build_top_per_produkt(df: pd.DataFrame, n_per: int = 10) -> pd.DataFrame:
    """Top N KW per produkt (long format)."""
    if "produkt" not in df.columns or "volume" not in df.columns:
        return pd.DataFrame()
    tmp = df.copy()
    tmp["volume"] = pd.to_numeric(tmp["volume"], errors="coerce").fillna(0)
    display_cols = [
        c for c in ["produkt", "keyword", "volume", "kd", "intent", "priority"]
        if c in tmp.columns
    ]
    parts = []
    for prod, g in tmp.groupby("produkt"):
        parts.append(g.nlargest(n_per, "volume")[display_cols])
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)


def build_ranking_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot ranking_bucket × produkt."""
    if "position_client" not in df.columns:
        return pd.DataFrame()
    tmp = df.copy()
    tmp["ranking_bucket"] = tmp["position_client"].apply(ranking_bucket)
    segment = "produkt" if "produkt" in tmp.columns else None
    if segment:
        tmp[segment] = tmp[segment].fillna("(prazdne)")
        pivot = (
            tmp.groupby(["ranking_bucket", segment])
            .size()
            .unstack(fill_value=0)
        )
    else:
        pivot = (
            tmp.groupby("ranking_bucket")
            .size()
            .to_frame(name="count")
        )
    # serad podle BUCKET_ORDER
    pivot = pivot.reindex(BUCKET_ORDER, fill_value=0).reset_index()
    return pivot


def write_with_chart(
    writer: pd.ExcelWriter,
    df: pd.DataFrame,
    sheet: str,
    chart_type: str = "bar",
    chart_title: str | None = None,
    value_col_idx: int = 1,
):
    """Zapise DataFrame a prida embedded chart. Pouziva xlsxwriter engine."""
    df.to_excel(writer, sheet_name=sheet, index=False)
    if df.empty:
        return
    ws = writer.sheets[sheet]
    workbook = writer.book
    chart = workbook.add_chart({"type": chart_type})
    n = len(df)
    # columns[0] = categories, columns[value_col_idx] = values
    chart.add_series({
        "name": df.columns[value_col_idx] if value_col_idx < len(df.columns) else "value",
        "categories": [sheet, 1, 0, n, 0],
        "values": [sheet, 1, value_col_idx, n, value_col_idx],
    })
    if chart_title:
        chart.set_title({"name": chart_title})
    chart.set_size({"width": 600, "height": 360})
    # vlozit za data (pod poslednim radkem + 2)
    ws.insert_chart(n + 2, 0, chart)


def main() -> int:
    parser = argparse.ArgumentParser(description="Faze 7: Dashboard")
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--input", type=Path, default=None,
                        help="Vstupni CSV (default: data/interim/keywords_enriched.csv)")
    parser.add_argument("--output", type=Path, default=None,
                        help="Vystupni XLSX (default: data/output/07_dashboard.xlsx)")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    interim_dir = project_root / "data" / "interim"
    output_dir = project_root / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    input_path = args.input or (interim_dir / "keywords_enriched.csv")
    output_path = args.output or (output_dir / "07_dashboard.xlsx")

    if not input_path.exists():
        # fallback — nekonzumuje enrichment
        fallback = interim_dir / "keywords_categorized.csv"
        if fallback.exists():
            log.warning("keywords_enriched.csv neexistuje — fallback na %s "
                        "(bez ranking distribuce)", fallback)
            input_path = fallback
        else:
            log.error("Nenalezen vstupni dataset (%s ani %s)", input_path, fallback)
            return 1

    log.info("Input:  %s", input_path)
    log.info("Output: %s", output_path)

    df = pd.read_csv(input_path, encoding="utf-8-sig", low_memory=False)
    log.info("Nacteno %d radku, %d sloupcu", len(df), len(df.columns))

    # zapiseme pres xlsxwriter engine (kvuli nativnim grafum)
    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        # 1. Overview
        overview = build_overview(df)
        overview.to_excel(writer, sheet_name="Overview", index=False)

        # 2-4. Distribuce
        dist1 = build_dist(df, "intent", "funnel")
        if not dist1.empty:
            dist1.to_excel(writer, sheet_name="Dist_Intent_Funnel", index=False)

        dist2 = build_dist(df, "produkt", "brand_type" if "brand_type" in df.columns else "intent")
        if not dist2.empty:
            dist2.to_excel(writer, sheet_name="Dist_Produkt_Brand", index=False)

        # Dist_Priority — count × priority
        if "priority" in df.columns:
            prio = df["priority"].fillna("(prazdne)").value_counts().reset_index()
            prio.columns = ["priority", "count"]
            write_with_chart(writer, prio, "Dist_Priority", "bar",
                             "Distribuce priority", value_col_idx=1)

        # 5-7. Top listy
        if "volume" in df.columns:
            top_vol = build_top_list(df, "volume", 100)
            top_vol.to_excel(writer, sheet_name="Top_Volume", index=False)

        cpc_cand = next((c for c in ["cpc", "CPC", "Google CPC [CZK]"] if c in df.columns), None)
        if cpc_cand:
            top_cpc = build_top_list(df, cpc_cand, 100)
            top_cpc.to_excel(writer, sheet_name="Top_CPC", index=False)

        top_val = build_top_value(df, 100)
        if not top_val.empty:
            top_val.to_excel(writer, sheet_name="Top_Value", index=False)

        # 8. Top per produkt
        top_per = build_top_per_produkt(df, 10)
        if not top_per.empty:
            top_per.to_excel(writer, sheet_name="Top_Per_Produkt", index=False)

        # 9. Ranking distribution
        rank_dist = build_ranking_distribution(df)
        if not rank_dist.empty:
            rank_dist.to_excel(writer, sheet_name="Ranking_Distribution", index=False)
            # pridam chart na samostatny Charts sheet
            workbook = writer.book
            ws_rank = writer.sheets["Ranking_Distribution"]
            chart = workbook.add_chart({"type": "column", "subtype": "stacked"})
            n = len(rank_dist)
            # kazdy sloupec krom prvniho (ranking_bucket) je segment
            for col_idx in range(1, len(rank_dist.columns)):
                chart.add_series({
                    "name": [ws_rank.name, 0, col_idx],
                    "categories": [ws_rank.name, 1, 0, n, 0],
                    "values": [ws_rank.name, 1, col_idx, n, col_idx],
                })
            chart.set_title({"name": "Ranking distribuce × segment"})
            chart.set_size({"width": 720, "height": 400})
            ws_rank.insert_chart(n + 2, 0, chart)

        # 10. Intent pie chart
        if "intent" in df.columns:
            intent_counts = df["intent"].fillna("(prazdne)").value_counts().reset_index()
            intent_counts.columns = ["intent", "count"]
            intent_counts.to_excel(writer, sheet_name="Charts_Intent", index=False)
            workbook = writer.book
            ws = writer.sheets["Charts_Intent"]
            chart = workbook.add_chart({"type": "pie"})
            n = len(intent_counts)
            chart.add_series({
                "name": "Intent distribution",
                "categories": ["Charts_Intent", 1, 0, n, 0],
                "values": ["Charts_Intent", 1, 1, n, 1],
                "data_labels": {"percentage": True},
            })
            chart.set_title({"name": "Intent distribuce"})
            chart.set_size({"width": 480, "height": 360})
            ws.insert_chart(n + 2, 0, chart)

    log.info("=" * 50)
    log.info("DASHBOARD HOTOVY: %s", output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
