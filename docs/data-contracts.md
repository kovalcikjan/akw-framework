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
   ↓
Fáze 6.5 → keywords_enriched.csv (pozice klienta + konkurence, KD, SERP features)
   ↓
Fáze 7  → 07_dashboard.xlsx (read-only — nepridava sloupce)
   ↓
Fáze 8  → keywords_with_gap.csv + 08_gap.xlsx (gap_type + action)
   ↓
Fáze 9  → keywords_scored.csv + 09_scoring.xlsx (priority_score + tier)
   ↓
Fáze 10 → keywords_mapped.csv + 10_content_mapping.xlsx (optional — URL plan)
   ↓
Fáze 11 → 11_FINAL_<client>_<date>.xlsx (klientsky deliverable)
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

## Fáze 6.5 — keywords_enriched.csv

SERP enrichment — pozice klienta + konkurence, KD, SERP features. Cesta: `data/interim/keywords_enriched.csv`.

**Všechny sloupce z fáze 6 (nebo 5 pokud fáze 6 neběžela)** +

| Sloupec | Typ | Required | Poznámka |
|---------|-----|----------|----------|
| `position_client` | float | — | 1.0-100.0, prázdné = nerankuje (> 100 nebo neexistuje) |
| `position_<competitor_domain>` | float | — | Jeden sloupec per tracked competitor z `enrichment.tracked_competitors` |
| `best_competitor_position` | float | — | Minimum ze všech competitor pozic |
| `best_competitor_domain` | str | — | Která doména je nejvýše |
| `kd` | int | — | 0-100 (pokud není z fáze 1, doplní se z Ahrefs/MM) |
| `serp_features` | str | — | Pipe-separated: `images\|video\|paa\|featured_snippet\|shopping\|local_pack` |
| `has_featured_snippet` | bool | — | True/False |
| `top_10_domains` | str | — | Pipe-separated, pořadí podle pozice 1-10 |

### Doprovodné soubory

| Soubor | Účel |
|--------|------|
| `checkpoint_enrichment.json` | Progress pro resume (API rate limits recovery) |

---

## Fáze 7 — 07_dashboard.xlsx (read-only)

Dashboard je **čtecí vrstva** — NEMĚNÍ main dataset, nepřidává sloupce. Výstup je jen XLSX s pivoty a grafy.

Cesta: `data/output/07_dashboard.xlsx`.

### XLSX listy

| List | Obsah |
|------|-------|
| `Overview` | Key metrics summary: count KW, total volume, P1 pending, intent split, % s pozicí klienta, median volume/CPC |
| `Dist_Intent_Funnel` | Pivot count × intent × funnel |
| `Dist_Produkt_Brand` | Pivot count × produkt × brand_type |
| `Dist_Priority` | Pivot count × priority (money_keyword / not) |
| `Top_Volume` | TOP 100 podle volume |
| `Top_CPC` | TOP 100 podle CPC |
| `Top_Value` | TOP 100 podle `volume × CPC` |
| `Top_Per_Produkt` | TOP 10 KW per produkt (long format) |
| `Ranking_Distribution` | Pivot ranking bucket × segment: `top_3` / `top_10` / `pos_11_20` / `pos_21_50` / `pos_51_100` / `nerankuje` |
| `Charts` | Nativní xlsxwriter grafy (histogram volume, pie intent, bar funnel, heatmap produkt × intent) |

### Enum: ranking buckets

```
top_3        — position_client in [1, 3]
top_10       — position_client in [4, 10]
pos_11_20    — position_client in [11, 20]
pos_21_50    — position_client in [21, 50]
pos_51_100   — position_client in [51, 100]
nerankuje    — position_client > 100 or prázdné
```

---

## Fáze 8 — keywords_with_gap.csv + 08_gap.xlsx

Competitive Gap — rule-based gap typology + recommended action + gap sizing.

- `data/interim/keywords_with_gap.csv` — dataset s přidanými sloupci
- `data/output/08_gap.xlsx` — klientský/interní XLSX se subsety

**Všechny sloupce z fáze 6.5** +

| Sloupec | Typ | Required | Poznámka |
|---------|-----|----------|----------|
| `gap_type` | str | ✓ | **defended** / **quick_win** / **close_gap** / **content_gap** / **no_opportunity** / **monitor** |
| `recommended_action` | str | ✓ | **optimize_existing** / **boost_authority** / **create_new_page** / **monitor** / **skip** |
| `gap_traffic_potential` | int | — | Odhad ztraceného trafficu (návštěv/měsíc), 0 pokud nelze spočítat |

### Enum: gap_type

