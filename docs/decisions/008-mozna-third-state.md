# ADR-008: MOZNA jako 3. stav relevance (ne binární ANO/NE)

- **Status:** accepted
- **Date:** 2026-04-23
- **Validated by:** llentab (`src/relevance.py:145-178`, reálná data: 90.2 % MOZNA)

## Context

Fáze 4 (Relevance) odpovídá na otázku: *"Je toto keyword pro klienta relevantní?"*

Naivní přístupy:

1. **Binární ANO/NE** — rule-based musí rozhodnout i u hraničních případů, vznikají false positives/negatives
2. **Confidence score (0.0–1.0)** — vyžaduje kalibraci a threshold tuning; výstup jako `0.62` je neintuitivní pro human review
3. **Probabilistic label + threshold** — varianta confidence score, stejný problém

## Decision

**Třístupňová relevance: `ANO` / `NE` / `MOZNA`**

- `ANO` — jasně relevantní (pravidlo nebo AI s high confidence)
- `NE` — jasně nerelevantní (pravidlo nebo AI s high confidence)
- `MOZNA` — explicitní nejistota → cílí se na AI retry nebo human review

Implementováno v `src/relevance.py` (viz llentab referenční projekt).

## Reasoning

### Proč ne binární

Rule-based decision tree musí každý KW zařadit. U hraničních KW (`"invertor na svařování"`, `"argon 8l"`) to vede k:
- False positives: vágní pravidlo dostane "skoro match" → ANO, ale KW je nerelevantní
- False negatives: pravidlo chybí → NE, ale KW je relevantní (neviditelná ztráta)

Binární přístup tuto chybu schová. MOZNA ji zviditelní.

### Proč ne confidence score

- `0.62` vs `0.58` — kde je threshold? Každý projekt by potřeboval jiný.
- Neintuitivní pro human review: víc mentální zátěže než `ANO/NE/MOZNA`.
- LLM confidence scores nejsou calibrated — model často říká `0.9` i pro nepřesné predikce.

### Proč MOZNA funguje

- **Explicitní "nevím"**: rule-based nemusí hádat, stačí říct `MOZNA`.
- **AI batch je zacílený**: na AI jdou jen `MOZNA`, ne celý dataset → úspora závisí na projektu (typicky 30-70 % MOZNA po rule-based; edge case llentab 90 %).
- **Human review path**: `MOZNA` po AI retry zůstává jako `MOZNA` s flagem `LOW_CONFIDENCE` nebo `MOZNA_UNRESOLVED` → konzultant rozhodne.
- **Transparentnost**: v `relevance_source` vidíš `rule / ai / ai_retry / manual`, v `review_flag` vidíš důvod flagu.

### Kdy MOZNA zůstane jako výstup

Pokud AI nedokáže rozhodnout (low confidence i po `ai_retry`) → `MOZNA` s `review_flag = MOZNA_UNRESOLVED` je legitimní výstup. KW se nezahazuje, jen se označí pro human review. Lepší než forcované špatné rozhodnutí.

## Consequences

**Pozitivní:**
- Chyby v edge cases jsou viditelné, ne schované
- AI běží jen na subset dat → šetří náklady (podle projektu různě)
- Human review má jasný vstupní seznam (`relevance_review.csv` = všechny flagged KW)
- `MOZNA_UNRESOLVED` jako valid output — nezahazujeme KW jen proto, že si nejsme jisti

**Negativní:**
- Třetí stav musí být handled v každé části pipeline (cleaning, kategorizace, reporting)
- Neintuitivní pro nové uživatele — "proč jsme to nerozhodli automaticky?"
- `MOZNA` zbytky po AI vyžadují human review → pomalejší throughput
- **Edge case risk**: u doménově těžkých projektů může MOZNA dominovat (llentab: 90.2 % MOZNA) → AI batch není úspora, naopak skoro full run

## Enum

```
relevance:    ANO | NE | MOZNA
review_flag:  HIGH_VOL_NE | COMPETITOR_ANO | LOW_CONFIDENCE | MOZNA_UNRESOLVED | <prazdne>
```

**Poznámka k `RELEVANCE_LEAK_MOZNA`**: tento flag **není** výstupem fáze 4. Generuje se post-hoc po fázi 5 (kategorizace), když se zjistí, že KW označené jako MOZNA proklouzly do kategorizace → ukládá se do `relevance_leak_review.csv`.

## Reality check (llentab)

V llentab (architektonická terminologie, hard-domain projekt) rozdělení:

- `ANO`: 630 (6.5 %)
- `NE`: 312 (3.2 %)
- `MOZNA`: 8 705 (90.2 %)

Všechny MOZNA byly flagované `LOW_CONFIDENCE` a uložené do `relevance_review.csv`. AI fáze 4 v tomto projektu vůbec neběžela — projekt dokončil se všemi MOZNA zachovanými. Přesto doběhl úspěšně do kategorizace (money keywords 14.9 %).

**Lesson:** MOZNA funguje i u extrémních rozdělení — framework nezkolaboval, review je explicitně delegován na člověka.

## Related

- [ADR-004](004-rule-based-before-ai.md) — rule-based jako first pass generuje MOZNA pool
- [ADR-005](005-checkpoint-resume-pattern.md) — checkpointy pro high-volume MOZNA retry
- [ADR-007](007-test-mode-before-full-run.md) — test mode ukáže kolik MOZNA zůstane po rule-based
