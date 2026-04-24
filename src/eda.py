"""Faze 2: EDA — Exploratory Data Analysis.

Plain Python script (no Jupyter by default). Reads keywords_raw.csv,
analyzes data, outputs eda_summary.json for AI to read and walk user
through results.

Auto mode — runs without interaction, AI interprets results afterwards.

Outputs:
  - data/interim/eda_summary.json (structured results for AI)
  - Terminal output (human-readable summary)
  - Optional: notebooks/01_eda.ipynb (--notebook flag) pro user co chce
    dal stourat interaktivne v Jupyter/VS Code

Usage:
    python src/eda.py                             # default: stdout + JSON
    python src/eda.py --input data/interim/keywords_raw.csv
    python src/eda.py --notebook                  # + .ipynb
"""

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

CZECH_STOPWORDS = {
    "a", "i", "k", "o", "s", "v", "z", "na", "do", "se", "je", "to",
    "za", "co", "si", "pro", "jak", "ale", "ani", "pod", "nad", "po",
    "od", "ze", "ve", "ke", "bez", "pri", "pred", "nebo",
}


def load_params(project_root: Path) -> dict:
    """Load params.yaml."""
    path = project_root / "params.yaml"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def get_ngrams(
    texts: list[str], n: int = 1, top: int = 30
) -> list[tuple[str, int]]:
    """Extract top n-grams from keyword list."""
    ngrams: list[str] = []
    for text in texts:
        words = [
            w for w in str(text).lower().split()
            if w not in CZECH_STOPWORDS and len(w) > 1
        ]
        for i in range(len(words) - n + 1):
            ngrams.append(" ".join(words[i : i + n]))
    return Counter(ngrams).most_common(top)


def remove_diacritics_simple(text: str) -> str:
    """Simple diacritics removal for comparison only."""
    table = str.maketrans(
        "\u00e1\u00e4\u010d\u010f\u00e9\u011b\u00ed\u013a\u013e\u0148"
        "\u00f3\u00f4\u0155\u0159\u0161\u0165\u00fa\u016f\u00fd\u017e",
        "aacdeeillnoorrstuuyz",
    )
    return str(text).translate(table)