```
defended        — position_client in top 3 (klient už rankuje dobře)
quick_win       — position_client in [4, 20] + best_competitor_position ≤ 3 + kd ≤ gap.quick_win_max_kd
close_gap       — position_client in [21, 50] + best_competitor_position ≤ 10
content_gap     — position_client nerankuje + best_competitor_position ≤ 10
no_opportunity  — nikdo nerankuje top 10 NEBO všichni top 3 s KD > 70
monitor         — default fallback
```

### Enum: recommended_action

```
optimize_existing  — máme URL, jen ji zlepšit (quick_win, close_gap)
boost_authority    — existing URL potřebuje backlinks (close_gap s vysokou KD)
create_new_page    — content_gap → nová stránka
monitor            — defended nebo nejasné → jen sledovat
skip               — no_opportunity → nestát se zabývat
```

### XLSX listy

| List | Filter |
|------|--------|
| `All_Gaps` | Master list se všemi KW |
| `Quick_Wins` | `gap_type = quick_win`, sortováno DESC podle `gap_traffic_potential` |
| `Close_Gaps` | `gap_type = close_gap` |
| `Content_Gaps` | `gap_type = content_gap` |
| `Defended` | `gap_type = defended` (monitoring) |
| `Gap_Summary` | Pivot `gap_type × produkt` (count + sum volume) |

---

## Fáze 9 — keywords_scored.csv + 09_scoring.xlsx

Scoring = jediný oficiální prioritizační mechanismus. Deterministický model, transparentní komponenty.

- `data/interim/keywords_scored.csv` — dataset se scoring sloupci
- `data/output/09_scoring.xlsx` — XLSX s rozkladem + P1 subset

**Všechny sloupce z fáze 8** +

| Sloupec | Typ | Required | Poznámka |
|---------|-----|----------|----------|
| `business_value` | float | ✓ | 0-10, z intent + money_keyword bonus |
| `ranking_probability` | float | ✓ | 0-10, z KD + position + gap_type modifier |
| `traffic_potential` | float | ✓ | 0-10, normalizováno min-max per dataset |
| `priority_score` | float | ✓ | Vážený součet: `0.40·BV + 0.35·RP + 0.25·TP` |
| `priority_tier` | str | ✓ | **P1** / **P2** / **P3** / **P4** |
| `scoring_reason` | str | ✓ | Human-readable breakdown: `"BV=9.0 (TRANS+money) \| RP=6.5 (KD=40, pos=15, quick_win) \| TP=4.2 = 6.94 (P2)"` |

### Enum: priority_tier

Prahy konfigurovatelné v `params.yaml: scoring.tier_thresholds`. Default:

```
P1  — priority_score ≥ 7.5    — immediate action
P2  — priority_score 5.0-7.5  — next quarter
P3  — priority_score 2.5-5.0  — nice to have
P4  — priority_score < 2.5    — ignore / monitor
```

### XLSX listy

| List | Obsah |
|------|-------|
| `Scored` | Full dataset, sortováno DESC podle `priority_score` |
| `Score_Breakdown` | Per-KW rozklad komponent (transparentnost) |
| `P1_Actionable` | Jen P1 subset — okamžitá akce |
| `Tier_Summary` | Pivot `priority_tier × produkt` (count + avg score) |
| `Methodology` | Vysvětlení vah, CTR estimates, gap modifiers (pro audit) |

### Validace flagy (v `scoring_issues.csv`)

- `P1_NO_OPPORTUNITY` — P1 s `gap_type = no_opportunity` (konflikt)
- `P4_MONEY_KEYWORD` — P4 s `priority = money_keyword` (review scoring)
- `MISSING_COMPONENT` — některá komponenta je null (data quality issue)

---

## Fáze 10 — keywords_mapped.csv + 10_content_mapping.xlsx (optional)

Content Mapping — KW → URL → content type. Volitelná fáze, `params.yaml: content_mapping.enabled` kontroluje zapnutí.

**Všechny sloupce z fáze 9** +

| Sloupec | Typ | Required | Poznámka |
|---------|-----|----------|----------|
| `target_url` | str | — | Cílová URL (existing URL pokud je, jinak slug návrh) |
| `url_status` | str | ✓ | **existing** / **new** / **merge** / **update** |
| `content_type` | str | ✓ | **product** / **category** / **comparison_lp** / **blog** / **faq** / **guide** / **comparison** / **landing** |
| `primary_cluster` | str | — | Název primárního clusteru (pro group) |
| `is_primary_kw` | bool | ✓ | True = primary KW v clusteru (highest priority_score), False = secondary |
| `secondary_keywords` | str | — | Pipe-separated seznam secondary KW v clusteru (jen u primary row) |

### Enum: url_status

```
existing  — klient má rankující URL (position_client v top 50)
new       — žádná URL neexistuje nebo > pozice 50
merge     — 2+ existujících URL pokrývá stejný cluster (konsolidovat)
update    — URL existuje v top 20, ale pokrývá jen část clusteru
```

