# AKW Framework

Framework pro analýzu klíčových slov. Opakovaně použitelný pro klienty (e-shopy, služby, weby).

Tento repozitář obsahuje **framework samotný**, ne klientské projekty. Klientské projekty žijí v `/Users/admin/Documents/Akws/<klient>/` a mají vlastní `CLAUDE.md` + `params.yaml`.

## Kam pro co

| Potřebuješ | Kde najdeš |
|------------|------------|
| Detailní workflow (fáze 0-11, kroky, prompty) | `/akw` skill |
| Datové kontrakty (schema výstupů, enum) | [`docs/data-contracts.md`](docs/data-contracts.md) |
| Akceptační kritéria (kdy je fáze hotová) | [`docs/acceptance-criteria.md`](docs/acceptance-criteria.md) |
| Architektonická rozhodnutí | [`docs/decisions/`](docs/decisions/) (ADR 001-010) |
| Known issues + TODO | [`ISSUES.md`](ISSUES.md) |
| Aktuální stav frameworku | [`CURRENT.md`](CURRENT.md) |

## Quick reference — enum hodnoty

```
relevance:  ANO | NE | MOZNA
intent:     INFO | COMM | TRANS | NAV
funnel:     TOFU | MOFU | BOFU | BRAND
brand_type: own | competitor | retail
priority:   money_keyword | <prazdne>
confidence: high | medium | low
```

## Repo konvence (docs-process)

- **`docs/` = AS IS** — jak framework DNES funguje (zdroj pravdy pro schema, ADRs, kritéria)
- **`tasks/<FW-XXX>/` = TO BE** — specifikace budoucích změn
- **`projects/` = klientská data** — NIKDY necommitovat (gitignored)

Když měníš kód, updatuj odpovídající dokument v `docs/` ve stejném commitu.

## Referenční projekty

| Projekt | Cesta | K čemu |
|---------|-------|--------|
| llentab | `~/Documents/Akws/llentab/` | Hlavní reference — `src/*.py`, `params.yaml` ověřené proti docs |
| mBank | `~/Documents/Akws/mbank/` | `keyword_cleaner.py`, iterace v2 |
| DeLonghi | `~/Documents/Akws/Delonghi/` | Few-shot + checkpoint pattern |
| CPP | `~/Documents/Akws/CPP/` | Test mode pattern |

## Jak začít na klientském projektu

1. **Nový projekt** (`params.yaml` neexistuje) → spusť `/akw` skill, následuj fázi 0
2. **Rozpracovaný projekt** → přečti `CLAUDE.md` daného projektu + `params.yaml`, zjisti kde se skončilo, pokračuj od další fáze

## Klíčová pravidla

1. `data/raw` je **READ-ONLY** — pipeline výstupy jdou do `data/interim/`
2. Rule-based first, AI jen na `MOZNA` nebo low-confidence KW (viz [ADR-004](docs/decisions/004-rule-based-before-ai.md))
3. `--test N` před každým full AI runnem (viz [ADR-007](docs/decisions/007-test-mode-before-full-run.md))
4. Konzistentní enum hodnoty (viz výše) — žádné `ano`/`yes`/`True`
5. UTF-8 se signaturou BOM (`utf-8-sig`) pro Excel kompatibilitu
