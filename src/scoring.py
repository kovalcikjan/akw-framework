"""
Faze 9: Scoring

Prioritizacni vrstva — jediny oficialni prioritizacni mechanismus ve frameworku.
Deterministicky, transparentni model. Zadne AI.

priority_score = (
    business_value × 0.40 +
    ranking_probability × 0.35 +
    traffic_potential × 0.25
)

Vsechny komponenty jsou 0-10. Vysledek se mapuje na P1/P2/P3/P4 podle prahu.

Vstup:  data/interim/keywords_with_gap.csv (nebo keywords_enriched.csv)
Vystup: data/interim/keywords_scored.csv + data/output/09_scoring.xlsx
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


DEFAULT_WEIGHTS = {"business_value": 0.40, "ranking_probability": 0.35, "traffic_potential": 0.25}
DEFAULT_INTENT_SCORES = {"TRANS": 10, "COMM": 7, "INFO": 3, "NAV": 1}
DEFAULT_MONEY_BONUS = 2.0
DEFAULT_GAP_MODIFIER = {
    "quick_win": 1.5,
    "close_gap": 0.5,
    "content_gap": 0.0,
    "defended": 0.0,
    "no_opportunity": -2.0,
    "monitor": 0.0,
}
DEFAULT_TIERS = {"P1": 7.5, "P2": 5.0, "P3": 2.5}
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


def _to_float(v, default: float | None = None) -> float | None:
    if v is None or pd.isna(v):
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def compute_business_value(row, intent_scores: dict, money_bonus: float) -> float:
    intent = str(row.get("intent") or "").upper()
    base = float(intent_scores.get(intent, 0))
    if str(row.get("priority") or "") == "money_keyword":
        base += money_bonus
    return min(10.0, base)


def compute_ranking_probability(row, gap_modifier: dict) -> float:
    kd = _to_float(row.get("kd"), default=50.0)  # pokud KD neznamy, stredni hodnota
    pos = _to_float(row.get("position_client"), default=None)
    base = 10.0 - (kd / 10.0)
    # position bonus
    if pos is not None:
        if pos <= 10:
            base += 2.0
        elif pos <= 20:
            base += 1.0
    # gap_type modifier
    gt = str(row.get("gap_type") or "")
    base += float(gap_modifier.get(gt, 0.0))
    return max(0.0, min(10.0, base))


def compute_traffic_potential_raw(row, ctr_table: dict) -> float:
    """Raw value — bude se normalizovat pres min-max per dataset."""
    try:
        vol = float(row.get("volume") or 0)
    except (ValueError, TypeError):
        vol = 0.0
    if vol <= 0:
        return 0.0
    pos = _to_float(row.get("position_client"), default=None)
    if pos is None:
        # nerankuje — odhad po optimalizaci (pozice 10 × diskont 0.5)
        ctr = ctr_table.get(10, DEFAULT_CTR_FALLBACK) * 0.5
    else:
        p = int(round(pos))
        ctr = ctr_table.get(p, DEFAULT_CTR_FALLBACK)
    return np.log10(vol + 1) * ctr


def normalize_to_10(series: pd.Series) -> pd.Series:
    """Min-max normalizace na skalu 0-10. Pokud vse stejne, vrati 5."""
    lo, hi = series.min(), series.max()
    if pd.isna(lo) or pd.isna(hi) or hi - lo < 1e-9:
        return pd.Series(np.full(len(series), 5.0), index=series.index)
    return (series - lo) / (hi - lo) * 10.0


def assign_tier(score: float, tiers: dict) -> str:
    if score >= tiers.get("P1", 7.5):
        return "P1"
    if score >= tiers.get("P2", 5.0):
        return "P2"
    if score >= tiers.get("P3", 2.5):
        return "P3"
    return "P4"


def build_scoring_reason(bv, rp, tp, score, tier, row) -> str:
    parts = []
    intent = row.get("intent") or "?"
    priority = row.get("priority") or ""
    bv_note = intent
    if priority == "money_keyword":
        bv_note += "+money"
    parts.append(f"BV={bv:.1f} ({bv_note})")

    kd = _to_float(row.get("kd"))
    pos = _to_float(row.get("position_client"))
    gt = row.get("gap_type") or "?"
    rp_note_parts = []
    if kd is not None:
        rp_note_parts.append(f"KD={kd:.0f}")
    if pos is not None:
        rp_note_parts.append(f"pos={pos:.0f}")
    rp_note_parts.append(gt)
    parts.append(f"RP={rp:.1f} ({', '.join(rp_note_parts)})")

    vol = _to_float(row.get("volume"), default=0)
    parts.append(f"TP={tp:.1f} (vol={vol:.0f})")

    return f"{' | '.join(parts)} = {score:.2f} ({tier})"


def main() -> int:
    parser = argparse.ArgumentParser(description="Faze 9: Scoring")
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--output-csv", type=Path, default=None)
    parser.add_argument("--output-xlsx", type=Path, default=None)
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    interim_dir = project_root / "data" / "interim"
    output_dir = project_root / "data" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # input priority: with_gap → enriched → categorized
    input_path = args.input
    if input_path is None:
        for cand in ["keywords_with_gap.csv", "keywords_enriched.csv", "keywords_categorized.csv"]:
            p = interim_dir / cand
            if p.exists():
                input_path = p
                break
    if input_path is None or not input_path.exists():
        log.error("Nenalezen vstupni dataset v %s", interim_dir)
        return 1

    output_csv = args.output_csv or (interim_dir / "keywords_scored.csv")
    output_xlsx = args.output_xlsx or (output_dir / "09_scoring.xlsx")

    log.info("Input:  %s", input_path)
    log.info("Output CSV:  %s", output_csv)
    log.info("Output XLSX: %s", output_xlsx)

    params = load_params(project_root)
    scoring_cfg = params.get("scoring") or {}
    weights = {**DEFAULT_WEIGHTS, **(scoring_cfg.get("weights") or {})}
    intent_scores = {**DEFAULT_INTENT_SCORES, **(scoring_cfg.get("intent_scores") or {})}
    money_bonus = float(scoring_cfg.get("money_keyword_bonus", DEFAULT_MONEY_BONUS))
    gap_modifier = {**DEFAULT_GAP_MODIFIER, **(scoring_cfg.get("gap_modifier") or {})}
    # tier thresholds: preferuj tier_thresholds (new), fallback na tiers (old schema)
    tiers_from_cfg = scoring_cfg.get("tier_thresholds") or scoring_cfg.get("tiers") or {}
    tiers = {**DEFAULT_TIERS, **tiers_from_cfg}
    ctr_raw = scoring_cfg.get("ctr_estimates") or {}
    ctr_table = dict(DEFAULT_CTR)
    for k, v in ctr_raw.items():
        try:
            ctr_table[int(k)] = float(v)
        except (ValueError, TypeError):
            continue

    df = pd.read_csv(input_path, encoding="utf-8-sig", low_memory=False)
    log.info("Nacteno %d radku", len(df))

    # 1. business_value + ranking_probability
    bv_vals = df.apply(lambda r: compute_business_value(r, intent_scores, money_bonus), axis=1)
    rp_vals = df.apply(lambda r: compute_ranking_probability(r, gap_modifier), axis=1)

    # 2. traffic_potential raw + normalizace
    tp_raw = df.apply(lambda r: compute_traffic_potential_raw(r, ctr_table), axis=1)
    tp_norm = normalize_to_10(tp_raw)

    # 3. priority_score
    w_bv = weights["business_value"]
    w_rp = weights["ranking_probability"]
    w_tp = weights["traffic_potential"]
    score = bv_vals * w_bv + rp_vals * w_rp + tp_norm * w_tp

    df["business_value"] = bv_vals.round(2)
    df["ranking_probability"] = rp_vals.round(2)
    df["traffic_potential"] = tp_norm.round(2)
    df["priority_score"] = score.round(2)
    df["priority_tier"] = score.apply(lambda s: assign_tier(s, tiers))
    df["scoring_reason"] = [
        build_scoring_reason(bv_vals.iloc[i], rp_vals.iloc[i], tp_norm.iloc[i],
                             score.iloc[i], df["priority_tier"].iloc[i], df.iloc[i])
        for i in range(len(df))
    ]

    df_sorted = df.sort_values("priority_score", ascending=False).reset_index(drop=True)
    df_sorted.to_csv(output_csv, index=False, encoding="utf-8-sig")

    # issues
    issues = []
    for _, row in df_sorted.iterrows():
        if row["priority_tier"] == "P1" and str(row.get("gap_type") or "") == "no_opportunity":
            issues.append({"keyword": row.get("keyword"), "issue": "P1_NO_OPPORTUNITY",
                           "priority_score": row["priority_score"]})
        elif row["priority_tier"] == "P4" and str(row.get("priority") or "") == "money_keyword":
            issues.append({"keyword": row.get("keyword"), "issue": "P4_MONEY_KEYWORD",
                           "priority_score": row["priority_score"]})
    if issues:
        issues_df = pd.DataFrame(issues)
        issues_path = interim_dir / "scoring_issues.csv"
        issues_df.to_csv(issues_path, index=False, encoding="utf-8-sig")
        log.warning("Zjisteno %d scoring issues → %s", len(issues), issues_path)

    # XLSX
    display_cols = [
        c for c in [
            "keyword", "volume", "kd", "intent", "funnel", "produkt",
            "brand", "brand_type", "priority", "position_client",
            "best_competitor_position", "gap_type", "recommended_action",
            "business_value", "ranking_probability", "traffic_potential",
            "priority_score", "priority_tier", "scoring_reason",
        ]
        if c in df_sorted.columns
    ]
    view = df_sorted[display_cols]

    with pd.ExcelWriter(output_xlsx, engine="xlsxwriter") as writer:
        view.to_excel(writer, sheet_name="Scored", index=False)
        # Score_Breakdown
        breakdown_cols = [
            c for c in ["keyword", "volume", "intent", "priority", "gap_type",
                        "business_value", "ranking_probability", "traffic_potential",
                        "priority_score", "priority_tier"]
            if c in df_sorted.columns
        ]
        df_sorted[breakdown_cols].to_excel(writer, sheet_name="Score_Breakdown", index=False)
        # P1_Actionable
        p1 = view[view["priority_tier"] == "P1"]
        p1.to_excel(writer, sheet_name="P1_Actionable", index=False)
        # Tier_Summary pivot
        segment = "produkt" if "produkt" in df_sorted.columns else None
        if segment:
            tmp = df_sorted.copy()
            tmp[segment] = tmp[segment].fillna("(prazdne)")
            summary = (
                tmp.groupby(["priority_tier", segment])
                .size()
                .unstack(fill_value=0)
                .reset_index()
            )
        else:
            summary = (
                df_sorted.groupby("priority_tier")
                .size()
                .reset_index(name="count")
            )
        summary.to_excel(writer, sheet_name="Tier_Summary", index=False)
        # Methodology
        method_rows = [
            ["Weight business_value", w_bv],
            ["Weight ranking_probability", w_rp],
            ["Weight traffic_potential", w_tp],
            ["Money keyword bonus", money_bonus],
            ["Tier P1 threshold", tiers.get("P1")],
            ["Tier P2 threshold", tiers.get("P2")],
            ["Tier P3 threshold", tiers.get("P3")],
        ]
        for intent, sc in intent_scores.items():
            method_rows.append([f"Intent score {intent}", sc])
        for gt, mod in gap_modifier.items():
            method_rows.append([f"Gap modifier {gt}", mod])
        pd.DataFrame(method_rows, columns=["Parameter", "Value"]).to_excel(
            writer, sheet_name="Methodology", index=False
        )

    # summary
    log.info("=" * 50)
    log.info("SCORING HOTOVO")
    tc = df_sorted["priority_tier"].value_counts()
    for t in ["P1", "P2", "P3", "P4"]:
        log.info("  %s: %d (%.1f %%)", t, int(tc.get(t, 0)),
                 tc.get(t, 0) / len(df_sorted) * 100 if len(df_sorted) else 0)
    if issues:
        log.warning("  %d scoring issues (viz scoring_issues.csv)", len(issues))
    return 0


if __name__ == "__main__":
    sys.exit(main())
