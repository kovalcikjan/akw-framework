"""Faze 5: Categorization (typ, produkt, brand, intent, funnel).

Uses shared ai_client.py for multi-model support (OpenAI/Anthropic/Gemini).
Test mode includes AI + reasoning. Iterative testing. Few-shot from rule-based.
Checkpoint/resume. Post-processing.

Outputs:
  - data/interim/keywords_categorized.csv
  - data/interim/money_keywords.csv
  - data/interim/categorization_issues.csv
  - data/interim/categorization_test_N.csv (test rounds)
  - checkpoint_categorization.json

Usage:
    python src/categorization.py --test 20                          # test
    python src/categorization.py --test 20 --model gemini-2.0-flash # test + model
    python src/categorization.py --test 20 --test-round 2           # next round
    python src/categorization.py --dry-run                          # show prompt
    python src/categorization.py                                    # full run
    python src/categorization.py --auto                             # skip review
"""

import argparse
import json
import logging
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd
import yaml
from tqdm import tqdm

from ai_client import call_ai_json, get_ai_client, load_env

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DIACRITICS_MAP = str.maketrans(
    "\u00e1\u00e4\u010d\u010f\u00e9\u011b\u00ed\u013a\u013e\u0148"
    "\u00f3\u00f4\u0155\u0159\u0161\u0165\u00fa\u016f\u00fd\u017e",
    "aacdeeillnoorrstuuyz",
)

INTENT_PATTERNS: dict[str, list[str]] = {
    "INFO": [
        r"\bjak\b", r"\bco je\b", r"\bco jsou\b", r"\bproc\b", r"\bnavod\b",
        r"\bpruvodce\b", r"\bpostup\b", r"\bvyznam\b", r"\bdefinice\b",
        r"\btypy\b", r"\bdruhy\b", r"\brozdi[l]\b",
    ],
    "COMM": [
        r"\bnejleps[i]\b", r"\bporovnan[i]\b", r"\brecenz[ei]\b",
        r"\bhodnocen[i]\b", r"\btest\b", r"\bvs\b", r"\bversus\b",
        r"\btop \d+\b", r"\bsrovnan[i]\b", r"\bzkusenost\b",
    ],
    "TRANS": [
        r"\bcena\b", r"\bceni[k]\b", r"\bcenik\b", r"\bkoupit\b", r"\bobjednat\b",
        r"\beshop\b", r"\be-shop\b", r"\bsleva\b", r"\bakce\b", r"\blevn[eéě]\b",
        r"\bprodej\b", r"\bkalkulac\b", r"\bna prodej\b", r"\bna miru\b",
        r"\bpoptavk\b", r"\bnejlevn\b", r"\bkolik stoj\b", r"\bprodam\b",
    ],
    "NAV": [
        r"\blogin\b", r"\bkontakt\b", r"\bpobock\b", r"\bprihlaseni\b",
        r"\bregistrac\b",
    ],
}

FUNNEL_MAP = {"INFO": "TOFU", "COMM": "MOFU", "TRANS": "BOFU", "NAV": "BRAND"}


def remove_diacritics(text: str) -> str:
    return text.translate(DIACRITICS_MAP)


def load_params(project_root: Path) -> dict:
    path = project_root / "params.yaml"
    if not path.exists():
        log.error("params.yaml not found at %s", path)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_ngrams(texts: list[str], n: int = 2, top: int = 20) -> list[tuple[str, int]]:
    stops = {"a", "i", "k", "o", "s", "v", "z", "na", "do", "se", "je", "to", "za", "co", "si", "pro", "jak", "ale"}
    ng: list[str] = []
    for t in texts:
        words = [w for w in str(t).lower().split() if w not in stops and len(w) > 1]
        for i in range(len(words) - n + 1):
            ng.append(" ".join(words[i:i + n]))
    return Counter(ng).most_common(top)


# --- Checkpoint ---


def load_checkpoint(project_root: Path) -> dict:
    path = project_root / "checkpoint_categorization.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"processed_batches": [], "results": {}}


def save_checkpoint(project_root: Path, checkpoint: dict) -> None:
    path = project_root / "checkpoint_categorization.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)


def cleanup_checkpoint(project_root: Path) -> None:
    path = project_root / "checkpoint_categorization.json"
    if path.exists():
        path.unlink()


# --- Rule-based ---


