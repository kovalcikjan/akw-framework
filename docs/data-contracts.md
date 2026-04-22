# Data Contracts

Definice výstupů jednotlivých fází frameworku. Tento dokument je **zdroj pravdy pro datové schéma**. Pokud se sloupce nebo enum hodnoty změní, musí se aktualizovat zde **a zároveň v kódu**.

## Princip

Každá fáze čte výstup předchozí fáze a produkuje vlastní výstup. Sloupce se **akumulují** — fáze 5 obsahuje všechno z fáze 4 + vlastní nové sloupce.

```
Fáze 1C → keywords_raw.csv
   ↓
Fáze 3  → keywords_clean.csv + keywords_clean.xlsx (5 listů)
   ↓
Fáze 4  → keywords_with_relevance.csv + keywords_relevant.csv (jen ANO)
   ↓
Fáze 5  → keywords_categorized.csv + money_keywords.csv
   ↓
Fáze 6  → keywords_clustered.csv (optional)
```

---

## Fáze 1C — keywords_raw.csv

Sloučený výstup všech zdrojů po initial dedup. Cesta: `data/interim/keywords_raw.csv`.

| Sloupec | Typ | Required | Poznámka |
|---------|-----|----------|----------|
| `keyword` | str | ✓ | Original, case-preserved |
| `keyword_normalized` | str | ✓ | lowercase, stripped |
| `source` | str | ✓ | `competitor_[domain]` / `gsc` / `client_seed` / `ahrefs` / `marketing_miner` / `reddit` / `paa` |
| `volume` | int | — | 0 pokud neznámý |
| `kd` | int | — | 0-100 |
| `position` | float | — | 1.0-100.0 |
| `url` | str | — | Ranking URL |

---

## Fáze 3 — keywords_clean.csv

Vyčistený, deduplikovaný dataset. Cesta: `data/interim/keywords_clean.csv`.

**Všechny sloupce z fáze 1C** +

| Sloupec | Typ | Required | Poznámka |
|---------|-----|----------|----------|
| `keyword_no_diacritics` | str | — | Pro matching |
| `all_variants` | str | — | Sloučené varianty, separator `\|` |
| `variant_count` | int | — | Počet sloučených variant |

### Doprovodné soubory

| Soubor | Účel |
|--------|------|
| `data/interim/keywords_clean.xlsx` | **Primární output** — multi-sheet (viz níže) |
| `data/interim/keywords_removed.csv` | Odebrané při dedup + `merged_into` + `removal_reason` |
| `data/interim/keywords_filtered_out.csv` | Odebrané filterem + `filter_reason` |

### XLSX listy (keywords_clean.xlsx)

| List | Obsah |
|------|-------|
| `Final Keywords` | Čisté KW (odpovídá keywords_clean.csv) |
| `All Keywords` | Všechny s flagy `is_duplicate`, `has_variant` |
| `Merged Variants` | Odebrané varianty s `merged_into` |
| `Variant Clusters` | `cluster_id`, `type`, všechny KW v clusteru, canonical |
| `Summary` | Metriky: input, exact dupes, diacritics, word-order, filtered, final |

### Enum hodnoty

- `removal_reason`: `exact_dedup` / `diacritics_dedup` / `word_order_dedup`
- `filter_reason`: `volume` / `length` / `blacklist: <term>`

---

## Fáze 4 — keywords_with_relevance.csv / keywords_relevant.csv

- `data/interim/keywords_with_relevance.csv` — **všechny** KW (ANO/NE/MOZNA)
- `data/interim/keywords_relevant.csv` — **jen ANO** (vstup pro fázi 5)

**Všechny sloupce z fáze 3** +

| Sloupec | Typ | Required | Poznámka |
|---------|-----|----------|----------|
| `relevance` | str | ✓ | **ANO** / **NE** / **MOZNA** |
| `relevance_reason` | str | ✓ | Max 15 slov |
| `relevance_source` | str | — | `rule` / `ai` |
| `relevance_confidence` | str | — | `high` / `medium` / `low` |

### Doprovodné soubory

| Soubor | Účel |
|--------|------|
| `data/interim/relevance_review.csv` | Flagged pro human review |
| `data/interim/checkpoint_relevance.json` | Progress pro resume |

---

## Fáze 5 — keywords_categorized.csv / money_keywords.csv

- `data/interim/keywords_categorized.csv` — všechny ANO KW s kategoriemi
- `data/interim/money_keywords.csv` — subset s `priority=money_keyword`

**Všechny sloupce z fáze 4 (jen ANO KW)** +

| Sloupec | Typ | Required | Poznámka |
|---------|-----|----------|----------|
| `typ` | str | — | Dle schema klienta v params.yaml |
| `produkt` | str | — | Dle schema klienta |
| `brand` | str | — | Název brandu |
| `brand_type` | str | — | `own` / `competitor` |
| `specifikace` | str | — | Cílová skupina / varianta |
| `intent` | str | ✓ | **INFO** / **COMM** / **TRANS** / **NAV** |
| `funnel` | str | ✓ | **TOFU** / **MOFU** / **BOFU** / **BRAND** |
| `priority` | str | — | `money_keyword` nebo prázdné |
| `categorization_reason` | str | — | Vysvětlení AI |

### Intent → Funnel mapping

| Intent | Funnel | Content type |
|--------|--------|--------------|
| INFO | TOFU | Blog, průvodce |
| COMM | MOFU | Porovnání, recenze |
| TRANS | BOFU | Produkt, kalkulačka |
| NAV | BRAND | Homepage, kontakt |

### Money keyword kritéria

Všechny tři podmínky musí platit:

1. `intent ∈ {TRANS, COMM}`
2. `volume >= money_threshold` (z params.yaml, default 20)
3. `brand_type != competitor`

### Doprovodné soubory

| Soubor | Účel |
|--------|------|
| `data/interim/categorization_issues.csv` | Flagged inkonzistence |
| `data/interim/categorization_test_N.csv` | Výsledky test kol |
| `data/interim/checkpoint_categorization.json` | Progress pro resume |

---

## Fáze 6 — keywords_clustered.csv (optional)

**Všechny sloupce z fáze 5** +

| Sloupec | Typ | Required | Poznámka |
|---------|-----|----------|----------|
| `cluster_id` | int | — | Jen money keywords |
| `cluster_name` | str | — | Highest volume KW v clusteru |

**Fallback:** pokud fáze 6 neběžela, použij `produkt` jako `cluster_name`.

---

## Enum hodnoty (STRICT)

Tyto hodnoty se nesmí odchýlit. Žádné `ano`/`yes`/`True` místo `ANO`. Konzistence je důležitější než přirozenost.

```
relevance:  ANO | NE | MOZNA
intent:     INFO | COMM | TRANS | NAV
funnel:     TOFU | MOFU | BOFU | BRAND
brand_type: own | competitor
priority:   money_keyword | <prazdne>
confidence: high | medium | low
```

## Konvence pro soubory

- **Kódování:** UTF-8 se signaturou BOM pro Excel kompatibilitu (CSV)
- **Separator:** čárka `,` (standardní)
- **Decimal:** tečka `.` (ne čárka)
- **Datum:** ISO 8601 `YYYY-MM-DD`
- **NULL:** prázdný string, **ne** `null`/`None`/`NaN`
- **List v jednom sloupci:** separator `|` (pipe), ne čárka (kolize s CSV)

## Primární vs sekundární output

- **Primární pro klienta:** XLSX multi-sheet (viz [ADR-003](decisions/003-xlsx-primary-output.md))
- **Sekundární pro pipeline:** CSV (vstup další fáze)
