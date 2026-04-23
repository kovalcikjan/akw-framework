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

**Pořadí sloupců** (podle reálného výstupu `merge_sources.py`):

| # | Sloupec | Typ | Required | Poznámka |
|---|---------|-----|----------|----------|
| 1 | `keyword_normalized` | str | ✓ | lowercase, stripped |
| 2 | `keyword` | str | ✓ | Original, case-preserved |
| 3 | `volume` | int | — | 0 pokud neznámý |
| 4 | `source` | str | ✓ | `competitor_[domain]` / `gsc` / `client_seed` / `ahrefs` / `marketing_miner` / `reddit` / `paa` |
| 5 | `kd` | int | — | 0-100 |
| 6 | `position` | float | — | 1.0-100.0, prázdné pokud není |
| 7 | `url` | str | — | Ranking URL |

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

| List | Sloupce |
|------|---------|
| `Final Keywords` | `keyword, keyword_normalized, keyword_no_diacritics, source, volume, kd, position, url, all_variants, variant_count` (identické s keywords_clean.csv) |
| `All Keywords` | Stejné sloupce jako Final Keywords |
| `Merged Variants` | `keyword_normalized, keyword, volume, source, kd, position, url, removal_reason, merged_into, keyword_no_diacritics, _score` |
| `Variant Clusters` | `cluster_key, cluster_type, canonical, canonical_volume, variant_count, all_variants, total_volume` |
| `Summary` | `input_keywords, after_normalization, exact_duplicates_removed, diacritics_variants_merged, word_order_variants_merged, after_dedup, filtered_out, final_keywords, kept_percent, total_volume, volume_strategy, word_order_dedup_enabled` |

**Pozn.:** `_score` v Merged Variants je tuple canonical score (např. `"(True, 130, -19)"` = `(has_diacritics, volume, -length)`), viz [ADR-001](decisions/001-static-diacritics-map.md).

### Enum hodnoty

- `removal_reason`: `exact_dedup` / `diacritics_dedup` / `word_order_dedup`
- `filter_reason`: popisný výraz, např. `"volume < 10"`, `"length > 100"`, `"blacklist: bazar"`
- `cluster_type`: různé typy clusterů podle fáze dedup (diacritics / word-order / …)

---

## Fáze 4 — keywords_with_relevance.csv / keywords_relevant.csv

- `data/interim/keywords_with_relevance.csv` — **všechny** KW (ANO/NE/MOZNA)
- `data/interim/keywords_relevant.csv` — **jen ANO** (vstup pro fázi 5)

**Všechny sloupce z fáze 3** +

| Sloupec | Typ | Required | Poznámka |
|---------|-----|----------|----------|
| `relevance` | str | ✓ | **ANO** / **NE** / **MOZNA** |
| `relevance_reason` | str | ✓ | Max 15 slov |
| `relevance_source` | str | — | `rule` / `ai` / `ai_retry` / `manual` |
| `relevance_confidence` | str | — | `high` / `medium` / `low` |
| `review_flag` | str | — | Prázdné nebo `LOW_CONFIDENCE` / `RELEVANCE_LEAK_MOZNA` / `MOZNA_UNRESOLVED` |

### Doprovodné soubory

| Soubor | Účel |
|--------|------|
| `data/interim/relevance_review.csv` | Flagged pro human review (má `review_flag`) |
| `data/interim/relevance_leak_review.csv` | Post-hoc review (po kategorizaci se najde leak — MOZNA, které proklouzlo) |
| `data/interim/keywords_rule_only.csv` | Výstup `--rule-only` módu (jen rule-based, bez AI) |
| `data/interim/relevance_test_<N>.csv` | Výstup `--test N --test-round N` módu |
| `checkpoint_relevance.json` | Progress pro resume (v project root) |

---

## Fáze 5 — keywords_categorized.csv / money_keywords.csv

- `data/interim/keywords_categorized.csv` — jen **ANO** KW s kategoriemi (pro klienta)
- `data/interim/keywords_categorized_full.csv` — všechny KW včetně NE/MOZNA (audit trail)
- `data/interim/money_keywords.csv` — subset s `priority=money_keyword`

**Všechny sloupce z fáze 4 (pro `keywords_categorized.csv` jen ANO)** +