def build_product_patterns(params: dict) -> dict[str, list[re.Pattern]]:
    cat = params.get("categorization", {}).get("produkt", {})
    patterns: dict[str, list[re.Pattern]] = {}
    for category, kws in cat.items():
        patterns[category] = []
        items = kws if isinstance(kws, list) else [kws] if isinstance(kws, str) else []
        for kw in items:
            if isinstance(kw, str) and kw.strip():
                p = re.escape(kw.lower().strip())
                p_nd = re.escape(remove_diacritics(kw.lower().strip()))
                patterns[category].append(re.compile(rf"{p}"))
                if p != p_nd:
                    patterns[category].append(re.compile(rf"{p_nd}"))
    return patterns


def build_brand_patterns(params: dict) -> dict[str, list[re.Pattern]]:
    brand_cfg = params.get("categorization", {}).get("brand", {})
    patterns: dict[str, list[re.Pattern]] = {"own": [], "competitor": [], "retail": []}
    for btype in ["own", "competitor", "competitor_indirect", "retail"]:
        target = "competitor" if btype == "competitor_indirect" else btype
        if target not in patterns:
            patterns[target] = []
        for b in brand_cfg.get(btype, []):
            if isinstance(b, str) and b.strip():
                patterns[target].append(re.compile(re.escape(b.lower().strip())))
    return patterns


def classify_intent(keyword: str) -> tuple[str, str]:
    kw = keyword.lower()
    kw_nd = remove_diacritics(kw)
    for intent, pats in INTENT_PATTERNS.items():
        for pat in pats:
            if re.search(pat, kw) or re.search(pat, kw_nd):
                return intent, FUNNEL_MAP[intent]
    return "INFO", "TOFU"


