"""Faze 4: Relevance classification.

Vectorized rule-based (ordered decision tree) + AI for uncertain keywords.
Multi-model support (OpenAI, Anthropic, Gemini).
Test mode includes AI + reasoning column. Iterative testing (multiple rounds).
Checkpoint/resume, exponential backoff, batched high-volume retry.

Outputs:
  - data/interim/keywords_relevant.csv (ANO only)
  - data/interim/keywords_with_relevance.csv (all)
  - data/interim/relevance_review.csv (flagged)
  - data/interim/relevance_test_N.csv (test round results)
  - checkpoint_relevance.json (resume support)

Usage:
    python src/relevance.py --test 25                          # DEFAULT: 25 KW, gpt-4o-mini
    python src/relevance.py --test 25 --model gpt-4o           # vyssi presnost
    python src/relevance.py --test 25 --model claude-haiku-4-5-20251001  # Anthropic alt
    python src/relevance.py --test 25 --model gemini-2.0-flash # Google alt
    python src/relevance.py                                    # full run
    python src/relevance.py --auto                             # full run, skip review
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DIACRITICS_MAP = str.maketrans(
    "\u00e1\u00e4\u010d\u010f\u00e9\u011b\u00ed\u013a\u013e\u0148"
    "\u00f3\u00f4\u0155\u0159\u0161\u0165\u00fa\u016f\u00fd\u017e"
    "\u00c1\u00c4\u010c\u010e\u00c9\u011a\u00cd\u0139\u013d\u0147"
    "\u00d3\u00d4\u0154\u0158\u0160\u0164\u00da\u016e\u00dd\u017d",
    "aacdeeillnoorrstuuyz"
    "AACDEEILLNOORRSTUUYZ",
)

# Supported models per provider
SUPPORTED_MODELS = {
    "openai": ["gpt-5.5", "gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1-nano"],
    "anthropic": ["claude-sonnet-4-5-20241022", "claude-haiku-4-5-20251001"],
    "gemini": ["gemini-2.0-flash", "gemini-2.5-flash-preview-05-20", "gemini-2.5-pro-preview-05-06"],
}


def remove_diacritics(text: str) -> str:
    """Remove diacritics using static map."""
    return text.translate(DIACRITICS_MAP)


def load_params(project_root: Path) -> dict:
    """Load params.yaml."""
    path = project_root / "params.yaml"
    if not path.exists():
        log.error("params.yaml not found at %s", path)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_business_research(project_root: Path) -> str:
    """Load business research for AI context."""
    path = project_root / "docs" / "business_research.md"
    if path.exists():
        return path.read_text(encoding="utf-8")[:3000]
    return ""


# --- Checkpoint ---


def load_checkpoint(project_root: Path) -> dict:
    path = project_root / "checkpoint_relevance.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"processed_batches": [], "results": {}}


def save_checkpoint(project_root: Path, checkpoint: dict) -> None:
    path = project_root / "checkpoint_relevance.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)


def cleanup_checkpoint(project_root: Path) -> None:
    path = project_root / "checkpoint_relevance.json"
    if path.exists():
        path.unlink()
        log.info("Checkpoint cleaned up")


# --- Rule-based classification (vectorized) ---


def build_combined_regex(terms: list[str]) -> re.Pattern | None:
    """Build single compiled regex from list of terms (with diacritics variants)."""
    if not terms:
        return None
    parts: list[str] = []
    for term in terms:
        if not isinstance(term, str) or not term.strip():
            continue
        t = re.escape(term.lower().strip())
        t_nodiac = re.escape(remove_diacritics(term.lower().strip()))
        parts.append(t)
        if t != t_nodiac:
            parts.append(t_nodiac)
    if not parts:
        return None
    return re.compile("|".join(parts))


def rule_based_classify(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Vectorized ordered decision tree (pandas boolean masking).

    Order:
    1. excluded -> NE
    2. products -> ANO
    3. competitor + product context -> ANO
    4. competitor alone -> MOZNA
    5. default -> MOZNA
    """
    rel_cfg = params.get("relevance", {})

    excluded_re = build_combined_regex(rel_cfg.get("excluded", []))
    product_re = build_combined_regex(rel_cfg.get("products", []))
    competitor_re = build_combined_regex(rel_cfg.get("competitors", []))

    df["relevance"] = "MOZNA"
    df["relevance_reason"] = "no pattern match"
    df["relevance_source"] = "rule"
    df["relevance_confidence"] = "low"

    kw = df["keyword_normalized"]
    kw_nodiac = kw.apply(remove_diacritics)

    def _matches(regex: re.Pattern | None) -> pd.Series:
        if regex is None:
            return pd.Series(False, index=df.index)
        return kw.str.contains(regex, na=False) | kw_nodiac.str.contains(regex, na=False)

    is_excluded = _matches(excluded_re)
    is_product = _matches(product_re)
    is_competitor = _matches(competitor_re)

    # Apply in REVERSE priority (later overwrites earlier)
    mask_comp_alone = is_competitor & ~is_product & ~is_excluded
    df.loc[mask_comp_alone, "relevance"] = "MOZNA"
    df.loc[mask_comp_alone, "relevance_reason"] = "competitor without product context"
    df.loc[mask_comp_alone, "relevance_confidence"] = "medium"

    mask_comp_product = is_competitor & is_product & ~is_excluded
    df.loc[mask_comp_product, "relevance"] = "ANO"
    df.loc[mask_comp_product, "relevance_reason"] = "competitor + product context"
    df.loc[mask_comp_product, "relevance_confidence"] = "high"

    mask_product = is_product & ~is_excluded
    df.loc[mask_product, "relevance"] = "ANO"
    df.loc[mask_product, "relevance_reason"] = "product match"
    df.loc[mask_product, "relevance_confidence"] = "high"

    df.loc[is_excluded, "relevance"] = "NE"
    df.loc[is_excluded, "relevance_reason"] = "excluded pattern"
    df.loc[is_excluded, "relevance_confidence"] = "high"

    counts = df["relevance"].value_counts()
    log.info(
        "Rule-based: ANO=%d, NE=%d, MOZNA=%d",
        counts.get("ANO", 0), counts.get("NE", 0), counts.get("MOZNA", 0),
    )
    return df


