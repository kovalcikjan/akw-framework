# ADR-008: MOZNA jako 3. stav relevance (ne binární ANO/NE)

- **Status:** accepted
- **Date:** 2026-04-23
- **Validated by:** všechny projekty od mBank dále

## Context

Fáze 4 (Relevance) odpovídá na otázku: *"Je toto keyword pro klienta relevantní?"*

Naivní přístupy:

1. **Binární ANO/NE** — rule-based musí rozhodnout i u hraničních případů, vznikají false positives/negatives
2. **Confidence score (0.0–1.0)** — vyžaduje kalibraci, threshold tuning; výstup jako `0.62` je neintuitivní
3. **Probabilistic label + threshold** — varianta confidence score, stejný problém

## Decision

**Třístupňová relevance: ANO / NE / MOZNA**

- `ANO` — jasně relevantní (pravidlo nebo AI s high confidence)
- `NE` — jasně nerelevantní (pravidlo nebo AI s high confidence)
- `MOZNA` — explicitní nejistota → vstup do human review nebo AI retry

## Reasoning

### Proč ne binární

Rule-based decision tree musí každý KW zařadit. U hraničních KW (`"invertor na svařování"`, `"argon 8l"`) to vede k:
- False positives: vágní pravidlo dostane "skoro match" → ANO, ale KW je nerelevantní
- False negatives: pravidlo chybí → NE, ale KW je relevantní (neviditelná ztráta)

Binární přístup tuto chybu schová. MOZNA ji zviditelní.

### Proč ne confidence score

- `0.62` vs `0.58` — kde je threshold? Každý projekt by potřeboval jiný.
- Neintuitivní pro human review: víc mentální zátěže než `ANO/NE/MOZNA`.
- LLM confidence scores nejsou calibrated — model říká `0.9` i pro nepřesné predikce.

### Proč MOZNA funguje

- **Explicitní "nevím"**: rule-based nemusí hádat, stačí říct `MOZNA`.
- **Menší AI batch**: na AI jdou jen `MOZNA` (~20-40 % z celku), ne celý dataset → 3-5× nižší náklady.
- **Human review path**: `MOZNA` po AI = `MOZNA_UNRESOLVED` flag → konzultant rozhodne.
- **Transparentnost**: v `relevance_source` vidíš `rule/ai/manual`, v `review_flag` vidíš `MOZNA_UNRESOLVED`.

### Kdy MOZNA zůstane jako výstup

Pokud AI nedokáže rozhodnout (low confidence i po retry) → `MOZNA_UNRESOLVED` je legitimní výstup. KW se nezahazuje, jen se označí pro human review. To je lepší než forcované špatné rozhodnutí.

## Consequences

**Pozitivní:**
- Chyby v edge cases jsou viditelné, ne schované
- AI batch je 2-4× menší → nižší náklady
- Human review má jasný vstupní seznam (flagged MOZNA)
- `MOZNA_UNRESOLVED` jako valid output — nezahazujeme KW jen proto, že si nejsme jisti

**Negativní:**
- Třetí stav musí být handled v každé části pipeline (cleaning, kategorizace, reporting)
- Neintuitivní pro nové uživatele — "proč jsme to nerozhodli automaticky?"
- `MOZNA` zbytky po AI vyžadují human review → pomalejší throughput

## Enum

```
relevance: ANO | NE | MOZNA
review_flag: LOW_CONFIDENCE | RELEVANCE_LEAK_MOZNA | MOZNA_UNRESOLVED
```

## Related

- [ADR-004](004-rule-based-before-ai.md) — rule-based jako first pass generuje MOZNA pool
- [ADR-007](007-test-mode-before-full-run.md) — test mode ukáže kolik MOZNA zůstane po rule-based