def rule_based_categorize(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Rule-based categorization."""
    prod_patterns = build_product_patterns(params)
    brand_patterns = build_brand_patterns(params)

    for col in ["typ", "produkt", "brand", "brand_type", "specifikace",
                 "intent", "funnel", "categorization_source", "categorization_confidence"]:
        df[col] = ""

    kw_col = "keyword_normalized"

    for idx in tqdm(df.index, desc="Rule-based", disable=len(df) < 50):
        kw = df.loc[idx, kw_col]
        kw_nd = remove_diacritics(kw)

        # Product
        for category, pats in prod_patterns.items():
            if any(p.search(kw) or p.search(kw_nd) for p in pats):
                df.loc[idx, "produkt"] = category
                df.loc[idx, "categorization_source"] = "rule"
                break

        # Brand (own, competitor, retail)
        for btype, pats in brand_patterns.items():
            for p in pats:
                if p.search(kw) or p.search(kw_nd):
                    df.loc[idx, "brand"] = p.pattern.replace("\\", "")
                    df.loc[idx, "brand_type"] = btype
                    break
            if df.loc[idx, "brand"] != "":
                break

        # Typ
        typ_patterns = [
            ("dotaz", r"\bjak\b|\bco je\b|\bproc\b|\bnavod\b"),
            ("porovnani", r"\bnejleps\b|\bporovnan\b|\bvs\b|\bsrovnan\b"),
            ("recenze", r"\brecenz\b|\bhodnocen\b|\bzkusenost\b"),
            ("kalkulace", r"\bkalkulac\b|\bvypocet\b|\bceni[k]\b|\bcenik\b|\bkolik stoj\b"),
            ("legislativa", r"\bstavebni povolen\b|\bdokumentac\b|\bohlaseni\b|\buzemni rozhodnut\b|\bkolaudac\b"),
            ("sluzba", r"\bna klic\b|\bna klíč\b|\bmontaz hal\b|\bvystavba\b|\bstavba hal\b"),
            ("komponenta", r"\bprofil\b|\bvaznik\b|\bvaznice\b|\bplech[uy]?\b|\bpanel[uy]?\b|\boplasteni\b|\bkonstrukce\b|\bsloup\b|\bpatka\b"),
        ]
        for typ_name, pattern in typ_patterns:
            if re.search(pattern, kw) or re.search(pattern, kw_nd):
                df.loc[idx, "typ"] = typ_name
                break
        if df.loc[idx, "typ"] == "" and df.loc[idx, "produkt"] != "":
            df.loc[idx, "typ"] = "produkt"

        # Specifikace detection
        spec_patterns = [
            ("na klíč", r"\bna klic\b|\bna klíč\b"),
            ("izolovaná", r"\bzateplen\b|\bizolovan\b"),
            ("neizolovaná", r"\bneizolovan\b|\bnezateplen\b"),
            ("svépomocí", r"\bsvepomoc\b|\bsvépomoc\b"),
        ]
        for spec_name, pattern in spec_patterns:
            if re.search(pattern, kw) or re.search(pattern, kw_nd):
                df.loc[idx, "specifikace"] = spec_name
                break

        # Intent + funnel
        intent, funnel = classify_intent(kw)
        df.loc[idx, "intent"] = intent
        df.loc[idx, "funnel"] = funnel

        # Kalkulace/cenik → TRANS override (intent=INFO + typ=kalkulace is contradiction)
        if df.loc[idx, "typ"] in ("kalkulace",) and df.loc[idx, "intent"] == "INFO":
            df.loc[idx, "intent"] = "TRANS"
            df.loc[idx, "funnel"] = "BOFU"

        # Confidence
        if df.loc[idx, "produkt"] != "" or df.loc[idx, "typ"] != "":
            df.loc[idx, "categorization_confidence"] = "high"
        else:
            df.loc[idx, "categorization_confidence"] = "low"

    rule_n = (df["categorization_source"] == "rule").sum()
    low_n = (df["categorization_confidence"] == "low").sum()
    log.info("Rule-based: %d categorized (%.0f%%), %d low-confidence", rule_n, rule_n / len(df) * 100, low_n)
    return df


# --- Few-shot ---


def extract_few_shot(df: pd.DataFrame, count: int = 20) -> list[dict]:
    """Extract diverse few-shot examples from rule-based high-confidence results."""
    high = df[df["categorization_confidence"] == "high"].copy()
    if len(high) == 0:
        return []

    examples: list[dict] = []
    for intent in ["INFO", "COMM", "TRANS", "NAV"]:
        subset = high[high["intent"] == intent]
        n = min(count // 4 + 1, len(subset))
        if n > 0:
            sampled = subset.sample(n, random_state=42)
            for _, row in sampled.iterrows():
                examples.append({
                    "keyword": row["keyword_normalized"],
                    "typ": row["typ"],
                    "produkt": row["produkt"],
                    "brand": row["brand"],
                    "intent": row["intent"],
                })

    random.seed(42)
    if len(examples) > count:
        examples = random.sample(examples, count)
    log.info("Extracted %d few-shot examples", len(examples))
    return examples


# --- Prompt ---


def build_categorization_prompt(
    keywords: list[str], params: dict,
    few_shot: list[dict], ngram_context: str = "",
) -> str:
    cat = params.get("categorization", {})
    produkt_map = cat.get("produkt", {})
    brand_cfg = cat.get("brand", {})
    typ_list = cat.get("typ", [])
    spec_list = cat.get("specifikace", [])

    fs_block = ""
    if few_shot:
        fs_lines = [
            f'  {{"keyword": "{ex["keyword"]}", "typ": "{ex["typ"]}", "produkt": "{ex["produkt"]}", "brand": "{ex["brand"]}", "intent": "{ex["intent"]}"}}'
            for ex in few_shot
        ]
        fs_block = f"\n## Priklady spravne kategorizace\n[\n{chr(10).join(fs_lines)}\n]\n"

    return f"""Jsi SEO analytik. Kategorizuj kazde keyword podle schema nize.

## Kategorization schema

### Typ
Mozne hodnoty: {', '.join(str(t) for t in typ_list) if typ_list else 'produkt, dotaz, porovnani, recenze, kalkulacka, brand'}

### Produkt
{json.dumps(produkt_map, ensure_ascii=False, indent=2) if produkt_map else 'N/A'}

### Brand
Vlastni: {', '.join(str(b) for b in brand_cfg.get('own', []))}
Konkurencni: {', '.join(str(b) for b in brand_cfg.get('competitor', []))}

### Specifikace
{', '.join(str(s) for s in spec_list) if spec_list else 'N/A'}

### Intent
INFO = informacni (jak, co je, proc, navod)
COMM = komercni srovnavaci (nejlepsi, porovnani, recenze, vs)
TRANS = transakcni (cena, cenik, koupit, objednat, na prodej, na miru)
NAV = navigacni (login, kontakt, pobocka)
{fs_block}
{f"## N-gram kontext{chr(10)}{ngram_context}" if ngram_context else ""}

## Keywords k kategorizaci
{chr(10).join(f'- {kw}' for kw in keywords)}

## Odpovez PRESNE v JSON formatu (list):
[
  {{
    "keyword": "...",
    "typ": "...",
    "produkt": "... nebo null",
    "brand": "... nebo null",
    "brand_type": "own/competitor/null",
    "specifikace": "... nebo null",
    "intent": "INFO/COMM/TRANS/NAV",
    "reason": "max 10 slov"
  }}
]

Odpovez JEN JSON."""


# --- AI classify ---


def ai_classify_batch(
    keywords: list[str], params: dict, few_shot: list[dict],
    ngram_ctx: str, client: object, provider: str, model: str,
) -> list[dict]:
    prompt = build_categorization_prompt(keywords, params, few_shot, ngram_ctx)
    results = call_ai_json(prompt, client, provider, model)
    if not results:
        return [{"keyword": kw, "intent": "INFO", "reason": "AI error"} for kw in keywords]
    return results


def ai_classify_all(
    df: pd.DataFrame, params: dict, few_shot: list[dict],
    model: str, batch_size: int, project_root: Path,
) -> pd.DataFrame:
    low_mask = df["categorization_confidence"] == "low"
    low_kws = df.loc[low_mask, "keyword_normalized"].tolist()
    if not low_kws:
        log.info("No low-confidence keywords")
        return df

    all_kws = df["keyword_normalized"].tolist()
    bigrams = get_ngrams(all_kws, n=2, top=20)
    ngram_ctx = "Top bi-gramy: " + ", ".join(f"'{g}' ({c}x)" for g, c in bigrams)

    checkpoint = load_checkpoint(project_root)
    processed = set(checkpoint.get("processed_batches", []))
    cached = checkpoint.get("results", {})

    log.info("AI categorization: %d keywords, batch=%d, model=%s, few-shot=%d",
             len(low_kws), batch_size, model, len(few_shot))

    client, provider = get_ai_client(model)
    total = (len(low_kws) + batch_size - 1) // batch_size

    for i in tqdm(range(0, len(low_kws), batch_size), desc="AI categorization", total=total):
        bid = str(i)
        if bid in processed:
            continue

        batch = low_kws[i:i + batch_size]
        results = ai_classify_batch(batch, params, few_shot, ngram_ctx, client, provider, model)

        for r in results:
            cached[r.get("keyword", "").lower().strip()] = r

        processed.add(bid)
        checkpoint["processed_batches"] = list(processed)
        checkpoint["results"] = cached
        save_checkpoint(project_root, checkpoint)

        if i + batch_size < len(low_kws):
            time.sleep(0.5)

    # Map back
    for idx in df.index[low_mask]:
        kw = df.loc[idx, "keyword_normalized"]
        if kw in cached:
            r = cached[kw]
            for col in ["typ", "produkt", "brand", "brand_type", "specifikace", "intent"]:
                val = r.get(col)
                if val and val != "null" and str(val).strip():
                    df.loc[idx, col] = str(val)
            df.loc[idx, "categorization_source"] = "ai"
            df.loc[idx, "categorization_confidence"] = "medium"
            if r.get("reason"):
                df.loc[idx, "categorization_reason"] = r["reason"]
            intent = df.loc[idx, "intent"]
            if intent in FUNNEL_MAP:
                df.loc[idx, "funnel"] = FUNNEL_MAP[intent]

    return df


# --- Money keywords ---


def flag_money_keywords(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    threshold = params.get("scoring", {}).get("money_threshold", 20)
    df["priority"] = ""
    money = df["intent"].isin(["TRANS", "COMM"]) & (df["brand_type"] != "competitor")
    if "volume" in df.columns:
        money = money & ((df["volume"] >= threshold) | (df["produkt"] != ""))
    else:
        money = money & (df["produkt"] != "")
    df.loc[money, "priority"] = "money_keyword"
    log.info("Money keywords: %d (%.1f%%), threshold=%d", money.sum(), money.sum() / len(df) * 100, threshold)
    return df


# --- Post-processing ---


def post_process(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    brand_cfg = params.get("categorization", {}).get("brand", {})
    own_brands = [b.lower() for b in brand_cfg.get("own", []) if isinstance(b, str)]
    fixes = 0
    for idx in df.index:
        kw = df.loc[idx, "keyword_normalized"]
        brand = df.loc[idx, "brand"]
        if brand and isinstance(brand, str) and brand.lower() in own_brands:
            if brand.lower() not in kw and remove_diacritics(brand.lower()) not in remove_diacritics(kw):
                df.loc[idx, "brand"] = ""
                df.loc[idx, "brand_type"] = ""
                fixes += 1
    if fixes > 0:
        log.info("Post-processing: removed brand from %d generic queries", fixes)
    return df


# --- Validation ---


def validate(df: pd.DataFrame) -> pd.DataFrame:
    df["categorization_issue"] = ""
    mask1 = (df["intent"] == "TRANS") & (df["typ"] == "dotaz")
    df.loc[mask1, "categorization_issue"] = "TRANS intent but typ=dotaz"
    mask2 = df["typ"].str.contains("brand", case=False, na=False) & (df["brand"] == "")
    df.loc[mask2, "categorization_issue"] = "typ=brand but no brand detected"
    issues = df[df["categorization_issue"] != ""]
    log.info("Consistency issues: %d", len(issues))
    return df


# --- Test mode ---


def run_test(
    df: pd.DataFrame, params: dict, model: str, batch_size: int,
    output_dir: Path, test_round: int,
) -> None:
    """Test: rule-based + AI on sample with reasoning for comparison."""
    log.info("TEST ROUND %d: %d keywords, model=%s", test_round, len(df), model)

    # Rule-based
    df = rule_based_categorize(df, params)
    few_shot = extract_few_shot(df, 15)

    # AI for ALL test keywords
    log.info("AI classification (test — all keywords get AI reasoning)")
    client, provider = get_ai_client(model)
    all_kws = df["keyword_normalized"].tolist()
    bigrams = get_ngrams(all_kws, n=2, top=20)
    ngram_ctx = "Top bi-gramy: " + ", ".join(f"'{g}' ({c}x)" for g, c in bigrams)

    all_results: list[dict] = []
    for i in tqdm(range(0, len(all_kws), batch_size), desc=f"Test AI ({model})"):
        batch = all_kws[i:i + batch_size]
        results = ai_classify_batch(batch, params, few_shot, ngram_ctx, client, provider, model)
        all_results.extend(results)
        if i + batch_size < len(all_kws):
            time.sleep(0.5)

    # Add AI columns
    result_map = {r.get("keyword", "").lower().strip(): r for r in all_results}
    for col in ["ai_typ", "ai_produkt", "ai_brand", "ai_intent", "ai_reason"]:
        df[col] = ""
    df["ai_model"] = model

    for idx in df.index:
        kw = df.loc[idx, "keyword_normalized"]
        if kw in result_map:
            r = result_map[kw]
            df.loc[idx, "ai_typ"] = r.get("typ", "")
            df.loc[idx, "ai_produkt"] = r.get("produkt", "") or ""
            df.loc[idx, "ai_brand"] = r.get("brand", "") or ""
            df.loc[idx, "ai_intent"] = r.get("intent", "")
            df.loc[idx, "ai_reason"] = r.get("reason", "")

    # Agreement
    df["rule_ai_match"] = (df["intent"] == df["ai_intent"]) & (df["produkt"] == df["ai_produkt"])
    agree = df["rule_ai_match"].sum()
    disagree = len(df) - agree

    # Save
    test_path = output_dir / f"categorization_test_{test_round}.csv"
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(test_path, index=False, encoding="utf-8-sig")
    log.info("Saved: %s", test_path)

    # Summary
    log.info("=" * 50)
    log.info("TEST ROUND %d (model: %s)", test_round, model)
    log.info("=" * 50)
    log.info("Rule-based coverage: %d/%d (%.0f%%)",
             (df["categorization_confidence"] == "high").sum(), len(df),
             (df["categorization_confidence"] == "high").sum() / len(df) * 100)
    log.info("Rule vs AI agreement: %d/%d (%.0f%%)", agree, len(df), agree / len(df) * 100)
    if disagree > 0:
        log.info("Disagreements:")
        mis = df[~df["rule_ai_match"]].head(10)
        for _, row in mis.iterrows():
            log.info("  '%s' rule=[%s/%s] ai=[%s/%s] reason=%s",
                     row["keyword_normalized"],
                     row["typ"], row["intent"],
                     row["ai_typ"], row["ai_intent"],
                     row["ai_reason"])

    log.info("")
    log.info("Next steps:")
    log.info("  Another round:  python src/categorization.py --test 20 --test-round %d", test_round + 1)
    log.info("  Other model:    python src/categorization.py --test 20 --model gpt-5.5")
    log.info("  Show prompt:    python src/categorization.py --dry-run")
    log.info("  Full run:       python src/categorization.py")


# --- Main ---


def main() -> None:
    parser = argparse.ArgumentParser(description="Categorize keywords")
    parser.add_argument("--input", type=Path, default=Path("data/interim/keywords_relevant.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/interim/keywords_categorized.csv"))
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--skip-ai", action="store_true", help="Only rule-based, no AI")
    parser.add_argument("--rule-only", action="store_true", help="Run rule-based only, save result, show few-shot for review")
    parser.add_argument("--continue-ai", action="store_true", help="Load rule-only result, run AI on low-confidence")
    parser.add_argument("--test", type=int, default=0, help="Test N random keywords (rule + AI)")
    parser.add_argument("--test-round", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true", help="Show prompt, no API call")
    parser.add_argument("--auto", action="store_true", help="Full run without stopping (rule + AI + post)")
    args = parser.parse_args()

    load_env(args.project_root)

    params = load_params(args.project_root)
    ai_cfg = params.get("ai", {})
    model = args.model or ai_cfg.get("default_model", "gpt-5.5")
    batch_size = args.batch_size or ai_cfg.get("batch_size", 30)

    if not args.input.exists():
        log.error("Input not found: %s", args.input)
        sys.exit(1)

    df = pd.read_csv(args.input, encoding="utf-8-sig")
    log.info("Loaded %d keywords from %s", len(df), args.input)

    # --- TEST ---
    if args.test > 0:
        sample = df.sample(min(args.test, len(df)), random_state=42 + args.test_round).reset_index(drop=True)
        run_test(sample, params, model, batch_size, args.output.parent, args.test_round)
        return

    # --- DRY RUN ---
    if args.dry_run:
        df_sample = df.sample(min(50, len(df)), random_state=42).reset_index(drop=True)
        df_sample = rule_based_categorize(df_sample, params)
        few_shot = extract_few_shot(df_sample, ai_cfg.get("few_shot_count", 20))
        sample_kws = df_sample[df_sample["categorization_confidence"] == "low"]["keyword_normalized"].head(5).tolist()
        if not sample_kws:
            sample_kws = df_sample["keyword_normalized"].head(5).tolist()
        bigrams = get_ngrams(df["keyword_normalized"].tolist(), n=2, top=20)
        ngram_ctx = "Top bi-gramy: " + ", ".join(f"'{g}' ({c}x)" for g, c in bigrams)
        prompt = build_categorization_prompt(sample_kws, params, few_shot, ngram_ctx)
        print("=" * 60)
        print("DRY RUN — Prompt preview:")
        print("=" * 60)
        print(prompt)
        print("=" * 60)
        print(f"Model: {model}, Batch: {batch_size}, Few-shot: {len(few_shot)}")
        return

    # --- RULE-ONLY MODE ---
    # Step A: run rule-based, save, show few-shot for review. Stop here.
    rule_only_path = args.output.parent / "keywords_rule_only.csv"

    if args.rule_only:
        log.info("RULE-ONLY MODE")
        log.info("Step 1: Rule-based categorization")
        df = rule_based_categorize(df, params)

        few_shot = extract_few_shot(df, ai_cfg.get("few_shot_count", 20))

        # Save rule-only result
        args.output.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(rule_only_path, index=False, encoding="utf-8-sig")
        log.info("Saved rule-only: %s (%d)", rule_only_path, len(df))

        # Show few-shot for review
        high_n = (df["categorization_confidence"] == "high").sum()
        low_n = (df["categorization_confidence"] == "low").sum()
        log.info("")
        log.info("=" * 50)
        log.info("RULE-ONLY SUMMARY")
        log.info("=" * 50)
        log.info("High confidence (rule-based): %d (%.0f%%)", high_n, high_n / len(df) * 100)
        log.info("Low confidence (need AI):     %d (%.0f%%)", low_n, low_n / len(df) * 100)
        log.info("")
        log.info("FEW-SHOT EXAMPLES that AI will use (%d):", len(few_shot))
        for ex in few_shot:
            log.info("  %-40s typ=%-12s produkt=%-15s intent=%s",
                     ex["keyword"][:40], ex["typ"], ex["produkt"], ex["intent"])
        log.info("")
        log.info("NEXT STEPS:")
        log.info("  1. Review few-shot examples above")
        log.info("  2. Adjust params.yaml if needed (add patterns, fix schema)")
        log.info("  3. Re-run rule-only if params changed: python src/categorization.py --rule-only")
        log.info("  4. When happy, run AI:                python src/categorization.py --continue-ai")
        return

    # --- CONTINUE-AI MODE ---
    # Step B: load rule-only result, run AI on low-confidence only.
    if args.continue_ai:
        if not rule_only_path.exists():
            log.error("No rule-only result found at %s. Run --rule-only first.", rule_only_path)
            sys.exit(1)

        log.info("CONTINUE-AI MODE — loading rule-only result")
        df = pd.read_csv(rule_only_path, encoding="utf-8-sig")
        log.info("Loaded %d keywords from %s", len(df), rule_only_path)

        few_shot = extract_few_shot(df, ai_cfg.get("few_shot_count", 20))

        log.info("Step 2: AI categorization (low-confidence only)")
        df = ai_classify_all(df, params, few_shot, model, batch_size, args.project_root)

        # Continue to money/validation/post-processing below
        # (falls through to shared finalization)

    # --- AUTO / FULL RUN ---
    elif args.auto or args.skip_ai:
        log.info("Step 1: Rule-based categorization")
        df = rule_based_categorize(df, params)
        few_shot = extract_few_shot(df, ai_cfg.get("few_shot_count", 20))

        if not args.skip_ai:
            log.info("Step 2: AI categorization")
            df = ai_classify_all(df, params, few_shot, model, batch_size, args.project_root)
        else:
            log.info("Step 2: AI SKIPPED")

    else:
        # Default (no flag) = same as --auto for backwards compat
        log.info("FULL RUN (rule-based + AI)")
        log.info("  TIP: Use --rule-only first to review few-shot before AI")
        log.info("")
        log.info("Step 1: Rule-based categorization")
        df = rule_based_categorize(df, params)
        few_shot = extract_few_shot(df, ai_cfg.get("few_shot_count", 20))

        log.info("Step 2: AI categorization")
        df = ai_classify_all(df, params, few_shot, model, batch_size, args.project_root)

    # --- SHARED FINALIZATION (money, validation, post-processing, save) ---

    log.info("Step 3: Money keywords")
    df = flag_money_keywords(df, params)

    log.info("Step 4: Validation")
    df = validate(df)

    log.info("Step 5: Post-processing")
    df = post_process(df, params)

    if "categorization_reason" not in df.columns:
        df["categorization_reason"] = ""

    # Save
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False, encoding="utf-8-sig")
    log.info("Saved: %s (%d)", args.output, len(df))

    money = df[df["priority"] == "money_keyword"]
    if len(money) > 0:
        money_path = args.output.parent / "money_keywords.csv"
        money.to_csv(money_path, index=False, encoding="utf-8-sig")
        log.info("Money keywords: %s (%d)", money_path, len(money))

    issues = df[df["categorization_issue"] != ""]
    if len(issues) > 0:
        issues_path = args.output.parent / "categorization_issues.csv"
        issues.to_csv(issues_path, index=False, encoding="utf-8-sig")
        log.info("Issues: %s (%d)", issues_path, len(issues))

    cleanup_checkpoint(args.project_root)

    # Summary
    log.info("=" * 50)
    log.info("CATEGORIZATION SUMMARY")
    log.info("=" * 50)
    log.info("Intent:")
    for intent, count in df["intent"].value_counts().items():
        log.info("  %-6s %d (%.1f%%)", intent, count, count / len(df) * 100)
    log.info("Money: %d", len(money))
    prods = df[df["produkt"] != ""]["produkt"].value_counts()
    if len(prods) > 0:
        log.info("Top products:")
        for prod, count in prods.head(10).items():
            log.info("  %-25s %d", prod, count)

    if not args.auto:
        issues_n = len(issues)
        if issues_n > 0:
            log.info("")
            log.info("REVIEW: %d consistency issues (see %s)", issues_n, args.output.parent / "categorization_issues.csv")


if __name__ == "__main__":
    main()