# --- AI classification (multi-model) ---


def detect_provider(model: str) -> str:
    """Detect provider from model name."""
    if model.startswith("claude"):
        return "anthropic"
    elif model.startswith("gemini"):
        return "gemini"
    else:
        return "openai"


def get_ai_client(model: str) -> tuple[object, str]:
    """Initialize AI client based on model name."""
    provider = detect_provider(model)

    if provider == "anthropic":
        import anthropic
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            log.error("ANTHROPIC_API_KEY not set in .env")
            sys.exit(1)
        return anthropic.Anthropic(api_key=key), provider

    elif provider == "gemini":
        import google.generativeai as genai
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            log.error("GEMINI_API_KEY not set in .env")
            sys.exit(1)
        genai.configure(api_key=key)
        return genai, provider

    else:  # openai
        import openai
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            log.error("OPENAI_API_KEY not set in .env")
            sys.exit(1)
        return openai.OpenAI(api_key=key), provider


def build_relevance_prompt(keywords: list[str], params: dict, business_research: str) -> str:
    """Build prompt for AI relevance classification."""
    rel = params.get("relevance", {})
    return f"""Jsi SEO analytik. Rozhodni u kazdeho keyword, zda je RELEVANTNI pro klienta.

## Klient
{rel.get('client_description', 'N/A')}

## Produkty/sluzby klienta (= relevantni)
{', '.join(str(p) for p in rel.get('products', []))}

## Cilove skupiny
{', '.join(str(t) for t in rel.get('target_groups', []))}

## Vyloucene temata (= nerelevantni)
{', '.join(str(e) for e in rel.get('excluded', []))}

## Business kontext
{business_research[:1500] if business_research else 'N/A'}

## Keywords k posouzeni
{chr(10).join(f'- {kw}' for kw in keywords)}

## Pravidla
- ANO = keyword je relevantni (produkt, sluzba, informacni obsah pro cilovou skupinu)
- NE = keyword neni relevantni (jiny obor, jiny produkt, nerelevantni kontext)
- MOZNA = nejiste, potrebuje lidsky review

## Odpovez PRESNE v JSON formatu (list):
[
  {{"keyword": "...", "relevance": "ANO/NE/MOZNA", "reason": "max 15 slov", "confidence": "high/medium/low"}}
]

Odpovez JEN JSON, nic jineho."""


def call_ai(
    prompt: str, client: object, provider: str, model: str
) -> str:
    """Call AI API and return raw text response. Supports OpenAI, Anthropic, Gemini."""
    if provider == "openai":
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=4000,
        )
        return response.choices[0].message.content

    elif provider == "anthropic":
        response = client.messages.create(
            model=model, max_tokens=4000, temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    elif provider == "gemini":
        import google.generativeai as genai
        gen_model = genai.GenerativeModel(model)
        response = gen_model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(temperature=0.1, max_output_tokens=4000),
        )
        return response.text

    else:
        raise ValueError(f"Unknown provider: {provider}")


