# AKW Framework Documentation

Dokumentace AS IS — jak framework DNES funguje. Tato složka je referenční zdroj pravdy pro datové schéma, akceptační kritéria a klíčová rozhodnutí. Každý dokument odpovídá na jednu konkrétní otázku.

Provozní specifikace workflow (fáze 0-11, rule-based pravidla, prompty) žije v `/akw` skillu a v root `CLAUDE.md`. Zde je kondenzovaná, stabilní část, kterou chceme držet konzistentní napříč projekty.

## Struktura

### Referenční dokumenty

| Soubor | Odpovídá na otázku |
|--------|---------------------|
| [`data-contracts.md`](data-contracts.md) | Jaké má výstup každé fáze sloupce, typy, enum hodnoty? |
| [`acceptance-criteria.md`](acceptance-criteria.md) | Kdy je fáze hotová a správně? Jaké metriky kontrolovat? |

### Decisions (ADR)

Hard-won rozhodnutí, která se při opakovaných projektech snadno zapomenou. Každý ADR odpovídá na otázku *"Proč to děláme tak a ne jinak?"* a obsahuje, čím je validované.

| ADR | Téma |
|-----|------|
| [001](decisions/001-static-diacritics-map.md) | Static diacritics map (ne NFD decomposition) |
| [002](decisions/002-batch-size-30-50.md) | AI batch size 30-50 keywords |
| [003](decisions/003-xlsx-primary-output.md) | XLSX primary output formát |
| [004](decisions/004-rule-based-before-ai.md) | Rule-based klasifikace před AI |
| [005](decisions/005-checkpoint-resume-pattern.md) | Checkpoint/resume pattern v AI skriptech |
| [006](decisions/006-few-shot-examples.md) | Few-shot 15-20 příkladů pro AI kategorizaci |
| [007](decisions/007-test-mode-before-full-run.md) | Test mode (--test N) před full AI run |
| [008](decisions/008-mozna-third-state.md) | MOZNA jako 3. stav relevance (ne binární ANO/NE) |
| [009](decisions/009-word-order-dedup-opt-in.md) | Word-order dedup opt-in (default OFF) |
| [010](decisions/010-conversational-flow-checkpoints.md) | Konverzační flow s checkpointy (ne one-shot pipeline) |

## Dvě pravidla pro údržbu

1. **`docs/` popisuje aktuální stav.** Pokud něco v kódu změníš, updatuj odpovídající dokument ve stejném commitu.
2. **Nepiš sem historii.** Důvody a kontext změn patří do git commitů a do `tasks/<FW-XXX>/changelog.md`.
