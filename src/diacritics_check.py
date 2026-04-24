"""
Faze 3.6: Diacritics check (post-cleaning)

Po Fazi 3 cleaningu zkontroluje, zda vystupni keywords neobsahuji slova,
ktera by mela mit diakritiku, ale nemaji. Kombinuje:

1) Heuristika — rychla, offline, detekuje typicke CZ patterny
2) AI check — volitelna, presnejsi, pouzije OpenAI/Anthropic/Gemini batch

Duvod: cleaning.py slouci varianty s/bez diakritiky **pokud obe existuji
v datech**. Pokud ale input obsahuje jen "kuchynsky robot" a "kuchyňský
robot" chybi uplne, cleaning nema co slucovat a vystup zustane bez
diakritiky. Tento script to detekuje a navrhne opravy.

Vstup:  data/interim/keywords_clean.csv
Vystup: data/interim/keywords_diacritics_review.xlsx (jen suspects)
        stdout summary

Pouziti:
    python src/diacritics_check.py --project-root .                    # jen heuristika
    python src/diacritics_check.py --project-root . --mode ai          # AI batch
    python src/diacritics_check.py --project-root . --mode both        # oboji
    python src/diacritics_check.py --project-root . --sample 50        # jen sample
"""
from __future__ import annotations

import argparse
import json
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


CZECH_DIACRITICS = set("áäčďéěíĺľňóôŕřšťúůýž")


HEURISTIC_PATTERNS = [
    (r"\bkuchynsk", "kuchyňsk"),
    (r"\bstrojek", "strojek"),
    (r"\bsvarec", "svářeč"),
    (r"\bsvarov", "svářov"),
    (r"\bvyroba\b", "výroba"),
    (r"\bnejlepsi\b", "nejlepší"),
    (r"\brecenz", "recenz"),
    (r"\bsleva\b", "sleva"),
    (r"\bprislusenstv", "příslušenstv"),
    (r"\bcasti\b", "části"),
    (r"\bnahradni\b", "náhradní"),
    (r"\bruzne\b", "různé"),
    (r"\bprakticky\b", "praktický"),
    (r"\bdomaci\b", "domácí"),
    (r"\bvystava\b", "výstava"),
    (r"\bprodejce\b", "prodejce"),
    (r"\bcesky\b", "český"),
    (r"\bceska\b", "česká"),
    (r"\bceske\b", "české"),
    (r"\bzaruka\b", "záruka"),
    (r"\bpocitac", "počítač"),
    (r"\bucinn", "účinn"),
    (r"\bcisteni\b", "čištění"),
    (r"\bmycka\b", "myčka"),
    (r"\blednic", "lednič"),
]


COMMON_CZECH_ROOTS_NEED_DIACRITICS = {
    "čk", "šk", "čt", "št", "čn", "šn", "čt", "řad", "řed", "žad",
    "páč", "mužs", "žens", "měs", "tří", "čtyř", "příč", "více",
}


def has_diacritics(text: str) -> bool:
    return any(c in CZECH_DIACRITICS for c in text.lower())


def heuristic_flag(keyword: str) -> tuple[bool, str | None]:
    """Detekuje pravdepodobne chybejici diakritiku. Vrati (flagged, suggested_fix|None)."""
    if has_diacritics(keyword):
        return False, None

    kw = keyword.lower()
    for pat, replacement in HEURISTIC_PATTERNS:
        m = re.search(pat, kw)
        if m:
            suggested = re.sub(pat, replacement, kw, count=1)
            return True, suggested

    return False, None


def run_heuristic(df: pd.DataFrame, kw_col: str) -> pd.DataFrame:
    """Projde dataset a flagne suspects."""
    flagged = []
    for _, row in df.iterrows():
        kw = str(row[kw_col])
        is_flagged, suggested = heuristic_flag(kw)
        if is_flagged:
            flagged.append({
                kw_col: kw,
                "suggested_fix": suggested,
                "method": "heuristic",
                "volume": row.get("volume", None),
            })
    return pd.DataFrame(flagged)


def build_ai_prompt(keywords: list[str]) -> str:
    kw_list = "\n".join(f"{i + 1}. {kw}" for i, kw in enumerate(keywords))
    return f"""Jsi jazykovy korektor pro cestinu. Dostanes seznam klicovych slov
a tvym ukolem je ziskat, ktera by mela mit diakritiku ale nemaji (resp. maji
ASCII-fikovanou formu).

Pro kazde slovo rozhodni:
- potrebuje_diakritiku: true/false (true = chybi diakritika, mela by tam byt)
- spravna_forma: navrhovana spravna forma s diakritikou (jen pokud true)

Pozor na slova ktera v cestine diakritiku NEMAJI (napr. "robot", "cena",
"levny" bez -y̌, "domov"). Ta oznac false.

Keywords:
{kw_list}

Odpoved STRIKTNE v JSON formatu:
{{
  "results": [
    {{"index": 1, "kw": "...", "needs_fix": true/false, "suggested": "..."}},
    ...
  ]
}}"""


