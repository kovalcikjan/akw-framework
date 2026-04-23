# ADR-010: Konverzační flow s checkpointy (ne one-shot pipeline)

- **Status:** accepted
- **Date:** 2026-04-23
- **Validated by:** llentab (`src/relevance.py` + `src/categorization.py` obsahují `--auto` flag, checkpoint JSON, `--rule-only/--continue-ai` split)

## Context

Framework zpracovává 1 000–15 000 KW přes 6 fází (cleaning → relevance → kategorizace → clustering). Existují dva přístupy k orchestraci:

1. **One-shot pipeline** — spustíš jeden příkaz, pipeline proběhne automaticky od fáze 1 do 6
2. **Konverzační flow** — klíčové fáze (3, 4, 5) jsou designované pro human review mezi kroky, s mechanismy (checkpoint JSON, `--rule-only/--continue-ai`, `--test`) které to podporují

## Decision

**Konverzační flow jako doporučený workflow, ne hard-enforced gate.**

Skripty obsahují **mechanismy** pro checkpoint + review (`checkpoint_*.json`, `--rule-only`, `--test`, `--auto` flag), ale uživatel má možnost je obejít. Discipline > enforcement.

## Reasoning

### Proč ne one-shot pipeline

**Error propagation**: chyba v rané fázi se multiplikuje do pozdějších fází.

Příklad:
```
Fáze 3 (cleaning): blacklist byl příliš agresivní → smazal head terms
    ↓
Fáze 4 (relevance): few-shot examples jsou podivné (chybí důležité KW)
    ↓
Fáze 5 (kategorizace): money keywords mají bias (top volume KW chybí)
    ↓
Výsledek: klient dostane analýzu bez hlavních KW, nikdo to neví
```

Ve fázi 5 nevidíš, že fáze 3 smazala důležitá data. Bez checkpointu po fázi 3 tento bug projde.

**Params.yaml je per-project**: produktové patterny, schema, excluded — vše záleží na konkrétním klientovi. One-shot pipeline předpokládá, že je params.yaml dokonalý od začátku. V praxi se ladí iterativně.

**Scope changes**: klient v průběhu projektu zpřesní scope ("vlastně tam nechci blogové KW") → review point umožňuje přizpůsobit ještě před drahým AI runnem.

### Proč mechanism, ne hard gate

- **Flexibilita**: některé projekty jsou jednoduché a pipeline může běžet rychle — `--auto` flag to umožňuje.
- **Checkpoint JSON jako resume**: implementovaný primárně jako crash recovery, sekundárně jako review point (můžeš skript zastavit ručně a pokračovat později).
- **Realita**: zkušený konzultant někdy ví, že si v konkrétní fázi review nemusí dělat. Framework ho nenutí.

### Které fáze mají jaké mechanismy

| Fáze | Skript | Run modes | Checkpoint | Review pattern |
|------|--------|-----------|------------|----------------|
| 1C merge | `merge_sources.py` | jednofázový | — | výstup CSV se podívej ručně |
| 2 EDA | `eda_notebook_generator.py` | auto / `--run-as-script` | — | notebook, konverzační review sekce po sekci |
| 3 Cleaning | `cleaning.py` | jednofázový | — | XLSX multi-sheet = audit trail |
| 4 Relevance | `relevance.py` | `--test N`, `--skip-ai`, `--auto` | `checkpoint_relevance.json` | MOZNA review + `--auto` skip |
| 5 Kategorizace | `categorization.py` | `--rule-only`, `--continue-ai`, `--test N`, `--dry-run`, `--auto` | `checkpoint_categorization.json` | few-shot inspection před AI runnem |
| 6 Clustering | (optional) | auto | — | top 10 clusterů ručně |

**Hard dependence na human review:** žádná. Skripty poběží bez zastavení s `--auto`. Framework se spoléhá na disciplínu, ne na vynucování.

### --auto flag

V obou kritických skriptech (`relevance.py`, `categorization.py`) existuje `--auto`:
- `relevance.py --auto`: skipuje MOZNA review (viz `src/relevance.py:548` v llentab)
- `categorization.py --auto`: full run bez zastavení na review points (viz `src/categorization.py:571`)

Smysl: automatizované běhy (CI, batch processing, zkušený uživatel) bez interaktivity.

### --rule-only / --continue-ai ve fázi 5

Kategorizace má navíc **explicitní split** na rule-based a AI fázi:

```bash
python src/categorization.py --rule-only     # jen rule, ulož, UKAŽ few-shot
# (uživatel zkontroluje few-shot + rule výstupy, upraví params.yaml)
python src/categorization.py --continue-ai   # AI na low-confidence
```

To je **nejsilnější review point v celém frameworku** — protože AI ve fázi 5 stojí nejvíc a quality few-shot dramaticky ovlivňuje output. Split umožňuje iterovat params.yaml bez placení za AI.

## Consequences

**Pozitivní:**
- Chyby odhaleny a opraveny early, před drahým AI runnem
- Iterativní ladění params.yaml bez plýtvání AI tokeny (díky `--rule-only`)
- Scope flexibility — projekt se může přizpůsobit mid-run
- `--auto` flag pro zkušené uživatele nebo automatizaci
- Auditovatelná pipeline pro klienta nebo QA (výstupní soubory per fáze)

**Negativní:**
- Disciplína není vynucená — nezkušený uživatel může přeskočit review a neuvědomit si chybu
- Pomalejší throughput vs. fully automated pipeline
- Vyžaduje dostupného konzultanta v klíčových bodech projektu
- Složitější implementace (checkpointy, run modes, state management)
- `--auto` může schovat problémy, které by review odhalil

## Antipattern

Full auto pipeline bez kontroly:
```bash
# Nedoporučeno pro nový projekt:
python src/cleaning.py && \
python src/relevance.py --auto && \
python src/categorization.py --auto
```

Tohle funguje, ale ztrácíš value review pointů. Používej jen pro opakované runy známého projektu.

## When to revisit

- Pokud se framework rozšíří na 50 000+ KW projekty kde human review není praktický
- Pokud přijde solid fine-tuned model s > 95 % přesností → plně auto mode pro fáze 4-5 by byl reálný
- Pokud tým má 3+ konzultantů a pipeline se paralelizuje → review gates by bylo třeba designovat pro async review

## Related

- [ADR-005](005-checkpoint-resume-pattern.md) — technická implementace checkpointů (JSON state)
- [ADR-004](004-rule-based-before-ai.md) — rule-only / continue-ai jako konkrétní review point ve fázi 5
- [ADR-007](007-test-mode-before-full-run.md) — `--test N` jako mini-review před full AI run
