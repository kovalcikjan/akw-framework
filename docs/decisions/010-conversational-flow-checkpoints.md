# ADR-010: Konverzační flow s checkpointy (ne one-shot pipeline)

- **Status:** accepted
- **Date:** 2026-04-23
- **Validated by:** DeLonghi, mBank, llentab (bez checkpointů by nebyly opraveny mezivýsledky)

## Context

Framework zpracovává 1 000–15 000 KW přes 6 fází (cleaning → relevance → kategorizace → clustering). Existují dva přístupy k orchestraci:

1. **One-shot pipeline** — spustíš jeden příkaz, pipeline proběhne automaticky od fáze 1 do 6
2. **Konverzační flow** — každá klíčová fáze má checkpoint, před pokračováním proběhne human review

## Decision

**Konverzační flow s povinným checkpointem po fázích 3, 4, 5.** Fáze 1C, 2, 6 mohou běžet bez interakce (auto mode).

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
Výsledek: klient dostane analyzu bez hlavních KW, nikdo to neví
```

Ve fázi 5 nevidíš, že fáze 3 smazala důležitá data. Bez checkpointu po fázi 3 tento bug projde.

**Params.yaml je per-project**: produktové patterny, schema, excluded — vše záleží na konkrétním klientovi. One-shot pipeline předpokládá, že je params.yaml dokonalý od začátku. V praxi se ladí iterativně.

**Scope changes**: klient v průběhu projektu zpřesní scope ("vlastně tam nechci blogové KW") → checkpoint umožňuje přizpůsobit ještě před drahým AI runnem.

### Proč checkpointy fungují

- **Checkpoint cost je nízký**: 5–10 min review po fázi 3 (podívat se na Variant Clusters, sample check), 10–15 min po fázi 4 (projít MOZNA KW), 10 min po fázi 5 (sample 20 money keywords).
- **Iterativní ladění**: checkpointy umožňují `--rule-only → review → upravit params.yaml → rerun` bez placení za AI.
- **Auditovatelnost**: client nebo šéf se může podívat na mezivýsledky, ne jen finální output.

### Které fáze mají checkpoint a proč

| Fáze | Checkpoint | Důvod |
|------|-----------|-------|
| 1C merge | NE | Deterministické slučování souborů |
| 2 EDA | ANO (soft) | Doporučení z n-gramů musí schválit člověk |
| 3 Cleaning | ANO (hard) | Canonical selection a dedup ratio mají být zkontrolovány |
| 4 Relevance | ANO (hard) | MOZNA KW vyžadují human rozhodnutí |
| 5 Kategorizace | ANO (hard) | Few-shot quality + money keyword sample check |
| 6 Clustering | NE | Výpočet z existujících dat, lehce revertovatelný |

### Auto mode existence

Fáze s auto modem (1C, 2, 3, 6) mohou běžet bez checkpointů — ale uživatel si tím bere zodpovědnost. Skript stejně vypíše summary metriky (dedup ratio, source breakdown). Auto mode není "blind" — je "fast, no wait".

## Consequences

**Pozitivní:**
- Chyby odhaleny a opraveny early, před drahým AI runnem
- Iterativní ladění params.yaml bez plýtvání AI tokeny
- Scope flexibility — projekt se může přizpůsobit mid-run
- Auditovatelná pipeline pro klienta nebo QA

**Negativní:**
- Nelze spustit unattended (overnight batch)
- Pomalejší throughput vs. fully automated pipeline
- Vyžaduje dostupného konzultanta v klíčových bodech projektu
- Složitější implementace (checkpointy, run modes, state management)

## When to revisit

- Pokud se framework rozšíří na 50 000+ KW projekty kde human review není praktický
- Pokud přijde solid fine-tuned model s > 95 % přesností → auto mode pro fáze 4-5 by byl reálný
- Pokud tým má 3+ konzultantů a pipeline se paralelizuje → checkpointy by bylo třeba designovat pro async review

## Related

- [ADR-005](005-checkpoint-resume-pattern.md) — technická implementace checkpointů (JSON state)
- [ADR-004](004-rule-based-before-ai.md) — rule-only / continue-ai jako checkpoint vzor ve fázi 5
- [ADR-007](007-test-mode-before-full-run.md) — --test N jako mini-checkpoint před full AI run