def ai_classify_batch(
    keywords: list[str], params: dict, business_research: str,
    client: object, provider: str, model: str,
    max_retries: int = 3,
) -> list[dict]:
    """Classify batch with exponential backoff."""
    prompt = build_relevance_prompt(keywords, params, business_research)

    for attempt in range(max_retries):
        try:
            content = call_ai(prompt, client, provider, model)

            content = content.strip()
            if content.startswith("```"):
                content = re.sub(r"^```\w*\n?", "", content)
                content = re.sub(r"\n?```$", "", content)
            return json.loads(content)

        except json.JSONDecodeError as e:
            log.warning("JSON parse error (attempt %d/%d): %s", attempt + 1, max_retries, e)
        except Exception as e:
            delay = 2 ** attempt
            log.warning("API error (attempt %d/%d, retry in %ds): %s", attempt + 1, max_retries, delay, e)
            time.sleep(delay)

    return [{"keyword": kw, "relevance": "MOZNA", "reason": "AI error after retries", "confidence": "low"} for kw in keywords]


def ai_classify_all(
    df: pd.DataFrame, params: dict, business_research: str,
    model: str, batch_size: int, project_root: Path,
) -> pd.DataFrame:
    """Classify MOZNA keywords with AI, with checkpoint/resume."""
    mozna_mask = df["relevance"] == "MOZNA"
    mozna_kws = df.loc[mozna_mask, "keyword_normalized"].tolist()
    if not mozna_kws:
        log.info("No MOZNA keywords to classify")
        return df

    checkpoint = load_checkpoint(project_root)
    processed = set(checkpoint.get("processed_batches", []))
    cached_results = checkpoint.get("results", {})

    log.info("AI classification: %d keywords, batch=%d, model=%s", len(mozna_kws), batch_size, model)
    if processed:
        log.info("  Resuming: %d batches already done", len(processed))

    client, provider = get_ai_client(model)
    total_batches = (len(mozna_kws) + batch_size - 1) // batch_size

    for i in tqdm(range(0, len(mozna_kws), batch_size), desc="AI relevance", total=total_batches):
        batch_id = str(i)
        if batch_id in processed:
            continue

        batch = mozna_kws[i:i + batch_size]
        results = ai_classify_batch(batch, params, business_research, client, provider, model)

        for r in results:
            kw_key = r.get("keyword", "").lower().strip()
            cached_results[kw_key] = r

        processed.add(batch_id)
        checkpoint["processed_batches"] = list(processed)
        checkpoint["results"] = cached_results
        save_checkpoint(project_root, checkpoint)

        if i + batch_size < len(mozna_kws):
            time.sleep(0.5)

    # Map results back
    for idx in df.index[mozna_mask]:
        kw = df.loc[idx, "keyword_normalized"]
        if kw in cached_results:
            r = cached_results[kw]
            df.loc[idx, "relevance"] = r.get("relevance", "MOZNA")
            df.loc[idx, "relevance_reason"] = r.get("reason", "")
            df.loc[idx, "relevance_source"] = "ai"
            df.loc[idx, "relevance_confidence"] = r.get("confidence", "medium")

    # High-volume MOZNA retry — BATCHED
    if "volume" in df.columns:
        still_mozna_high = (df["relevance"] == "MOZNA") & (df["volume"] > 500)
        retry_kws = df.loc[still_mozna_high, "keyword_normalized"].tolist()
        if retry_kws:
            log.info("High-volume MOZNA retry: %d keywords (vol>500)", len(retry_kws))
            for attempt in range(3):
                remaining = df.loc[
                    (df["relevance"] == "MOZNA") & (df["volume"] > 500),
                    "keyword_normalized",
                ].tolist()
                if not remaining:
                    break
                log.info("  Retry %d: %d keywords", attempt + 1, len(remaining))
                for i in range(0, len(remaining), batch_size):
                    batch = remaining[i:i + batch_size]
                    results = ai_classify_batch(
                        batch, params, business_research, client, provider, model
                    )
                    for r in results:
                        kw_key = r.get("keyword", "").lower().strip()
                        if r.get("relevance") != "MOZNA":
                            mask = df["keyword_normalized"] == kw_key
                            df.loc[mask, "relevance"] = r.get("relevance", "MOZNA")
                            df.loc[mask, "relevance_reason"] = r.get("reason", "")
                            df.loc[mask, "relevance_source"] = "ai_retry"
                            df.loc[mask, "relevance_confidence"] = r.get("confidence", "medium")
                    time.sleep(0.5)

    counts = df["relevance"].value_counts()
    log.info("After AI: ANO=%d, NE=%d, MOZNA=%d", counts.get("ANO", 0), counts.get("NE", 0), counts.get("MOZNA", 0))
    return df