def run_ai_check(df: pd.DataFrame, kw_col: str, model: str,
                 batch_size: int = 30) -> pd.DataFrame:
    """AI batch check. Vraci dataframe jen s flagged rows."""
    sys.path.insert(0, str(Path(__file__).parent))
    from ai_client import get_ai_client, call_ai  # type: ignore

    client, provider = get_ai_client(model)

    candidates = df[~df[kw_col].apply(has_diacritics)].copy()
    log.info("AI check: %d kandidatu bez diakritiky", len(candidates))

    if candidates.empty:
        return pd.DataFrame()

    flagged_rows = []
    total_batches = (len(candidates) + batch_size - 1) // batch_size

    for batch_idx in range(0, len(candidates), batch_size):
        batch = candidates.iloc[batch_idx:batch_idx + batch_size]
        keywords = batch[kw_col].tolist()
        prompt = build_ai_prompt(keywords)

        log.info("Batch %d/%d (%d KW)", batch_idx // batch_size + 1,
                 total_batches, len(batch))

        try:
            response = call_ai(prompt, client, provider, model)
            data = json.loads(_extract_json(response))
            results = data.get("results", [])
        except Exception as e:
            log.error("AI batch selhal: %s — preskakuji", e)
            continue

        for item in results:
            if item.get("needs_fix"):
                idx = item.get("index", 0) - 1
                if 0 <= idx < len(batch):
                    row = batch.iloc[idx]
                    flagged_rows.append({
                        kw_col: row[kw_col],
                        "suggested_fix": item.get("suggested", ""),
                        "method": "ai",
                        "volume": row.get("volume", None),
                    })

    return pd.DataFrame(flagged_rows)


def _extract_json(text: str) -> str:
    """AI nekdy obali JSON markdown — orizni."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return m.group(0) if m else text


def main() -> int:
    parser = argparse.ArgumentParser(description="Faze 3.6: Post-cleaning diacritics check")
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--input", type=Path, default=None,
                        help="Default: data/interim/keywords_clean.csv")
    parser.add_argument("--output", type=Path, default=None,
                        help="Default: data/interim/keywords_diacritics_review.xlsx")
    parser.add_argument("--mode", choices=["heuristic", "ai", "both"],
                        default="heuristic",
                        help="heuristic (fast, offline) / ai / both")
    parser.add_argument("--model", type=str, default="gpt-4o-mini",
                        help="AI model (jen pro mode=ai|both)")
    parser.add_argument("--sample", type=int, default=0,
                        help="Otestuj jen N nahodnych KW (0 = vse)")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    input_path = args.input or (project_root / "data" / "interim" / "keywords_clean.csv")
    output_path = args.output or (project_root / "data" / "interim"
                                  / "keywords_diacritics_review.xlsx")

    if not input_path.exists():
        log.error("Vstup neexistuje: %s", input_path)
        return 1

    log.info("Input: %s", input_path)
    df = pd.read_csv(input_path, encoding="utf-8-sig", low_memory=False)
    log.info("Nacteno %d radku", len(df))

    kw_col = "keyword_normalized" if "keyword_normalized" in df.columns else "keyword"

    if args.sample > 0:
        df = df.sample(min(args.sample, len(df)), random_state=42).reset_index(drop=True)
        log.info("Sample: %d radku", len(df))

    all_flagged = []

    if args.mode in ("heuristic", "both"):
        log.info("Heuristicky check...")
        h = run_heuristic(df, kw_col)
        log.info("  Flagnuto: %d", len(h))
        all_flagged.append(h)

    if args.mode in ("ai", "both"):
        log.info("AI check (model=%s)...", args.model)
        a = run_ai_check(df, kw_col, args.model)
        log.info("  Flagnuto: %d", len(a))
        all_flagged.append(a)

    if not all_flagged or all(f.empty for f in all_flagged):
        log.info("Zadne suspicous KW. Cleaning output je v poradku.")
        return 0

    combined = pd.concat([f for f in all_flagged if not f.empty], ignore_index=True)
    combined = combined.drop_duplicates(subset=[kw_col])
    combined = combined.sort_values("volume", ascending=False, na_position="last")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_excel(output_path, index=False)

    log.info("=" * 50)
    log.info("DIACRITICS CHECK HOTOVO")
    log.info("  Flagnutych KW: %d (z %d celkem — %.1f%%)",
             len(combined), len(df), len(combined) / len(df) * 100)
    log.info("  Vystup: %s", output_path)
    log.info("")
    log.info("TOP 10 suspects (nejvyssi volume):")
    for _, r in combined.head(10).iterrows():
        vol = r.get("volume", "?")
        print(f"  {r[kw_col]:<40} → {r['suggested_fix']:<40} [{r['method']}, vol={vol}]")

    log.info("")
    log.info("Dalsi krok: review XLSX a apply opravy (bud manualne, nebo")
    log.info("            pridej do cleaning.py params.yaml ekvivalenci).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