### Enum: content_type

```
product       — TRANS + konkrétní produkt
category      — TRANS + kategorie produktů
comparison_lp — TRANS + porovnání (vyšší fáze funnelu)
blog          — INFO + dlouhá forma
faq           — INFO + krátká otázka/odpověď
guide         — COMM + průvodce rozhodnutím
comparison    — COMM + srovnání X vs Y
landing       — NAV + brand / homepage
```

### XLSX listy

| List | Filter |
|------|--------|
| `URL_Plan` | 1 řádek = 1 cílová URL (primary KW + secondary list + content_type) |
| `New_Pages` | `url_status = new`, sortováno DESC podle sum(priority_score) v clusteru |
| `Optimize_Existing` | `url_status = existing` |
| `Merge_Candidates` | `url_status = merge` |
| `Update_Existing` | `url_status = update` |

---

## Fáze 11 — 11_FINAL_<client>_<date>.xlsx

Finální klientský deliverable. NEGENERUJE CSV — jediný output je `data/output/11_FINAL_<client>_<date>.xlsx`.

Client name a datum se berou z `params.yaml: export.client_name` a aktuálního datumu.

### XLSX listy

| List | Obsah |
|------|-------|
| `01_Executive_Summary` | Top metriky, TOP 20 P1 KW, TOP 5 quick wins, TOP 5 content gaps, 3-5 key recommendations |
| `02_Action_Plan` | Serazeno podle priority × gap_type (P1+quick_win first) |
| `03_Full_Keyword_List` | Kompletní dataset se všemi klientskými sloupci (skryté audit/debug) |
| `04_Per_Segment_<seg>` | Pokud `export.per_segment_sheets: true` — 1 list per produkt/segment |
| `05_Quick_Wins` | Samostatný přehled (z fáze 8) |
| `06_Content_Gaps` | Samostatný přehled (z fáze 8) |
| `07_Content_Plan` | URL plan (pokud fáze 10 běžela) |
| `08_Methodology` | Transparentnost — scoring váhy, CTR estimates, počet zdrojů v seed, rule coverage (pokud `export.include_methodology_sheet: true`) |

### Skryté sloupce (audit trail)

V klientském deliverable se skryjí tyto sloupce (zůstávají v interních `keywords_scored.csv`):

```
keyword_normalized, keyword_no_diacritics, all_variants, variant_count,
relevance_source, relevance_confidence, review_flag,
categorization_source, categorization_confidence, categorization_reason, categorization_issue,
scoring_reason (volitelně ponechat v Action_Plan pro transparentnost)
```

### Optional Google Sheets sync

Pokud `export.google_sheets_export: true`:
- `python src/export.py --to-sheets <spreadsheet_id>` (on-demand, nikdy auto po běhu)
- Používá `google_sheets_helper.py` pattern z Delonghi/mBank
- Nenahrazuje XLSX — Sheets je sekundární prezentační vrstva

---

## Enum hodnoty (STRICT)

Tyto hodnoty se nesmí odchýlit. Žádné `ano`/`yes`/`True` místo `ANO`. Konzistence je důležitější než přirozenost.

```
# Fáze 4-5 (kategorizace)
relevance:          ANO | NE | MOZNA
intent:             INFO | COMM | TRANS | NAV
funnel:             TOFU | MOFU | BOFU | BRAND
brand_type:         own | competitor | retail
priority:           money_keyword | <prazdne>
confidence:         high | medium | low

# Fáze 7 (dashboard)
ranking_bucket:     top_3 | top_10 | pos_11_20 | pos_21_50 | pos_51_100 | nerankuje

# Fáze 8 (gap)
gap_type:           defended | quick_win | close_gap | content_gap | no_opportunity | monitor
recommended_action: optimize_existing | boost_authority | create_new_page | monitor | skip

# Fáze 9 (scoring)
priority_tier:      P1 | P2 | P3 | P4

# Fáze 10 (content mapping)
url_status:         existing | new | merge | update
content_type:       product | category | comparison_lp | blog | faq | guide | comparison | landing
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
- **Fáze 6.5 (enrichment):** CSV (pipeline output — data se nerenderují pro klienta)
- **Fáze 7 (dashboard):** XLSX (read-only, bez CSV, bez změny main datasetu)
- **Fáze 8 (gap):** CSV (pipeline) + XLSX (interní prezentace subsetů)
- **Fáze 9 (scoring):** CSV (pipeline) + XLSX (interní prezentace + methodology sheet)
- **Fáze 10 (content mapping):** CSV (pipeline) + XLSX (interní URL plan)
- **Fáze 11 (export):** jen XLSX (klientský deliverable — `11_FINAL_<client>_<date>.xlsx`)
- **Google Sheets sync:** on-demand přes `python src/export.py --to-sheets <id>` (nikdy auto)