# --- Validation ---


def flag_for_review(df: pd.DataFrame) -> pd.DataFrame:
    """Flag suspicious classifications."""
    df["review_flag"] = ""

    if "volume" in df.columns:
        df.loc[(df["relevance"] == "NE") & (df["volume"] > 500), "review_flag"] = "HIGH_VOL_NE"

    df.loc[
        (df["relevance"] == "ANO") & df["relevance_reason"].str.contains("competitor", na=False),
        "review_flag",
    ] = "COMPETITOR_ANO"

    df.loc[
        (df["relevance_confidence"] == "low") & (df["review_flag"] == ""),
        "review_flag",
    ] = "LOW_CONFIDENCE"

    df.loc[
        (df["relevance"] == "MOZNA") & (df["review_flag"] == ""),
        "review_flag",
    ] = "MOZNA_UNRESOLVED"

    flagged = df[df["review_flag"] != ""]
    log.info("Flagged for review: %d keywords", len(flagged))
    return df


# --- Test mode ---


def run_test(
    df: pd.DataFrame, params: dict, business_research: str,
    model: str, batch_size: int, output_dir: Path, test_round: int,
) -> pd.DataFrame:
    """Run test: rule-based + AI on sample. Saves test results with reasoning.

    Test includes AI so user can see full classification with reasoning
    before committing to full run.
    """
    log.info("TEST ROUND %d: %d keywords, model=%s", test_round, len(df), model)

    # Rule-based first
    df = rule_based_classify(df, params)

    # AI for ALL keywords (not just MOZNA) — in test mode we want to see AI reasoning for everything
    log.info("AI classification (test mode — all keywords get AI reasoning)")
    client, provider = get_ai_client(model)

    kw_list = df["keyword_normalized"].tolist()
    all_results: list[dict] = []

    for i in tqdm(range(0, len(kw_list), batch_size), desc=f"Test AI ({model})"):
        batch = kw_list[i:i + batch_size]
        results = ai_classify_batch(batch, params, business_research, client, provider, model)
        all_results.extend(results)
        if i + batch_size < len(kw_list):
            time.sleep(0.5)

    # Add AI results as separate columns (keep rule-based for comparison)
    result_map = {r.get("keyword", "").lower().strip(): r for r in all_results}

    df["ai_relevance"] = ""
    df["ai_reason"] = ""
    df["ai_confidence"] = ""
    df["ai_model"] = model

    for idx in df.index:
        kw = df.loc[idx, "keyword_normalized"]
        if kw in result_map:
            r = result_map[kw]
            df.loc[idx, "ai_relevance"] = r.get("relevance", "")
            df.loc[idx, "ai_reason"] = r.get("reason", "")
            df.loc[idx, "ai_confidence"] = r.get("confidence", "")

    # Agreement check
    df["rule_ai_match"] = df["relevance"] == df["ai_relevance"]
    agree = df["rule_ai_match"].sum()
    disagree = len(df) - agree
    log.info("Rule vs AI agreement: %d/%d (%.0f%%), disagreements: %d", agree, len(df), agree / len(df) * 100, disagree)

    # Save test results
    test_path = output_dir / f"relevance_test_{test_round}.csv"
    df.to_csv(test_path, index=False, encoding="utf-8-sig")
    log.info("Saved test results: %s", test_path)

    # Summary
    ai_counts = df["ai_relevance"].value_counts()
    log.info("=" * 50)
    log.info("TEST ROUND %d SUMMARY (model: %s)", test_round, model)
    log.info("=" * 50)
    log.info("Rule-based:")
    for label in ["ANO", "NE", "MOZNA"]:
        c = (df["relevance"] == label).sum()
        log.info("  %-6s %d", label, c)
    log.info("AI (%s):", model)
    for label in ["ANO", "NE", "MOZNA"]:
        c = ai_counts.get(label, 0)
        log.info("  %-6s %d", label, c)
    log.info("Disagreements: %d", disagree)
    if disagree > 0:
        log.info("Examples where rule != AI:")
        mismatches = df[~df["rule_ai_match"]].head(10)
        for _, row in mismatches.iterrows():
            log.info("  '%s' rule=%s ai=%s (ai_reason: %s)",
                     row["keyword_normalized"], row["relevance"], row["ai_relevance"], row["ai_reason"])

    log.info("")
    log.info("Review %s, adjust params.yaml, then:", test_path)
    log.info("  - Another test round: python src/relevance.py --test 50 --test-round %d", test_round + 1)
    log.info("  - Different model:    python src/relevance.py --test 50 --model gpt-5.5")
    log.info("  - Full run:           python src/relevance.py")

    return df