def analyze(input_path: Path, params: dict) -> dict:
    """Run full EDA analysis. Returns structured summary dict."""
    df = pd.read_csv(input_path, encoding="utf-8-sig")
    kw_col = "keyword_normalized" if "keyword_normalized" in df.columns else "keyword"
    keywords = df[kw_col].astype(str).tolist()

    summary: dict = {
        "input_file": str(input_path),
        "total_keywords": len(df),
        "columns": list(df.columns),
    }

    # --- 1. Basic overview ---
    overview: dict = {
        "total": len(df),
        "unique": df[kw_col].nunique(),
        "duplicates": len(df) - df[kw_col].nunique(),
    }

    # Sources
    if "source" in df.columns:
        source_counts: dict[str, int] = {}
        for val in df["source"].dropna().astype(str):
            for s in val.split("|"):
                s = s.strip()
                if s:
                    source_counts[s] = source_counts.get(s, 0) + 1
        overview["sources"] = source_counts
        overview["source_count"] = len(source_counts)

        # Source overlap
        df["_src_cnt"] = df["source"].apply(
            lambda x: len(set(str(x).split("|"))) if pd.notna(x) else 1
        )
        overview["multi_source_keywords"] = int((df["_src_cnt"] > 1).sum())
        overview["multi_source_pct"] = round(
            (df["_src_cnt"] > 1).sum() / len(df) * 100, 1
        )
        df.drop(columns=["_src_cnt"], inplace=True)

    # Volume
    if "volume" in df.columns:
        vol = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
        overview["volume"] = {
            "min": int(vol.min()),
            "max": int(vol.max()),
            "median": int(vol.median()),
            "mean": int(vol.mean()),
            "total": int(vol.sum()),
            "zero_count": int((vol <= 0).sum()),
            "zero_pct": round((vol <= 0).sum() / len(df) * 100, 1),
        }
        # Buckets
        buckets = [0, 10, 50, 100, 500, 1000, 5000, float("inf")]
        labels = ["0-10", "10-50", "50-100", "100-500", "500-1K", "1K-5K", "5K+"]
        cuts = pd.cut(vol, bins=buckets, labels=labels, right=False)
        overview["volume"]["buckets"] = {
            label: int((cuts == label).sum()) for label in labels
        }

    # KD
    if "kd" in df.columns:
        kd = pd.to_numeric(df["kd"], errors="coerce").dropna()
        if len(kd) > 0:
            overview["kd"] = {
                "min": int(kd.min()),
                "max": int(kd.max()),
                "median": int(kd.median()),
                "easy_lt30": int((kd < 30).sum()),
                "medium_30_60": int(((kd >= 30) & (kd < 60)).sum()),
                "hard_60plus": int((kd >= 60).sum()),
            }

    summary["overview"] = overview

    # --- 2. Data quality ---
    quality: dict = {}

    # Duplicate examples
    dupes = df[df.duplicated(subset=kw_col, keep=False)]
    if len(dupes) > 0:
        dupe_groups = (
            dupes.groupby(kw_col)["keyword"]
            .apply(lambda x: list(x.unique()[:5]))
            .to_dict()
        )
        # Top 10 by group size
        top_dupes = sorted(dupe_groups.items(), key=lambda x: -len(x[1]))[:10]
        quality["duplicate_examples"] = [
            {"keyword": k, "count": len(v), "variants": v} for k, v in top_dupes
        ]

    # Diacritics variant preview
    df["_nd"] = df[kw_col].apply(remove_diacritics_simple)
    diac_groups = df.groupby("_nd")[kw_col].nunique()
    diac_multi = diac_groups[diac_groups > 1]
    quality["diacritics_groups"] = len(diac_multi)

    diac_examples: list[dict] = []
    for key in diac_multi.nlargest(10).index:
        variants = df[df["_nd"] == key][kw_col].unique().tolist()
        vol_sum = int(df[df["_nd"] == key]["volume"].sum()) if "volume" in df.columns else 0
        diac_examples.append({
            "key": key,
            "variants": variants,
            "volume_sum": vol_sum,
        })
    quality["diacritics_examples"] = diac_examples

    # Word-order variant preview
    df["_ws"] = df["_nd"].apply(lambda x: " ".join(sorted(str(x).split())))
    wo_groups = df.groupby("_ws")[kw_col].nunique()
    wo_multi = wo_groups[wo_groups > 1]
    quality["word_order_groups"] = len(wo_multi)

    wo_examples: list[dict] = []
    for key in wo_multi.nlargest(10).index:
        variants = df[df["_ws"] == key][kw_col].unique().tolist()
        if len(variants) > 1:
            wo_examples.append({"variants": variants[:5]})
    quality["word_order_examples"] = wo_examples[:10]

    quality["estimated_dedup_merges"] = len(diac_multi) + len(wo_multi)

    # Outliers (top volume)
    if "volume" in df.columns:
        top_vol = df.nlargest(15, "volume")[[kw_col, "volume"]].to_dict("records")
        quality["top_volume"] = top_vol

    df.drop(columns=["_nd", "_ws"], inplace=True)
    summary["quality"] = quality

    # --- 3. N-grams ---
    ngrams: dict = {}
    for n, label, top in [(1, "unigrams", 30), (2, "bigrams", 20), (3, "trigrams", 15)]:
        result = get_ngrams(keywords, n=n, top=top)
        ngrams[label] = [{"gram": g, "count": c} for g, c in result]

    summary["ngrams"] = ngrams

    # --- 4. Coverage checks ---
    coverage: dict = {}

    # Products from params.yaml
    products = params.get("relevance", {}).get("products", [])
    if products:
        product_coverage: list[dict] = []
        for product in products:
            p = str(product).lower()
            p_nd = remove_diacritics_simple(p)
            count = df[kw_col].str.contains(p, na=False, regex=False).sum()
            if count == 0:
                count = df[kw_col].apply(remove_diacritics_simple).str.contains(
                    p_nd, na=False, regex=False
                ).sum()
            product_coverage.append({
                "product": product,
                "keyword_count": int(count),
                "status": "OK" if count > 0 else "MISSING",
            })
        coverage["products"] = product_coverage

    # Competitors from params.yaml
    competitors = params.get("relevance", {}).get("competitors", [])
    if competitors:
        comp_coverage: list[dict] = []
        for comp in competitors:
            c = str(comp).lower()
            mask = df[kw_col].str.contains(c, na=False, regex=False)
            count = int(mask.sum())
            vol = int(df.loc[mask, "volume"].sum()) if "volume" in df.columns and count > 0 else 0
            comp_coverage.append({
                "competitor": comp,
                "keyword_count": count,
                "volume_sum": vol,
            })
        coverage["competitors"] = comp_coverage

    summary["coverage"] = coverage

    # --- 5. Intent signals ---
    intent_signals = {
        "INFO": ["jak", "co", "proc", "navod", "pruvodce", "rozdil", "postup", "typy"],
        "COMM": ["nejlepsi", "porovnani", "recenze", "hodnoceni", "test", "vs", "srovnani"],
        "TRANS": ["cena", "koupit", "objednat", "eshop", "sleva", "akce", "levne", "kalkulacka"],
        "NAV": ["kontakt", "login", "pobocka", "prihlaseni"],
    }

    uni_dict = dict(get_ngrams(keywords, n=1, top=200))
    intent_found: dict[str, dict] = {}
    for intent, signals in intent_signals.items():
        found = {s: uni_dict[s] for s in signals if s in uni_dict}
        intent_found[intent] = {
            "total": sum(found.values()),
            "signals": found,
        }
    summary["intent_signals"] = intent_found

    # --- 6. Keyword length ---
    word_counts = df[kw_col].str.split().str.len()
    summary["keyword_length"] = {
        "median_words": int(word_counts.median()),
        "single_word": int((word_counts == 1).sum()),
        "long_tail_4plus": int((word_counts >= 4).sum()),
        "long_tail_pct": round((word_counts >= 4).sum() / len(df) * 100, 1),
    }

    return summary


