# ADR-004: Rule-based klasifikace před AI

- **Status:** accepted
- **Date:** 2026-04-23
- **Validated by:** všechny projekty od mBank dále

## Context

Fáze 4 (Relevance) a 5 (Kategorizace) řeší klasifikační problém: zařadit KW do předem definovaných kategorií (ANO/NE/MOZNA; typ/produkt/intent).

Existují dvě naivní strategie:

1. **AI-only**: pošli vše do LLM, nech model rozhodnout
2. **Rule-only**: definuj všechna pravidla dopředu, AI se nepoužije

Obě jsou v praxi špatně.

## Decision

**Hybridní přístup s rule-based jako first pass**:

1. Rule-based pre-filter → zpracuje 60-80 % KW deterministicky
2. AI → jen na zbytek (typicky `MOZNA` nebo low-confidence KW)
3. Human review → flagged keywords

Rule-based MUSÍ běžet před AI, ne paralelně, ne po něm.

## Reasoning

### Proč ne AI-only

- **Náklady**: 10 000 KW × 1 request = $10-50 podle modelu. U 100 000 KW neakceptovatelné
- **Latency**: hodiny až dny čekání, nemožnost iterovat
- **Nekonzistence**: stejný KW v různých batchích může dostat jiný verdikt (halucinace, batch context pollution)
- **Známé patterns**: `"esab svarecka"` je evidentně ANO (competitor + product), proč to posílat do LLM

### Proč ne rule-only

- **Křehkost**: nová produktová kategorie = rozšiřovat pravidla, snadno vznikají díry
- **Nejednoznačné KW**: `"invertor na svarovani"` nezachytí žádné pravidlo → LLM to vyřeší kontextem
- **Synonyma a překlepy**: LLM je v tom silný, pravidla slabá

### Proč hybrid v tomto pořadí

- Rule-based je **zadarmo a rychlé**, odfiltruje snadné případy
- Na LLM jde **jen těžký zbytek** (MOZNA) → 10× nižší náklady
- Rule-based výsledky = **few-shot examples** pro LLM → vyšší přesnost klasifikace (viz [ADR-006](006-few-shot-examples.md))
- Auditovatelnost: v `relevance_source` vidíš, zda rozhodlo pravidlo nebo AI

## Consequences

**Pozitivní:**
- Nízké náklady (pravidla řeší 60-80 %, LLM jen zbytek)
- Rychlost — většina KW se řeší za minuty, ne hodiny
- Transparentnost — rule output je debuggable
- Konzistence — stejný KW = stejný verdikt (deterministické pravidlo)

**Negativní:**
- Dva různé codepaths (rule + AI) = víc kódu na údržbu
- Vyžaduje dobře napsaný `params.yaml` (patterns, blacklisty)
- Pravidla je nutné ladit pro každého klienta

## Workflow

### Fáze 4 (relevance) — lineární

```
params.yaml (products, excluded, competitors)
    ↓
Rule-based pass → ANO/NE (60-80 %) + MOZNA zbytek
    ↓
AI pass (jen MOZNA) → ANO/NE/stále MOZNA
    ↓
Human review (flagged + stále MOZNA)
```

### Fáze 5 (kategorizace) — inspection workflow

Kategorizace je komplexnější (víc dimenzí: typ/produkt/brand/intent/funnel) → má **tří-módový** běh, který umožňuje lidský review **před** AI:

```
                                    ┌─ --rule-only ────────────────┐
                                    │ 1. Rule-based categorization │
                                    │ 2. Extract few-shot (20 KW)  │
                                    │ 3. Uložit rule_only.csv       │
                                    │ 4. UKÁZAT few-shot v logu     │
                                    │ 5. KONEC — human review       │
                                    └──────────┬───────────────────┘
                                               │
                             (ladit params.yaml a opakovat --rule-only)
                                               │
                                    ┌─ --continue-ai ──────────────┐
                                    │ 6. Načíst rule_only.csv       │
                                    │ 7. AI na low-confidence (~20%)│
                                    │ 8. Finalizace (money, validace)│
                                    └──────────────────────────────┘

Alternativně: default / --auto = inline (bez mezistage review)
```

**Proč tento split existuje** (`--rule-only` / `--continue-ai`):

- AI běh stojí peníze a čas. Chceš **nejdřív zkontrolovat**, jaké few-shot examples AI dostane (→ dramaticky ovlivňují output quality)
- Pokud schema v params.yaml má mezeru, uvidíš to v rule-based výsledcích **před** tím, než zaplatíš za AI
- Iterativní cyklus: rule-only → review few-shot → ladit params.yaml → rerun rule-only → spokojen → `--continue-ai`

## When to revisit

- Pokud LLM cost klesne o řád a latency o řád (tj. pokud AI-only přestane být prohibitive)
- Pokud custom fine-tuned model dá > 95 % přesnost s low cost (specializovaný model pro tento use case)