# --- Main ---


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Classify keyword relevance")
    parser.add_argument("--input", type=Path, default=Path("data/interim/keywords_clean.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/interim/keywords_relevant.csv"))
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--model", type=str, default="gpt-4o-mini",
                        help="AI model — default: gpt-4o-mini. Alternativy: gpt-4o, "
                             "claude-haiku-4-5-20251001, gemini-2.0-flash")
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--skip-ai", action="store_true", help="Only rule-based (NEDOPORUCENE — AI je validacni vrstva)")
    parser.add_argument("--test", type=int, default=0,
                        help="Test mode: process N random keywords (default doporuceno: 25). "
                             "Rule-based + AI pro vsechny + tabulka keyword|relevance|reasoning.")
    parser.add_argument("--test-round", type=int, default=1, help="Test round number (for iterative testing)")
    parser.add_argument("--auto", action="store_true", help="Auto mode: skip MOZNA review")
    args = parser.parse_args()

    # Load .env — fallback chain: project → data/ → ~/Documents/Akws/.env → ~/.env
    _env_candidates = [
        args.project_root / ".env",
        args.project_root / "data" / ".env",
        Path.home() / "Documents" / "Akws" / ".env",
        Path.home() / ".env",
    ]
    for env_path in _env_candidates:
        if env_path.exists():
            load_dotenv(env_path)
            log.info("Loaded API keys from %s", env_path)
            break

    params = load_params(args.project_root)
    ai_cfg = params.get("ai", {})
    model = args.model or ai_cfg.get("default_model", "gpt-5.5")
    batch_size = args.batch_size or ai_cfg.get("batch_size", 30)
    business_research = load_business_research(args.project_root)

    # Load data
    if not args.input.exists():
        log.error("Input file not found: %s", args.input)
        sys.exit(1)

    df = pd.read_csv(args.input, encoding="utf-8-sig")
    log.info("Loaded %d keywords from %s", len(df), args.input)

    # --- TEST MODE ---
    if args.test > 0:
        sample = df.sample(min(args.test, len(df)), random_state=42 + args.test_round).reset_index(drop=True)
        log.info("TEST MODE: %d random keywords (round %d)", len(sample), args.test_round)
        run_test(sample, params, business_research, model, batch_size, args.output.parent, args.test_round)
        return

    # --- FULL RUN ---

    # Step 4.1: Rule-based
    log.info("Step 4.1: Rule-based classification")
    df = rule_based_classify(df, params)

    # Step 4.2: AI
    if not args.skip_ai:
        log.info("Step 4.2: AI classification")
        df = ai_classify_all(df, params, business_research, model, batch_size, args.project_root)
    else:
        log.info("Step 4.2: AI SKIPPED (--skip-ai)")

    # Step 4.3: Validation
    log.info("Step 4.3: Validation")
    df = flag_for_review(df)

    # Save
    args.output.parent.mkdir(parents=True, exist_ok=True)

    all_path = args.output.parent / "keywords_with_relevance.csv"
    df.to_csv(all_path, index=False, encoding="utf-8-sig")
    log.info("Saved all: %s (%d)", all_path, len(df))

    relevant = df[df["relevance"] == "ANO"].copy()
    relevant.to_csv(args.output, index=False, encoding="utf-8-sig")
    log.info("Saved relevant (ANO): %s (%d)", args.output, len(relevant))

    flagged = df[df["review_flag"] != ""].copy()
    if len(flagged) > 0:
        review_path = args.output.parent / "relevance_review.csv"
        flagged.to_csv(review_path, index=False, encoding="utf-8-sig")
        log.info("Saved review: %s (%d)", review_path, len(flagged))

    if not args.test:
        cleanup_checkpoint(args.project_root)

    # Summary
    counts = df["relevance"].value_counts()
    log.info("=" * 50)
    log.info("RELEVANCE SUMMARY")
    log.info("=" * 50)
    for label in ["ANO", "NE", "MOZNA"]:
        c = counts.get(label, 0)
        log.info("%-6s %d (%.1f%%)", label, c, c / len(df) * 100 if len(df) > 0 else 0)

    if not args.auto:
        mozna_count = counts.get("MOZNA", 0)
        if mozna_count > 0:
            log.info("")
            log.info("INTERACTIVE: %d MOZNA keywords need review (see %s)",
                     mozna_count, args.output.parent / "relevance_review.csv")


if __name__ == "__main__":
    main()