| Sloupec | Typ | Required | Poznámka |
|---------|-----|----------|----------|
| `typ` | str | — | Dle schema klienta v params.yaml |
| `produkt` | str | — | Dle schema klienta |
| `brand` | str | — | Název brandu |
| `brand_type` | str | — | `own` / `competitor` / `retail` (retail = prodejce/distribuční kanál, ne výrobce) |
| `specifikace` | str | — | Cílová skupina / varianta |
| `intent` | str | ✓ | **INFO** / **COMM** / **TRANS** / **NAV** |
| `funnel` | str | ✓ | **TOFU** / **MOFU** / **BOFU** / **BRAND** |
| `tema` | str | — | Tematická klasifikace (podle schema klienta, např. `legislativa_povoleni`) |
| `categorization_source` | str | — | `rule` / `ai` / `manual` |
| `categorization_confidence` | str | — | `high` / `medium` / `low` |
| `categorization_reason` | str | — | Vysvětlení AI |
| `priority` | str | — | `money_keyword` nebo prázdné |
| `categorization_issue` | str | — | Flag pro konzistenci (např. `"typ=brand but no brand detected"`) |

### Intent → Funnel mapping

| Intent | Funnel | Content type |
|--------|--------|--------------|
| INFO | TOFU | Blog, průvodce |
| COMM | MOFU | Porovnání, recenze |
| TRANS | BOFU | Produkt, kalkulačka |
| NAV | BRAND | Homepage, kontakt |

### Money keyword kritéria

Implementováno v `categorization.py::flag_money_keywords`. Všechny tři podmínky musí platit:

1. `intent ∈ {TRANS, COMM}`
2. `volume >= scoring.money_threshold` (z params.yaml, **default 20**)
3. `brand_type != "competitor"`

### Volitelné enrichment sloupce (project-specific)

V reálných projektech (např. llentab) jsou v `keywords_categorized.csv` přidané **další sloupce z externích nástrojů**, které framework negeneruje:

- **Marketing Miner data** — `Google Search Volume [MM]`, `Google CPC [CZK]`, `Google YoY Change [%]`, `Strongest Month`, měsíční data `January`-`December`
- **Sklik data** — `Sklik Search Volume`, `Sklik CPC [CZK]`, `Sklik Strongest Month`, měsíční data
- **SERP pozice** — `Google Position`, `Google Landing Page`, `Seznam Position`, per-competitor: `[domain] Google Position`, `[domain] Seznam Position`
- **Meta kategorie** — `Price`, `Color`, `Location`, `Questions`, `For who`, `Numbers`, `Brands`, `Materials`, `Properties`, `Seasons`, `Sports`
- **Competition** — `Google SERP Competition`, `Seznam SERP Competition class`

**Tyto sloupce přidává uživatel z Marketing Miner exportu, nejsou součástí frameworku.** V docs schema se neuvádějí povinně — jsou volitelné.

### Doprovodné soubory

| Soubor | Účel |
|--------|------|
| `data/interim/categorization_issues.csv` | Flagged inkonzistence (má `categorization_issue`) |
| `data/interim/classification_review_issues.csv` + `.json` | Strukturovaný review export |
| `data/interim/CLASSIFICATION_REVIEW_REPORT.md` | Human-readable report |
| `data/interim/keywords_rule_only.csv` | Výstup `--rule-only` módu (před AI) |
| `data/interim/categorization_test_<N>.csv` | Výstup `--test N --test-round N` módu |
| `checkpoint_categorization.json` | Progress pro resume (v project root) |

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
brand_type: own | competitor | retail
priority:   money_keyword | <prazdne>
confidence: high | medium | low
```

## Konvence pro soubory

- **Kódování:** UTF-8 se signaturou BOM (`utf-8-sig`) pro Excel kompatibilitu — ověřeno v `cleaning.py`, `relevance.py`, `categorization.py`
- **Separator:** čárka `,` (standardní)
- **Decimal:** tečka `.` (ne čárka)
- **Datum:** ISO 8601 `YYYY-MM-DD`
- **NULL:** prázdný string, **ne** `null`/`None`/`NaN`
- **List v jednom sloupci:** separator `|` (pipe), ne čárka (kolize s CSV) — např. `all_variants: "svářečka mig|svarecka mig"`

## Primární vs sekundární output

Viz [ADR-003](decisions/003-xlsx-primary-output.md) pro kompletní rozhodnutí.

- **Fáze 3 (cleaning):** XLSX multi-sheet (audit trail) + CSV (pro pipeline)
- **Fáze 4, 5, 6:** jen CSV (pipeline output)
- **Finální deliverable pro klienta:** Google Sheets (tvoří se mimo skripty fáze 3-6)
