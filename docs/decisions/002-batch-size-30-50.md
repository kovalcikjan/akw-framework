# ADR-002: AI batch size 30-50 keywords per prompt

- **Status:** accepted
- **Date:** 2026-04-23
- **Validated by:** mBank, CPP, DeLonghi, eVisions (4 projekty)

## Context

Fáze 4 (Relevance) a 5 (Kategorizace) posílají KW přes LLM API. Otázka: kolik KW na jedno volání?

Ranější projekty experimentovaly s batch size 1 (pomalé, drahé), 10 (stále neefektivní), 100+ (model ztrácí přesnost, nedodržuje schema).

## Decision

**Default batch size 30 KW per prompt, doporučený rozsah 30-50 při override.**

- **Hardcoded default v kódu: 30** (`ai_cfg.get("batch_size", 30)` v `relevance.py` i `categorization.py`)
- **Override přes params.yaml** (`ai.batch_size`) nebo CLI (`--batch-size N`)
- Rozsah 30-50 je doporučený pro běžné klasifikace; konkrétní hodnota validovaná napříč projekty = 30

Nikdy **ne 1 per call**. Nikdy **ne 100+**.

## Reasoning

- **30 je ověřený default** — běží napříč projekty (mBank, CPP, DeLonghi, eVisions, llentab)
- **30-50 je doporučený rozsah** pro běžné klasifikace
- Pod 30: zbytečně drahé (režie promptu = instrukce + few-shot + schema dominuje nad daty)
- Nad 50: model začíná
  - Zapomínat schema (prázdné pole v odpovědi)
  - Ztrácet konzistenci (stejné KW jinak klasifikované v různých batchích)
  - Překračovat max output tokens, truncated odpověď

## Consequences

**Pozitivní:**
- Předvídatelné náklady (cena za 1000 KW)
- Konzistence výstupu
- Odolnost proti truncation

**Negativní:**
- Při rate-limit errorech ztrácíš větší batch najednou (oproti batch=1) — řešeno [ADR-005](005-checkpoint-resume-pattern.md)
- Musíš explicitně instruovat model, aby vrátil **přesně N** odpovědí, jinak někdy vrací míň

## Configuration

`ai:` blok v `params.yaml` je **volitelný** — pokud chybí, použije se hardcoded default `batch_size=30`. Skripty čtou `ai_cfg.get("batch_size", 30)`.

Pokud chceš override:

```yaml
ai:
  batch_size: 30   # default, stačí vynechat celý ai: blok
  # batch_size: 50  # pro jednoduché klasifikace, když chceš zrychlit
```

Jednorázový override z CLI:

```bash
python src/categorization.py --batch-size 40
```

## When to revisit

- Pokud GPT-4.x modely prokáží lepší konzistenci při batch 100+ (unlikely v blízké době)
- Pokud cena modelu výrazně klesne (nebude cenově výhodné tlačit batch dolů)
