"""Faze 2: Generate EDA Jupyter notebook tailored to the project.

Creates notebook with distribution analysis, n-grams, dedup preview,
source overlap, competitor coverage, and recommendations for phases 3-5.

Can also run as plain Python script (--run-as-script).

Usage:
    python src/eda_notebook_generator.py
    python src/eda_notebook_generator.py --input data/interim/keywords_raw.csv
    python src/eda_notebook_generator.py --run-as-script
"""

import argparse
import json
import logging
from pathlib import Path

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def load_params(project_root: Path) -> dict:
    """Load params.yaml."""
    params_path = project_root / "params.yaml"
    if params_path.exists():
        with open(params_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def make_cell(cell_type: str, source: str | list[str], **kwargs) -> dict:
    """Create a notebook cell."""
    if isinstance(source, str):
        source = source.split("\n")
        source = [line + "\n" for line in source[:-1]] + [source[-1]]

    cell = {
        "cell_type": cell_type,
        "metadata": kwargs.get("metadata", {}),
        "source": source,
    }
    if cell_type == "code":
        cell["execution_count"] = None
        cell["outputs"] = []
    return cell


def generate_notebook(input_csv: str, params: dict) -> dict:
    """Generate EDA notebook content."""
    client_name = params.get("client", {}).get("name", "PROJECT")
    products = params.get("relevance", {}).get("products", [])
    excluded = params.get("relevance", {}).get("excluded", [])
    competitors = params.get("relevance", {}).get("competitors", [])
    blacklist = params.get("filters", {}).get("blacklist", [])

    cells = []

    # --- Title ---
    cells.append(make_cell("markdown", f"""# EDA: {client_name} - Keyword Analysis

Automaticky generovany notebook. Projdi vysledky s AI — sekce po sekci.

**Workflow:** Spust vsechny bunky (Run All) → vrat se do Claude Code → AI te provede vysledky."""))

    # --- Imports + load ---
    cells.append(make_cell("code", f"""import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter
import re
import warnings
warnings.filterwarnings('ignore')

plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 11
plt.style.use('seaborn-v0_8-whitegrid')

DIACRITICS_MAP = str.maketrans(
    "acdeeillnoorrsuuyzACDEEILLNOORRSUUYZ",
    "acdeeillnoorrsuuyzACDEEILLNOORRSUUYZ",
)

def remove_diacritics(text):
    MAP = str.maketrans(
        "\\u00e1\\u00e4\\u010d\\u010f\\u00e9\\u011b\\u00ed\\u013a\\u013e\\u0148\\u00f3\\u00f4\\u0155\\u0159\\u0161\\u0165\\u00fa\\u016f\\u00fd\\u017e",
        "aacdeeillnoorrstuuyz",
    )
    return str(text).translate(MAP)

def has_diacritics(text):
    return text != remove_diacritics(text)

CZECH_STOPWORDS = {{
    'a', 'i', 'k', 'o', 's', 'v', 'z', 'na', 'do', 'se', 'je', 'to',
    'za', 'co', 'si', 'pro', 'jak', 'ale', 'ani', 'pod', 'nad', 'po',
    'od', 'ze', 've', 'ke', 'bez', 'pri', 'pred', 'nebo', 'the', 'and',
    'for', 'with', 'from',
}}

def get_ngrams(texts, n=1, top=30, remove_stops=True):
    ngrams = []
    for text in texts:
        words = str(text).lower().split()
        if remove_stops:
            words = [w for w in words if w not in CZECH_STOPWORDS and len(w) > 1]
        for i in range(len(words) - n + 1):
            ngrams.append(' '.join(words[i:i+n]))
    return Counter(ngrams).most_common(top)

# Load data
df = pd.read_csv("{input_csv}", encoding="utf-8-sig")
keywords = df['keyword_normalized'].tolist()
print(f"Loaded {{len(df)}} keywords")
print(f"Columns: {{list(df.columns)}}")
df.head(10)"""))

    # --- 2.1 Basic overview ---
    cells.append(make_cell("markdown", "## 2.1 Zakladni prehled dat"))

    cells.append(make_cell("code", """print(f"Total keywords: {len(df)}")
print(f"Unique normalized: {df['keyword_normalized'].nunique()}")
if 'source' in df.columns:
    print(f"Sources: {df['source'].nunique()}")

# Source breakdown
if 'source' in df.columns:
    print("\\nKeywords per source:")
    source_counts = {}
    for sources_str in df['source']:
        for s in str(sources_str).split('|'):
            s = s.strip()
            if s:
                source_counts[s] = source_counts.get(s, 0) + 1
    for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        pct = count / len(df) * 100
        bar = '#' * int(pct / 2)
        print(f"  {src:<30s} {count:>5d} ({pct:>5.1f}%) {bar}")"""))

    cells.append(make_cell("code", """# Volume distribution
if 'volume' in df.columns:
    vol = df['volume']
    print("Volume stats:")
    print(f"  Min:       {vol.min()}")
    print(f"  Max:       {vol.max()}")
    print(f"  Median:    {vol.median():.0f}")
    print(f"  Mean:      {vol.mean():.0f}")
    print(f"  Zero/null: {(vol <= 0).sum()} ({(vol <= 0).sum()/len(df)*100:.1f}%)")
    print()

    # Volume buckets
    buckets = [0, 10, 50, 100, 500, 1000, 5000, float('inf')]
    labels = ['0-10', '10-50', '50-100', '100-500', '500-1K', '1K-5K', '5K+']
    df['_vol_bucket'] = pd.cut(vol, bins=buckets, labels=labels, right=False)

    print("Volume distribution:")
    for label in labels:
        count = (df['_vol_bucket'] == label).sum()
        pct = count / len(df) * 100
        bar = '#' * int(pct)
        print(f"  {label:>10s}: {count:>5d} ({pct:>5.1f}%) {bar}")

    # Histogram
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    vol_nonzero = vol[vol > 0]
    if len(vol_nonzero) > 0:
        axes[0].hist(vol_nonzero, bins=50, edgecolor='black', alpha=0.7)
        axes[0].set_title('Volume Distribution (linear)')
        axes[0].set_xlabel('Search Volume')
        axes[1].hist(np.log10(vol_nonzero + 1), bins=50, edgecolor='black', alpha=0.7, color='orange')
        axes[1].set_title('Volume Distribution (log10)')
        axes[1].set_xlabel('log10(Search Volume)')
    plt.tight_layout()
    plt.show()

    df.drop(columns=['_vol_bucket'], inplace=True)
else:
    print("No volume column found")"""))

    # --- Source overlap ---
    cells.append(make_cell("markdown", "### Source overlap (keywords z vice zdroju)"))
    cells.append(make_cell("code", """# Source overlap — keywords from multiple sources are stronger signals
if 'source' in df.columns:
    df['_source_count'] = df['source'].apply(lambda x: len(set(str(x).split('|'))))
    multi = df[df['_source_count'] > 1]
    print(f"Keywords z 1 zdroje:   {(df['_source_count'] == 1).sum()}")
    print(f"Keywords z 2+ zdroju:  {len(multi)} ({len(multi)/len(df)*100:.1f}%) — silnejsi signal")
    print(f"Keywords z 3+ zdroju:  {(df['_source_count'] >= 3).sum()}")

    if len(multi) > 0:
        print(f"\\nTop 10 keywords z nejvice zdroju:")
        top_multi = multi.nlargest(10, '_source_count')[['keyword', '_source_count', 'volume', 'source']]
        display(top_multi)

    df.drop(columns=['_source_count'], inplace=True)
else:
    print("No source column")"""))

    # --- 2.2 Data quality ---
    cells.append(make_cell("markdown", "## 2.2 Kvalita dat"))

    cells.append(make_cell("code", """# Duplicate analysis
print("Duplicate analysis:")
total = len(df)
unique_exact = df['keyword'].nunique()
unique_norm = df['keyword_normalized'].nunique()
print(f"  Total:               {total}")
print(f"  Unique (exact):      {unique_exact} (dupes: {total - unique_exact})")
print(f"  Unique (normalized): {unique_norm} (dupes: {total - unique_norm})")

# Show top duplicate groups
dupes = df[df.duplicated(subset='keyword_normalized', keep=False)]
if len(dupes) > 0:
    print(f"\\nTop 10 duplicate groups:")
    agg = {'keyword': ['count', lambda x: ' | '.join(x.unique()[:5])]}
    if 'volume' in df.columns:
        agg['volume'] = 'sum'
    dupe_groups = dupes.groupby('keyword_normalized').agg(agg)
    dupe_groups.columns = ['count', 'variants'] + (['total_vol'] if 'volume' in df.columns else [])
    display(dupe_groups.sort_values('count', ascending=False).head(10))"""))

    # --- Dedup preview ---
    cells.append(make_cell("markdown", "### Preview: kolik se slouci ve fazi 3"))
    cells.append(make_cell("code", """# Diacritics variant preview
df['_kw_nodiac'] = df['keyword_normalized'].apply(remove_diacritics)
diac_groups = df.groupby('_kw_nodiac')['keyword_normalized'].nunique()
diac_multi = diac_groups[diac_groups > 1]
print(f"Diacritics variants: {len(diac_multi)} skupin se slouci")
print(f"  Priklad variant ktere se mergnout:")
for key in diac_multi.nlargest(10).index:
    variants = df[df['_kw_nodiac'] == key]['keyword_normalized'].unique()
    vol_sum = df[df['_kw_nodiac'] == key]['volume'].sum() if 'volume' in df.columns else 0
    print(f"  {' | '.join(variants)}  (vol: {vol_sum})")

# Word-order variant preview
df['_word_sig'] = df['_kw_nodiac'].apply(lambda x: ' '.join(sorted(str(x).split())))
wo_groups = df.groupby('_word_sig')['keyword_normalized'].nunique()
wo_multi = wo_groups[wo_groups > 1]
# Exclude already-counted diacritics variants
wo_only = wo_multi.index.difference(diac_multi.index) if len(diac_multi) > 0 else wo_multi.index
print(f"\\nWord-order variants: {len(wo_multi)} skupin ({len(wo_only)} mimo diacritics)")
for key in list(wo_multi.nlargest(10).index)[:10]:
    variants = df[df['_word_sig'] == key]['keyword_normalized'].unique()
    if len(variants) > 1:
        print(f"  {' | '.join(variants[:5])}")

print(f"\\nODHAD pro fazi 3: ~{len(diac_multi) + len(wo_only)} keywords se slouci pri dedup")

df.drop(columns=['_kw_nodiac', '_word_sig'], inplace=True)"""))

    cells.append(make_cell("code", """# KD distribution
if 'kd' in df.columns:
    kd = pd.to_numeric(df['kd'], errors='coerce').dropna()
    if len(kd) > 0:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.hist(kd, bins=20, edgecolor='black', alpha=0.7, color='green')
        ax.set_title('Keyword Difficulty Distribution')
        ax.set_xlabel('KD')
        ax.axvline(kd.median(), color='red', linestyle='--', label=f'median={kd.median():.0f}')
        ax.legend()
        plt.tight_layout()
        plt.show()
        print(f"KD: min={kd.min():.0f}, max={kd.max():.0f}, median={kd.median():.0f}")
        print(f"Easy (KD<30): {(kd < 30).sum()}, Medium (30-60): {((kd >= 30) & (kd < 60)).sum()}, Hard (60+): {(kd >= 60).sum()}")
else:
    print("No KD column")"""))

    cells.append(make_cell("code", """# Outliers — head terms
if 'volume' in df.columns:
    cols = ['keyword', 'volume']
    if 'source' in df.columns:
        cols.append('source')
    if 'kd' in df.columns:
        cols.append('kd')
    print("Top 20 keywords by volume (head terms / potential outliers):")
    display(df.nlargest(20, 'volume')[cols])"""))

    # --- 2.3 N-gram analysis ---
    cells.append(make_cell("markdown", """## 2.3 N-gram analyza

Klicove pro identifikaci patterns pro faze 3 (blacklist), 4 (relevance) a 5 (kategorizace).
- **Uni-gramy**: jednotliva slova — odhaluji hlavni temata
- **Bi-gramy**: dvojice slov — odhaluji produkty a intent patterns
- **Tri-gramy**: trojice slov — odhaluji specifictejsi fraze"""))

    cells.append(make_cell("code", """# Uni-gramy
uni = get_ngrams(keywords, n=1, top=30)
print("=" * 60)
print("UNI-GRAMY (top 30 slov)")
print("=" * 60)
for word, count in uni:
    pct = count / len(df) * 100
    bar = '#' * int(pct)
    print(f"  {word:>25s}: {count:>5d} ({pct:>5.1f}%) {bar}")"""))

    cells.append(make_cell("code", """# Bi-gramy
bi = get_ngrams(keywords, n=2, top=20)
print("=" * 60)
print("BI-GRAMY (top 20 dvojic)")
print("=" * 60)
for gram, count in bi:
    pct = count / len(df) * 100
    bar = '#' * int(pct)
    print(f"  {gram:>35s}: {count:>5d} ({pct:>5.1f}%) {bar}")"""))

    cells.append(make_cell("code", """# Tri-gramy
tri = get_ngrams(keywords, n=3, top=15)
print("=" * 60)
print("TRI-GRAMY (top 15 trojic)")
print("=" * 60)
for gram, count in tri:
    pct = count / len(df) * 100
    print(f"  {gram:>45s}: {count:>5d} ({pct:>5.1f}%)")"""))

    cells.append(make_cell("code", """# N-gram bar charts
fig, axes = plt.subplots(1, 3, figsize=(18, 8))

for idx, (n, title, top_n) in enumerate([(1, 'Uni-gramy', 20), (2, 'Bi-gramy', 15), (3, 'Tri-gramy', 10)]):
    ngrams = get_ngrams(keywords, n=n, top=top_n)
    words = [g[0] for g in ngrams][::-1]
    counts = [g[1] for g in ngrams][::-1]
    colors = ['#2196F3', '#FF9800', '#4CAF50']
    axes[idx].barh(words, counts, color=colors[idx], alpha=0.8)
    axes[idx].set_title(title)
    axes[idx].set_xlabel('Count')

plt.tight_layout()
plt.show()"""))

    # --- Product coverage ---
    if products:
        products_str = repr(products)
        cells.append(make_cell("markdown", "### Pokryti produktu z params.yaml"))
        cells.append(make_cell("code", f"""expected_products = {products_str}
print("Pokryti produktu v datech:")
missing = []
for product in expected_products:
    p = str(product).lower()
    p_nd = remove_diacritics(p)
    count = df['keyword_normalized'].str.contains(p, na=False).sum()
    if count == 0:
        count = df['keyword_normalized'].apply(remove_diacritics).str.contains(p_nd, na=False).sum()
    status = 'OK' if count > 0 else 'MISSING'
    if count == 0:
        missing.append(product)
    print(f"  [{{status:>7s}}] {{product}}: {{count}} keywords")

if missing:
    print(f"\\nCHYBEJICI produkty (0 keywords): {{missing}}")
    print("  → Zvaz doplnit seed keywords pro tyto produkty (zpet do Faze 1)")"""))

    # --- Competitor coverage ---
    if competitors:
        comp_str = repr(competitors)
        cells.append(make_cell("markdown", "### Pokryti konkurentu z params.yaml"))
        cells.append(make_cell("code", f"""expected_competitors = {comp_str}
print("Pokryti konkurentu v datech:")
for comp in expected_competitors:
    c = str(comp).lower()
    count = df['keyword_normalized'].str.contains(c, na=False).sum()
    vol = df[df['keyword_normalized'].str.contains(c, na=False)]['volume'].sum() if 'volume' in df.columns and count > 0 else 0
    print(f"  {{comp:<25s}} {{count:>4d}} keywords (vol: {{vol:>6d}})")"""))

    # --- Intent pattern detection ---
    cells.append(make_cell("markdown", "### Intent patterns z n-gramu"))
    cells.append(make_cell("code", """# Auto-detect intent patterns
intent_signals = {
    'INFO': ['jak', 'co', 'proc', 'navod', 'pruvodce', 'rozdil', 'postup', 'typy', 'druhy'],
    'COMM': ['nejlepsi', 'porovnani', 'recenze', 'hodnoceni', 'test', 'vs', 'srovnani'],
    'TRANS': ['cena', 'koupit', 'objednat', 'eshop', 'sleva', 'akce', 'levne', 'kalkulacka'],
    'NAV': ['kontakt', 'login', 'pobocka', 'prihlaseni'],
}

uni = get_ngrams(keywords, n=1, top=100)
uni_dict = dict(uni)

print("Intent patterns nalezene v datech:")
for intent, signals in intent_signals.items():
    found = [(s, uni_dict[s]) for s in signals if s in uni_dict]
    if found:
        total = sum(c for _, c in found)
        print(f"  {intent}: {total:>4d}x total — {', '.join(f'{w}({c})' for w, c in found)}")
    else:
        print(f"  {intent}:    0x — zadne signaly nalezeny")"""))

    # --- Word length ---
    cells.append(make_cell("markdown", "### Delka keywords"))
    cells.append(make_cell("code", """df['_word_count'] = df['keyword_normalized'].str.split().str.len()
df['_char_count'] = df['keyword_normalized'].str.len()

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
axes[0].hist(df['_word_count'], bins=range(1, 12), edgecolor='black', alpha=0.7)
axes[0].set_title('Word count distribution')
axes[0].set_xlabel('Number of words')
axes[1].hist(df['_char_count'], bins=30, edgecolor='black', alpha=0.7, color='purple')
axes[1].set_title('Character count distribution')
axes[1].set_xlabel('Number of characters')
plt.tight_layout()
plt.show()

print(f"Median word count: {df['_word_count'].median():.0f}")
print(f"1-word keywords (head terms): {(df['_word_count'] == 1).sum()}")
print(f"4+ word keywords (long tail): {(df['_word_count'] >= 4).sum()} ({(df['_word_count'] >= 4).sum()/len(df)*100:.1f}%)")

# Short keywords
cols = ['keyword', 'volume'] if 'volume' in df.columns else ['keyword']
short = df[df['_word_count'] == 1].sort_values('volume', ascending=False).head(15) if 'volume' in df.columns else df[df['_word_count'] == 1].head(15)
print("\\nSingle-word keywords (head terms / noise):")
display(short[cols])

df.drop(columns=['_word_count', '_char_count'], inplace=True)"""))

    # --- 2.4 Recommendations ---
    cells.append(make_cell("markdown", """## 2.4 Doporuceni pro dalsi faze

Automaticky generovane navrhy na zaklade n-gram analyzy.
**Projdi s AI v Claude Code — AI vysvetli a navrhne akce.**"""))

    cells.append(make_cell("code", """uni = get_ngrams(keywords, n=1, top=100)
bi = get_ngrams(keywords, n=2, top=50)

# --- Faze 3: Blacklist ---
print("=" * 60)
print("NAVRHY PRO FAZI 3 (Cleaning) — blacklist kandidati")
print("=" * 60)
irrelevant_signals = ['kurz', 'prace', 'bazar', 'wiki', 'skoleni', 'referat', 'slozeni',
                      'volne', 'brigada', 'referaty', 'seminarka', 'maturita']
blacklist_candidates = []
for word, count in uni:
    if word in irrelevant_signals or any(s in word for s in irrelevant_signals):
        blacklist_candidates.append((word, count))
        print(f"  '{word}' ({count}x)")
if not blacklist_candidates:
    print("  (zadne ocividne blacklist kandidaty)")

# --- Faze 4: Excluded ---
print()
print("=" * 60)
print("NAVRHY PRO FAZI 4 (Relevance) — excluded patterns")
print("=" * 60)
excluded_signals = ['kurz', 'prace', 'bazar', 'wiki', 'skola', 'referat', 'seminarka',
                    'volne mist', 'nabidka prace', 'brigad']
for gram, count in bi:
    if any(s in gram for s in excluded_signals):
        print(f"  EXCLUDED bi-gram: '{gram}' ({count}x)")

# --- Faze 5: Product + intent patterns ---
print()
print("=" * 60)
print("NAVRHY PRO FAZI 5 (Kategorizace) — produkt patterns z bi-gramu")
print("=" * 60)
print("Top bi-gramy (count >= 5) — kandidati na produkt patterns:")
for gram, count in bi:
    if count >= 5:
        print(f"  '{gram}' ({count}x)")

# --- Summary ---
print()
print("=" * 60)
print("SHRNUTI")
print("=" * 60)
print(f"Total keywords:       {len(df)}")
if 'volume' in df.columns:
    print(f"Total volume:         {df['volume'].sum():,}")
    print(f"Median volume:        {df['volume'].median():.0f}")
print(f"Blacklist kandidatu:  {len(blacklist_candidates)}")
print(f"Diacritics to merge:  ~{len(df.groupby(df['keyword_normalized'].apply(remove_diacritics))['keyword_normalized'].nunique().pipe(lambda x: x[x > 1]))}")
print()
print("DALSI KROK: Projdi tyto vysledky s AI v Claude Code.")
print("AI navrhne konkretni zmeny do params.yaml.")"""))

    # --- Shrnuti markdown ---
    cells.append(make_cell("markdown", """## Shrnuti

**Projdi vysledky s AI:**
1. Vrat se do Claude Code
2. Rekni "projdeme EDA vysledky"
3. AI te provede sekci po sekci a navrhne akce

**Typicke akce po EDA:**
- [ ] Pridat blacklist slova do params.yaml
- [ ] Pridat excluded patterns do params.yaml
- [ ] Doplnit chybejici produkty (zpet do Faze 1)
- [ ] Potvrdit volume strategii (sum vs keep_highest)
- [ ] Doplnit produkt/intent patterns do params.yaml"""))

    # Build notebook
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.11.0"},
        },
        "cells": cells,
    }
    return notebook


