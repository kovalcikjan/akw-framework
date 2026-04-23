"""
Faze 8: Competitive Gap

Rule-based diagnostika — priradi kazdemu KW gap_type a recommended_action.
Odpovida na otazku "kde je mezera proti trhu".

NENI to finalni prioritizace (to je faze 9). Vystup se bere jako vstup
do scoringu, kde gap_type moduluje ranking_probability.

Vstup:  data/interim/keywords_enriched.csv
Vystup: data/interim/keywords_with_gap.csv + data/output/08_gap.xlsx
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


DEFAULT_GAP = {
    "quick_win_position_range": [4, 20],
    "close_gap_position_range": [21, 50],
    "quick_win_max_kd": 40,
    "competitor_top_threshold": 3,
}


DEFAULT_CTR = {
    1: 0.31, 2: 0.15, 3: 0.10, 4: 0.07, 5: 0.05,
    6: 0.04, 7: 0.03, 8: 0.025, 9: 0.02, 10: 0.02,
}
DEFAULT_CTR_FALLBACK = 0.005


def load_params(project_root: Path) -> dict:
    path = project_root / "params.yaml"
    if not path.exists():
        log.warning("params.yaml not found at %s — using defaults", path)
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def classify_gap(
    pos_client: float | None,
    pos_comp: float | None,
    kd: float | None,
    cfg: dict,
) -> str:
    """Ordered decision tree pro gap_type.

    Poradi rozhodovani je dulezite — prvni match vyhrava.
    """
    qw_lo, qw_hi = cfg["quick_win_position_range"]
    cg_lo, cg_hi = cfg["close_gap_position_range"]
    qw_kd = cfg["quick_win_max_kd"]
    comp_top = cfg["competitor_top_threshold"]

    # 1. defended — klient v top 3
    if pos_client is not None and pos_client <= 3:
        return "defended"

    # 2. quick_win — klient 4-20 + konkurent v top N + nizke KD
    if (pos_client is not None
            and qw_lo <= pos_client <= qw_hi
            and pos_comp is not None
            and pos_comp <= comp_top
            and (kd is None or kd <= qw_kd)):
        return "quick_win"

    # 3. close_gap — klient 21-50 + konkurent v top 10
    if (pos_client is not None
            and cg_lo <= pos_client <= cg_hi
            and pos_comp is not None
            and pos_comp <= 10):
        return "close_gap"

    # 4. content_gap — klient nerankuje + konkurent v top 10
    if pos_client is None and pos_comp is not None and pos_comp <= 10:
        return "content_gap"

    # 5. no_opportunity — nikdo nerankuje v top 10, nebo vysoke KD defense
    if pos_comp is None and pos_client is None:
        return "no_opportunity"
    if pos_client is not None and pos_client <= 3 and pos_comp is not None and pos_comp <= 3 and kd is not None and kd > 70:
        return "no_opportunity"

    # 6. monitor — default fallback
    return "monitor"


ACTION_MAP = {
    "quick_win": "optimize_existing",
    "close_gap": "optimize_existing",
    "content_gap": "create_new_page",
    "defended": "monitor",
    "no_opportunity": "skip",
    "monitor": "monitor",
}


def ctr_for_position(pos: float | None, ctr_table: dict) -> float:
    """Vrati CTR pro danou pozici. None → fallback (nerankuje)."""
    if pos is None or pd.isna(pos):
        return 0.0  # nerankuje = 0 trafficu
    p_int = int(round(pos))
    if p_int in ctr_table:
        return float(ctr_table[p_int])
    return DEFAULT_CTR_FALLBACK


def compute_gap_traffic(row, ctr_table) -> int:
    """Odhad ztraceneho trafficu = volume × (CTR_best_competitor − CTR_client)."""
    try:
        vol = float(row.get("volume") or 0)
    except (ValueError, TypeError):
        return 0
    if vol <= 0:
        return 0
    ctr_client = ctr_for_position(row.get("position_client"), ctr_table)
    ctr_comp = ctr_for_position(row.get("best_competitor_position"), ctr_table)
    delta = ctr_comp - ctr_client
    if delta <= 0:
        return 0
    return int(round(vol * delta))


def _to_float_or_none(v):
    if v is None or pd.isna(v):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Faze 8: Competitive Gap")
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--output-csv", type=Path, default=None)
    parser.add_argument("--output-xlsx", type=Path, default=None)
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    interim_dir = project_root / "data" / "interim"
    output_dir = project_root / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    input_path = args.input or (interim_dir / "keywords_enriched.csv")
    output_csv = args.output_csv or (interim_dir / "keywords_with_gap.csv")
    output_xlsx = args.output_xlsx or (output_dir / "08_gap.xlsx")

    if not input_path.exists():
        log.error("Nenalezen %s — spust nejdrive serp_enrichment.py", input_path)
        return 1

    log.info("Input:  %s", input_path)
    log.info("Output CSV:  %s", output_csv)
    log.info("Output XLSX: %s", output_xlsx)

    params = load_params(project_root)
    gap_cfg = {**DEFAULT_GAP, **(params.get("gap") or {})}
    ctr_cfg_raw = (params.get("scoring") or {}).get("ctr_estimates") or {}
    # klice mohou byt int nebo str v YAML — normalizuj
    ctr_table = {}
    for k, v in ctr_cfg_raw.items():
        try:
            ctr_table[int(k)] = float(v)
        except (ValueError, TypeError):
            continue
    if not ctr_table:
        ctr_table = dict(DEFAULT_CTR)

    df = pd.read_csv(input_path, encoding="utf-8-sig", low_memory=False)
    log.info("Nacteno %d radku", len(df))

    # ensure required columns
    for col in ["position_client", "best_competitor_position", "volume"]:
        if col not in df.columns:
            df[col] = pd.NA

    # klasifikace radek po radce
    gap_types = []
    actions = []
    traffic_potentials = []
    for _, row in df.iterrows():
        pos_c = _to_float_or_none(row.get("position_client"))
        pos_comp = _to_float_or_none(row.get("best_competitor_position"))
        kd = _to_float_or_none(row.get("kd"))
        gt = classify_gap(pos_c, pos_comp, kd, gap_cfg)
        gap_types.append(gt)
        actions.append(ACTION_MAP.get(gt, "monitor"))
        traffic_potentials.append(compute_gap_traffic(row, ctr_table))

    df["gap_type"] = gap_types
    df["recommended_action"] = actions
    df["gap_traffic_potential"] = traffic_potentials

    df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    # XLSX multi-sheet
    display_cols = [
        c for c in [
            "keyword", "volume", "kd", "intent", "funnel", "produkt",
            "brand_type", "priority", "position_client",
            "best_competitor_position", "best_competitor_domain",
            "gap_type", "recommended_action", "gap_traffic_potential",
        ]
        if c in df.columns
    ]
    view = df[display_cols].copy()

    with pd.ExcelWriter(output_xlsx, engine="xlsxwriter") as writer:
        # All_Gaps (master)
        view.sort_values("gap_traffic_potential", ascending=False).to_excel(
            writer, sheet_name="All_Gaps", index=False
        )
        # Quick_Wins
        qw = view[view["gap_type"] == "quick_win"].sort_values(
            "gap_traffic_potential", ascending=False
        )
        qw.to_excel(writer, sheet_name="Quick_Wins", index=False)
        # Close_Gaps
        cg = view[view["gap_type"] == "close_gap"].sort_values(
            "gap_traffic_potential", ascending=False
        )
        cg.to_excel(writer, sheet_name="Close_Gaps", index=False)
        # Content_Gaps
        cg2 = view[view["gap_type"] == "content_gap"].sort_values(
            "volume", ascending=False
        )
        cg2.to_excel(writer, sheet_name="Content_Gaps", index=False)
        # Defended
        dg = view[view["gap_type"] == "defended"].sort_values(
            "volume", ascending=False
        )
        dg.to_excel(writer, sheet_name="Defended", index=False)

        # Gap_Summary — pivot gap_type × produkt
        segment = "produkt" if "produkt" in df.columns else None
        if segment:
            tmp = df.copy()
            tmp[segment] = tmp[segment].fillna("(prazdne)")
            summary = (
                tmp.groupby(["gap_type", segment])
                .size()
                .unstack(fill_value=0)
                .reset_index()
            )
        else:
            summary = (
                df.groupby("gap_type")
                .size()
                .reset_index(name="count")
            )
        summary.to_excel(writer, sheet_name="Gap_Summary", index=False)

    # summary logging
    log.info("=" * 50)
    log.info("GAP ANALYSIS HOTOVA")
    vc = pd.Series(gap_types).value_counts()
    for gt in ["quick_win", "close_gap", "content_gap", "defended", "no_opportunity", "monitor"]:
        count = int(vc.get(gt, 0))
        log.info("  %-16s %d", gt, count)
    total_traffic = sum(traffic_potentials)
    log.info("  total gap traffic potential: %d visits/month", total_traffic)
    return 0


if __name__ == "__main__":
    sys.exit(main())