def print_summary(s: dict) -> None:
    """Print human-readable summary to terminal."""
    ov = s["overview"]
    log.info("=" * 60)
    log.info("EDA SUMMARY: %s", s["input_file"])
    log.info("=" * 60)

    # Overview
    log.info("Total: %d keywords, %d unique, %d duplicates",
             ov["total"], ov["unique"], ov["duplicates"])
    if "sources" in ov:
        log.info("Sources (%d):", ov["source_count"])
        for src, cnt in sorted(ov["sources"].items(), key=lambda x: -x[1]):
            log.info("  %-30s %d", src, cnt)
        log.info("Multi-source keywords: %d (%.1f%%)", ov["multi_source_keywords"], ov["multi_source_pct"])
    if "volume" in ov:
        v = ov["volume"]
        log.info("Volume: min=%d, max=%d, median=%d, mean=%d, total=%d",
                 v["min"], v["max"], v["median"], v["mean"], v["total"])
        log.info("Zero volume: %d (%.1f%%)", v["zero_count"], v["zero_pct"])
        log.info("Buckets:")
        for label, cnt in v["buckets"].items():
            log.info("  %-10s %d", label, cnt)
    if "kd" in ov:
        k = ov["kd"]
        log.info("KD: median=%d, easy(<30)=%d, medium(30-60)=%d, hard(60+)=%d",
                 k["median"], k["easy_lt30"], k["medium_30_60"], k["hard_60plus"])

    # Quality
    q = s["quality"]
    log.info("")
    log.info("DEDUP PREVIEW:")
    log.info("  Diacritics groups to merge: %d", q["diacritics_groups"])
    for ex in q.get("diacritics_examples", [])[:5]:
        log.info("    %s (vol: %d)", " | ".join(ex["variants"]), ex["volume_sum"])
    log.info("  Word-order groups: %d", q["word_order_groups"])
    log.info("  Estimated total merges: ~%d", q["estimated_dedup_merges"])

    # N-grams
    log.info("")
    log.info("UNI-GRAMY (top 15):")
    for item in s["ngrams"]["unigrams"][:15]:
        log.info("  %-25s %d", item["gram"], item["count"])
    log.info("")
    log.info("BI-GRAMY (top 10):")
    for item in s["ngrams"]["bigrams"][:10]:
        log.info("  %-35s %d", item["gram"], item["count"])
    log.info("")
    log.info("TRI-GRAMY (top 5):")
    for item in s["ngrams"]["trigrams"][:5]:
        log.info("  %-45s %d", item["gram"], item["count"])

    # Coverage
    cov = s.get("coverage", {})
    if "products" in cov:
        log.info("")
        log.info("PRODUCT COVERAGE:")
        missing = [p for p in cov["products"] if p["status"] == "MISSING"]
        for p in cov["products"]:
            log.info("  [%s] %-25s %d keywords", p["status"], p["product"], p["keyword_count"])
        if missing:
            log.info("  MISSING products: %s", [p["product"] for p in missing])
    if "competitors" in cov:
        log.info("")
        log.info("COMPETITOR COVERAGE:")
        for c in cov["competitors"]:
            log.info("  %-25s %d keywords (vol: %d)", c["competitor"], c["keyword_count"], c["volume_sum"])

    # Intent
    log.info("")
    log.info("INTENT SIGNALS:")
    for intent, data in s["intent_signals"].items():
        if data["total"] > 0:
            sigs = ", ".join(f"{k}({v})" for k, v in data["signals"].items())
            log.info("  %-6s %4dx — %s", intent, data["total"], sigs)

    # Length
    kl = s["keyword_length"]
    log.info("")
    log.info("KEYWORD LENGTH: median %d words, single-word: %d, long-tail(4+): %d (%.1f%%)",
             kl["median_words"], kl["single_word"], kl["long_tail_4plus"], kl["long_tail_pct"])

    log.info("")
    log.info("DONE. AI will walk you through the results.")