def run_as_script(input_csv: str, params: dict) -> None:
    """Run EDA analysis as plain Python (no Jupyter needed)."""
    import pandas as pd
    from collections import Counter

    log.info("Running EDA as script (no Jupyter)...")
    df = pd.read_csv(input_csv, encoding="utf-8-sig")
    log.info("Loaded %d keywords from %s", len(df), input_csv)

    # Basic stats
    log.info("=" * 50)
    log.info("BASIC OVERVIEW")
    log.info("=" * 50)
    log.info("Total: %d, Unique: %d", len(df), df["keyword_normalized"].nunique())
    if "volume" in df.columns:
        vol = df["volume"]
        log.info("Volume: min=%d, max=%d, median=%.0f, mean=%.0f", vol.min(), vol.max(), vol.median(), vol.mean())
        log.info("Zero volume: %d (%.1f%%)", (vol <= 0).sum(), (vol <= 0).sum() / len(df) * 100)

    # N-grams
    def _remove_diac(t: str) -> str:
        return t.translate(str.maketrans(
            "\u00e1\u00e4\u010d\u010f\u00e9\u011b\u00ed\u013a\u013e\u0148\u00f3\u00f4\u0155\u0159\u0161\u0165\u00fa\u016f\u00fd\u017e",
            "aacdeeillnoorrstuuyz",
        ))

    stops = {"a", "i", "k", "o", "s", "v", "z", "na", "do", "se", "je", "to", "za", "co", "si", "pro", "jak", "ale"}
    keywords = df["keyword_normalized"].tolist()

    def _ngrams(n: int, top: int) -> list[tuple[str, int]]:
        ng: list[str] = []
        for t in keywords:
            words = [w for w in str(t).lower().split() if w not in stops and len(w) > 1]
            for i in range(len(words) - n + 1):
                ng.append(" ".join(words[i:i + n]))
        return Counter(ng).most_common(top)

    for n, label, top in [(1, "UNI-GRAMY", 20), (2, "BI-GRAMY", 15), (3, "TRI-GRAMY", 10)]:
        log.info("")
        log.info("%s (top %d):", label, top)
        for gram, count in _ngrams(n, top):
            log.info("  %-30s %d", gram, count)

    # Dedup preview
    df["_nd"] = df["keyword_normalized"].apply(_remove_diac)
    diac = df.groupby("_nd")["keyword_normalized"].nunique()
    diac_multi = (diac > 1).sum()
    log.info("")
    log.info("Dedup preview: ~%d diacritics variant groups to merge", diac_multi)

    log.info("")
    log.info("DONE. For full analysis with charts, use Jupyter notebook.")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate EDA notebook")
    parser.add_argument("--input", type=str, default="data/interim/keywords_raw.csv")
    parser.add_argument("--output", type=Path, default=Path("notebooks/01_eda.ipynb"))
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--run-as-script", action="store_true", help="Run EDA as Python script (no Jupyter)")
    args = parser.parse_args()

    params = load_params(args.project_root)

    if args.run_as_script:
        run_as_script(args.input, params)
        return

    notebook = generate_notebook(args.input, params)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(notebook, f, ensure_ascii=False, indent=1)

    log.info("EDA notebook saved to %s", args.output)
    log.info("")
    log.info("Next steps:")
    log.info("  1. Open: jupyter notebook %s", args.output)
    log.info("  2. Select kernel for this project")
    log.info("  3. Run All cells")
    log.info("  4. Return to Claude Code and say 'projdeme EDA vysledky'")


if __name__ == "__main__":
    main()
