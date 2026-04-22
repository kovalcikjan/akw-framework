# ADR-002: AI batch size 30-50 keywords per prompt

- **Status:** accepted
- **Date:** 2026-04-23
- **Validated by:** mBank, CPP, DeLonghi, eVisions (4 projekty)

## Context

Fáze 4 (Relevance) a 5 (Kategorizace) posílají KW přes LLM API. Otázka: kolik KW na jedno volání?

Ranější projekty experimentovaly s batch size 1 (pomalé, drahé), 10 (stále neefektivní), 100+ (model ztrácí přesnost, nedodržuje schema).

## Decision

**Batch size 30-50 KW per prompt.** Default 30, můžeš jít do 50 pro jednoduché klasifikace s malým few-shot kontextem.

Nikdy **ne 1 per call**. Nikdy **ne 100+**.

## Reasoning

- **30-50 je sweet spot** — validováno napříč 4 projekty
- Pod 30: zbytečně drahé (režie promptu = instrukce + few-shot + schema dominuje nad daty)
- Nad 50: model začíná
  - Zapomínat schema (prázdné pole v odpovědi)
  - Ztrácet konzistenci (stejné KW jinak klasifikované v různých batchích)
  - Překračovat max output tokens, truncated odpověď
- Batch 30 × cena $0.15/1M tokens (gpt-4o-mini) ≈ $0.002 per batch, tedy $0.06 / 1000 KW

## Consequences

**Pozitivní:**
- Předvídatelné náklady (cena za 1000 KW)
- Konzistence výstupu
- Odolnost proti truncation

**Negativní:**
- Při rate-limit errorech ztrácíš větší batch najednou (oproti batch=1) — řešeno [ADR-005](005-checkpoint-resume-pattern.md)
- Musíš explicitně instruovat model, aby vrátil **přesně N** odpovědí, jinak někdy vrací míň

## Configuration

V `params.yaml`:

```yaml
ai:
  batch_size: 30   # default
  # batch_size: 50  # pro high-confidence klasifikace s malým schématem
```

## When to revisit

- Pokud GPT-4.x modely prokáží lepší konzistenci při batch 100+ (unlikely v blízké době)
- Pokud cena modelu výrazně klesne (nebude cenově výhodné tlačit batch dolů)
