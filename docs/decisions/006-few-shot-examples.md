# ADR-006: Few-shot 15-20 příkladů pro AI kategorizaci

- **Status:** accepted
- **Date:** 2026-04-23
- **Validated by:** DeLonghi, CPP, mBank

## Context

Při AI kategorizaci (fáze 5) LLM dostane KW a musí přiřadit `typ`, `produkt`, `brand`, `intent`, `funnel`. Bez kontextu klienta model hádá obecně, přesnost kolísá.

Klasické zlepšení je **few-shot learning** — do promptu přidat několik příkladů správné klasifikace. Otázka: **kolik příkladů** a **odkud je vzít**?

Zkoušeli jsme:
- 3 examples → model dostatečně nechápe schéma, velký odhad
- 5-10 examples → lepší, ale stále kolísavé na edge cases
- 50+ examples → prompt roste neúměrně, batch size se musí snižovat, cena roste

## Decision

**Default 20 few-shot examples** (rozsah 15-20), extrahovaných z rule-based výsledků:

1. Po rule-based pass vyber 20 KW s `categorization_confidence == "high"` flagem
2. Stratifikované napříč 4 intent hodnotami (INFO/COMM/TRANS/NAV) — `count // 4 + 1` na každou kategorii
3. Pokud výsledek > 20 → `random.sample` na přesný count
4. Slož do few-shot bloku v promptu
5. AI pak klasifikuje low-confidence keywords

Override přes `ai.few_shot_count` v `params.yaml` (hardcoded default 20).

## Reasoning

- **15-20 je sweet spot pro balanční pokrytí vs. prompt size**
  - Pokrývá základní typy (TRANS/INFO, money/non-money, vlastní/cizí brand)
  - Prompt nepřekračuje 2k tokens few-shot → zbývá místo pro schema + data
- **Z rule-based, ne manuálně**:
  - Manuálně psané příklady = bias autora, nemusí odpovídat reálným datům
  - Rule-based = skutečné KW z tohoto projektu, model vidí reálný pattern
  - Automatické = škáluje napříč klienty bez manuálního zásahu
- **Filtr `categorization_confidence == "high"`**:
  - Nechceš učit model ambiguous případům
  - High-confidence = "toto je určitě správně" → pevný anchor
  - Nastavuje se v rule-based logice podle počtu matchů + síly patternu
- **Stratifikace napříč 4 intent hodnotami** (INFO/COMM/TRANS/NAV):
  - Rovnoměrně `count // 4 + 1` na každou kategorii (pro count=20 → ~5 per intent, celkem 20-24 → random sample down na 20)
  - Zabrání situaci, kdy 20× TRANS a 0× INFO

## Consequences

**Pozitivní:**
- Výrazně vyšší konzistence klasifikace (shoda mezi batches ~92 % vs ~78 % bez few-shot)
- Model se adaptuje na specifické patterns klienta (nejen generický KW pattern)
- Zdarma, generuje se z rule-based výsledků

**Negativní:**
- Vyžaduje, aby rule-based pass měl aspoň 50+ high-confidence výsledků (jinak vybrat méně rozmanitých příkladů)
- Prompt je delší → batch size musí být spíše 30 než 50 (viz [ADR-002](002-batch-size-30-50.md))
- Při změně schematu / params.yaml musíš smazat checkpoint (few-shot se mění s pravidly)

## Implementace

```python
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
    return examples
```

## Prompt structure

```
System: You are expert keyword classifier for [client].
        Schema: [typ values, produkt values, intent enum, ...]

Few-shot:
  "svarecka mig 200a" → typ: produkt, produkt: svarecka, intent: TRANS
  "jak svarovat" → typ: navod, produkt: svarecka, intent: INFO
  ... (15-20 examples)

User: Classify these [batch_size] keywords:
  [batch of KW]
```

## When to revisit

- Pokud nové modely (GPT-5+, Claude 5) zvládají zero-shot klasifikaci s > 90 % přesností → few-shot by byl overhead
- Pokud přejdeme na custom fine-tuned model (ten má examples "built-in" během trainingu)
