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

**15-20 few-shot examples**, extrahovaných z rule-based výsledků:

1. Po rule-based pass vyber 15-20 KW s nejvyšší confidence (matched více pravidly)
2. Ty slož do few-shot bloku v promptu
3. AI pak klasifikuje zbývající MOZNA / low-confidence KW

## Reasoning

- **15-20 je sweet spot pro balanční pokrytí vs. prompt size**
  - Pokrývá základní typy (TRANS/INFO, money/non-money, vlastní/cizí brand)
  - Prompt nepřekračuje 2k tokens few-shot → zbývá místo pro schema + data
- **Z rule-based, ne manuálně**:
  - Manuálně psané příklady = bias autora, nemusí odpovídat reálným datům
  - Rule-based = skutečné KW z tohoto projektu, model vidí reálný pattern
  - Automatické = škáluje napříč klienty bez manuálního zásahu
- **High-confidence (> 1 pravidlo match)**:
  - Nechceš učit model ambiguous případům
  - High-confidence = "toto je určitě správně" → pevný anchor
- **Rozmanitost příkladů**: algoritmus vybírá napříč kategoriemi (ne 20× TRANS a nic INFO)

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
def extract_few_shot(rule_results, count=18):
    """
    Vybere diverzní sadu high-confidence KW napříč kategoriemi.
    Cíl: pokrytí všech intent hodnot + money/non-money mix.
    """
    high_conf = rule_results[rule_results["rule_matches"] >= 2]
    # vyvazena sample: 5x INFO, 5x COMM, 5x TRANS, 3x NAV
    diverse = stratified_sample(high_conf, by="intent", per_group=5)
    return diverse.head(count)
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