def generate_notebook(notebook_path: Path, input_path: Path) -> None:
    """Optional: vygeneruje .ipynb pro user co chce dal stourat."""
    nb = {
        "cells": [
            {"cell_type": "markdown", "metadata": {},
             "source": ["# EDA — interactive notebook\n",
                        f"Vstup: `{input_path}`\n",
                        "\nPython script `src/eda.py` uz bezi automaticky, tento notebook je pro deeper dive."]},
            {"cell_type": "code", "metadata": {}, "outputs": [], "execution_count": None,
             "source": ["import pandas as pd\n",
                        "import matplotlib.pyplot as plt\n",
                        f"df = pd.read_csv(r'{input_path}', encoding='utf-8-sig')\n",
                        "df.head()\n"]},
            {"cell_type": "code", "metadata": {}, "outputs": [], "execution_count": None,
             "source": ["df.describe()\n"]},
            {"cell_type": "code", "metadata": {}, "outputs": [], "execution_count": None,
             "source": ["# Source breakdown\n",
                        "df['source'].value_counts() if 'source' in df.columns else 'N/A'\n"]},
            {"cell_type": "code", "metadata": {}, "outputs": [], "execution_count": None,
             "source": ["# Volume histogram\n",
                        "if 'volume' in df.columns:\n",
                        "    pd.to_numeric(df['volume'], errors='coerce').hist(bins=50, log=True)\n",
                        "    plt.title('Volume distribution')\n",
                        "    plt.show()\n"]},
            {"cell_type": "markdown", "metadata": {},
             "source": ["## Doplnuj si vlastni bunky podle potreby\n"]},
        ],
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python", "version": "3"}},
        "nbformat": 4, "nbformat_minor": 5,
    }
    notebook_path.parent.mkdir(parents=True, exist_ok=True)
    with open(notebook_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="EDA analysis for keyword research")
    parser.add_argument("--input", type=Path, default=Path("data/interim/keywords_raw.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/interim/eda_summary.json"))
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--notebook", action="store_true",
                        help="Dodatecne vygeneruj notebooks/01_eda.ipynb pro interaktivni pruzkum")
    args = parser.parse_args()

    if not args.input.exists():
        log.error("Input not found: %s", args.input)
        sys.exit(1)

    params = load_params(args.project_root)
    summary = analyze(args.input, params)

    # Save JSON
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    log.info("Saved EDA summary to %s", args.output)

    # Print to terminal
    print_summary(summary)

    # Optional notebook
    if args.notebook:
        nb_path = args.project_root / "notebooks" / "01_eda.ipynb"
        generate_notebook(nb_path, args.input)
        log.info("Generated notebook: %s", nb_path)
        log.info("  Spust: jupyter notebook %s  (nebo otevri ve VS Code)", nb_path)


if __name__ == "__main__":
    main()
