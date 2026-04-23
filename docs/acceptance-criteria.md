# Acceptance Criteria

Kdy je která fáze **hotová a správně**. Každá klíčová metrika má 3 úrovně: 🎯 **Ideální**, ✓ **Akceptovatelné**, ⚠ **Signál** (vyžaduje rozhodnutí). Tento dokument je kontrolní seznam před pokračováním do další fáze.

## Princip

- **Tiered místo absolutních čísel.** Reálné projekty se liší (e-commerce vs. specializovaný obor) — pásma fungují lépe než jedna hranice.
- **⚠ Signál ≠ blocker.** Nutí tě se zastavit a rozhodnout (ignorovat / opravit / změnit scope).
- **Sample check = 20 KW ručně**, ne statistika. Statistika lže, KW pravdu řeknou.
- **Edge case poznámka:** Referenční projekt `llentab` (architektonická terminologie, 99 % Marketing Miner, 9.8 % rule coverage, AI v fázi 4 neběžela) úspěšně doběhl — prahy jsou nastavené tak, aby hard-domain projekty neshodily celou pipeline.

---

## Fáze 1 — Seed Keywords + Expansion

### Klíčové metriky

| Metrika | 🎯 Ideální | ✓ Akceptovatelné | ⚠ Signál |
|---------|------------|------------------|-----------|
| Počet zdrojů | 3+ různé (GSC, Ahrefs, konkurenti, MM) | 2 zdroje | 1 dominantní zdroj >95 % |
| Volume pokrytí | >0 u 80 %+ KW | 50-80 % | <50 % — MM expansion pravděpodobně neproběhla |
| Diverzita KW | žádný zdroj nemá >70 % | dominantní max 90 % | monokultura — 99 % z jednoho zdroje |

### Done checklist

- [ ] Všechny plánované zdroje nahrané do `data/raw/`
- [ ] `keywords_raw.csv` má sloupec `source` s jasným označením původu
- [ ] Žádné KW zjevně mimo obor (u sample 20)

### Sample check

Náhodných 20 KW → *"dává smysl, že je tu?"* Shoda < 15/20 → vrátit se k seed sběru.

---

## Fáze 3 — Cleaning + Dedup

### Klíčové metriky

| Metrika | 🎯 Ideální | ✓ Akceptovatelné | ⚠ Signál |
|---------|------------|------------------|-----------|
| Dedup ratio | 10-20 % | 5-30 % | <5 % (normalizace nefunguje) nebo >50 % (word_order moc agresivní) |
| Filter ratio | 5-20 % | do 35 % | >50 % — blacklist pravděpodobně odstřelil head terms |
| Canonical selection | 100 % preferuje diakritiku | OK | ASCII vybráno při existující diakritické variantě = bug |

### Done checklist

- [ ] `keywords_clean.xlsx` má všech 5 listů (viz [data-contracts](data-contracts.md))
- [ ] `Variant Clusters` sheet obsahuje aspoň 5 clusterů s 2+ variantami
- [ ] `keywords_filtered_out.csv` má `filter_reason` u každého záznamu
- [ ] `keywords_removed.csv` má `removal_reason` (exact/diacritics/word_order)

### Sample check

Z `Variant Clusters` sheetu náhodných 10 clusterů → *"dává smysl, že se sloučily?"* + *"je vybraná správná canonical?"*

---

## Fáze 4 — Relevance

### Klíčové metriky

| Metrika | 🎯 Ideální | ✓ Akceptovatelné | ⚠ Signál |
|---------|------------|------------------|-----------|
| Rule coverage (ANO+NE z rule) | 40-60 % | 15-40 % | <10 % — params.yaml je prázdné, AI dělá všechno |
| ANO ratio (z celku) | 50-75 % | 25-85 % | <20 % (příliš striktní) nebo >95 % (AI schvaluje vše) |
| MOZNA po AI | <15 % | do 30 % | >50 % — prompt nedává dost kontextu, nebo model je slabý |
| High-vol MOZNA (vol>500) | 0 | do 5 KW | 20+ — high-volume KW bez rozhodnutí = slepé místo |

### Done checklist

- [ ] Každý řádek má `relevance_reason` (max 15 slov)
- [ ] `relevance_source` = `rule` / `ai` / `ai_retry` / `manual` (nikdy prázdné)
- [ ] `relevance_review.csv` ručně projitý
- [ ] `MOZNA` zbytky rozhodnuté ručně nebo akceptované jako `MOZNA_UNRESOLVED`

### Red flags (mimo metriky)

- **ANO + competitor brand** bez product termu → zkontrolovat (často leak)
- **NE s volume > 1000** → možná legit, projít ručně
- **Krátký reason (<3 slova) u AI** → prompt nedává kontext

### Sample check

20 KW z každé kategorie (ANO/NE/MOZNA) → ruční verdikt vs. model verdikt. Shoda < 85 % = ladit prompt/pravidla.

---

## Fáze 5 — Kategorizace

### Klíčové metriky

| Metrika | 🎯 Ideální | ✓ Akceptovatelné | ⚠ Signál |
|---------|------------|------------------|-----------|
| Rule coverage (po EDA rozšíření) | 60-80 % | 30-60 % | <20 % — params.yaml product patterns chybí |
| Intent pokrytí | všechny 4 (INFO/COMM/TRANS/NAV) zastoupeny | 3 intenty | 1 intent >85 % — schema je neúplné |
| Money keywords z relevantních | 10-25 % | 5-40 % | <2 % (threshold moc vysoký) nebo >50 % (moc nízký) |
| Produkt prázdný | <15 % | do 30 % | >50 % — produkt patterns nedostatečné |
| `categorization_issues.csv` | 0 nevyřešených | do 5 % akceptovaných | >15 % nevyřešených |

### Done checklist

- [ ] Few-shot examples: 15-20 high-confidence case z rule-based
- [ ] `intent` a `funnel` u každého řádku (povinné)
- [ ] `intent × funnel` respektuje mapping ([data-contracts](data-contracts.md))
- [ ] `categorization_issues.csv` projitý

### Red flags (mimo metriky)

- **TRANS + dotazové slovo** (jak, co) → intent/typ mismatch
- **Brand keyword bez detected brand** → post-processing selhal
- **`typ=brand` ale žádný brand v KW** → flag v `categorization_issue`

### Sample check

20 money keywords → *"opravdu je to TRANS/COMM a dává smysl pro business?"* Shoda < 16/20 → projít kritéria.

---

## Fáze 6 — SERP Clustering (optional)

### Klíčové metriky

| Metrika | 🎯 Ideální | ✓ Akceptovatelné | ⚠ Signál |
|---------|------------|------------------|-----------|
| Počet clusterů | 15-40 | 10-50 | <5 (threshold moc volný) nebo >60 (moc přísný) |
| KW per cluster | 2-10 | 2-20 | 80 %+ single-KW → clustering nepomohl |
| Největší cluster | do 15 KW | do 25 | >30 — threshold moc volný |

### Done checklist

- [ ] `cluster_name` = highest volume KW v clusteru (konzistentně)
- [ ] Top 10 clusterů ručně projité
- [ ] Fallback: pokud fáze 6 neběží, `cluster_name = produkt`

### Sample check

5 největších clusterů → *"tyto KW patří opravdu na jednu stránku?"*

---

## Fáze 6.5 — SERP Enrichment

### Klíčové metriky

| Metrika | 🎯 Ideální | ✓ Akceptovatelné | ⚠ Signál |
|---------|------------|------------------|-----------|
| KW s `position_client` | 30-70 % | 10-80 % | <5 % (klient je nový/malý) nebo >90 % (možná chybí long-tail) |
| KW s `kd` | 80 %+ | 50-80 % | <30 % — enrichment source nefunguje |
| KW s `best_competitor_position` | 70 %+ | 40-70 % | <20 % — `tracked_competitors` nepokrývá trh |
| SERP features pokrytí | u relevantních 60 %+ má features | 30-60 % | <10 % — feature extraction nefunguje |

### Done checklist

- [ ] `position_client` má sloupec (i když prázdný) u každého KW
- [ ] `tracked_competitors` z params.yaml = sloupce `position_<domain>` existují
- [ ] `best_competitor_position` a `best_competitor_domain` konzistentně vypočítány
- [ ] `checkpoint_enrichment.json` dokončen (žádné incomplete KW)

### Red flags

- **Median `position_client` < 5** ale klient je nový → data jsou špatná, ověř domain v params.yaml
- **`has_featured_snippet` = True u > 30 % KW** → SERP parsing overcounts, ověř
- **Všechny `position_<competitor>` prázdné** → competitor domains chybně definované

### Sample check

20 KW s `position_client` → ručně ověř v Google (discrepancy < 10 % je OK)

---

## Fáze 7 — Dashboard

### Klíčové metriky

Dashboard nemá "quality" metriky — je to deskriptivní vrstva. Kritéria jsou **completeness**:

| Položka | 🎯 Ideální | ✓ Akceptovatelné | ⚠ Signál |
|---------|------------|------------------|-----------|
| Listy v XLSX | Všech 10 (viz data-contracts) | Min. `Overview`, `Top_Volume`, `Ranking_Distribution` | Chybí `Overview` nebo `Ranking_Distribution` |
| Grafy | 4-5 embedded nativních grafů | 2-3 grafy | Žádné grafy — XLSX je jen tabulky |
| Overview metriky | 8-10 klíčových čísel | 5-7 | <3 — sheet je prázdný |

### Done checklist

- [ ] `07_dashboard.xlsx` existuje a otevře se v Excelu/LibreOffice bez chyb
- [ ] `Overview` sheet má všechny klíčové čísla (count KW, median volume, intent split, % s pozicí klienta)
- [ ] `Ranking_Distribution` pokrývá všechny 6 ranking buckets
- [ ] `Charts` sheet obsahuje embedded grafy (ne jen tabulky)
- [ ] **Žádné** scoring sloupce nebyly přidány do main datasetu

### Red flags

- **Dashboard obsahuje `priority_score` sloupec** → porušení separace, score patří do fáze 9
- **Top listy jsou identické** (Top_Volume = Top_Value) → CPC data chybí nebo sort nefunguje
- **`Ranking_Distribution` má všechny KW v `nerankuje`** → SERP enrichment neběžel nebo selhal

### Sample check

Otevři XLSX, podívej se na `Overview` → *"odpovídají čísla tomu, co víme o klientovi?"* Pokud `total_volume = 0` nebo `intent_split` neobsahuje TRANS, něco je špatně.

---

## Fáze 8 — Competitive Gap

### Klíčové metriky

| Metrika | 🎯 Ideální | ✓ Akceptovatelné | ⚠ Signál |
|---------|------------|------------------|-----------|
| Quick wins count | 10-15 % datasetu | 5-25 % | <2 % (nedostatek dat) nebo >40 % (threshold moc široký) |
| Content gaps count | 20-40 % (klient je nový) | 10-50 % | >70 % — klient má obrovský obsahový deficit nebo SERP data neúplná |
| Defended count | 5-20 % (klient rankuje) | 2-30 % | <1 % — klient nerankuje nikde |
| `gap_type = monitor` fallback | <20 % | do 35 % | >50 % — rules nepokrývají většinu případů |

### Done checklist

- [ ] Každý řádek má `gap_type` (nikdy prázdné)
- [ ] Každý řádek má `recommended_action`
- [ ] `gap_traffic_potential` spočítán u quick_win / close_gap / content_gap
- [ ] `08_gap.xlsx` má všech 6 listů (All_Gaps, Quick_Wins, Close_Gaps, Content_Gaps, Defended, Gap_Summary)

### Red flags

- **Quick win s KD > `gap.quick_win_max_kd`** → threshold violation, review pravidla
- **Content gap s volume < 100** → marginální, zvaž prioritizaci
- **`best_competitor_position` chybí ale `gap_type != monitor`** → chybějící SERP data

### Sample check

10 quick wins → *"dává smysl, že je to 'blízko'? Má klient reálnou šanci optimalizovat?"* Shoda < 7/10 = ladit thresholds.

---

## Fáze 9 — Scoring

### Klíčové metriky

| Metrika | 🎯 Ideální | ✓ Akceptovatelné | ⚠ Signál |
|---------|------------|------------------|-----------|
| P1 count z datasetu | 5-15 % | 2-25 % | <1 % (prahy moc vysoké) nebo >40 % (moc nízké) |
| P1+P2 count | 20-40 % | 10-60 % | >80 % — "actionable" je všechno, prahy nefungují |
| P4 count | 30-60 % | 20-75 % | <10 % (archive je malý) nebo >80 % (většina je ignore) |
| Score rozdělení | Bimodální (hodně P1/P2 nebo P4) | Unimodální | Všechny KW v P2/P3 — model neodlišuje |
| `scoring_reason` non-empty | 100 % | 100 % | Chybí u některých KW — data quality issue |

### Done checklist

- [ ] Každý řádek má `priority_score`, `priority_tier`, `scoring_reason`
- [ ] `scoring_reason` je human-readable (obsahuje BV, RP, TP komponenty)
- [ ] `Methodology` sheet v XLSX vysvětluje váhy + CTR estimates + gap modifiers
- [ ] `scoring_issues.csv` ručně projitý (P1_NO_OPPORTUNITY, P4_MONEY_KEYWORD)

### Red flags

- **P1 s `gap_type = no_opportunity`** → konflikt, zkontroluj business_value (možná přestřeleno money_keyword bonusem)
- **P4 s `priority = money_keyword`** → scoring drtí money KW, review parametry
- **Median `ranking_probability` > 8** → model je moc optimistický, zkontroluj KD
- **Všechny KW mají `priority_tier = P3`** → rozptyl priority_score je příliš nízký (normalizace selhala)

### Sample check

20 P1 KW ručně → *"opravdu bych toto řešil jako první?"* Shoda < 15/20 = ladit váhy v `params.yaml: scoring.weights` nebo thresholds.

---

## Fáze 10 — Content Mapping (optional)

### Klíčové metriky

| Metrika | 🎯 Ideální | ✓ Akceptovatelné | ⚠ Signál |
|---------|------------|------------------|-----------|
| URL per cluster | 1 (1 URL = 1 cluster) | 1-2 | 3+ per cluster — clustering selhalo |
| New pages z P1+P2 | 20-40 % | 10-60 % | >70 % — klient má obrovský deficit nebo URL detection selhala |
| Merge candidates | 2-10 | 0-15 | >20 — klient má výrazný content duplicate problem |
| Pokrytí `content_type` | všech 8 typů zastoupeno (ideál) | 5-6 typů | 1-2 typy — schema je neúplné |

### Done checklist

- [ ] Každý řádek má `target_url`, `url_status`, `content_type`
- [ ] `is_primary_kw` konzistentně vyplněno (1 True per cluster)
- [ ] `secondary_keywords` jen u primary řádků
- [ ] `10_content_mapping.xlsx` má všech 5 listů

### Red flags

- **`content_type = product` ale `intent = INFO`** → intent/content_type mismatch
- **`url_status = merge` u 1-KW clusteru** → merge nedává smysl, review
- **`target_url` duplicitní napříč clusters** → URL conflict, potenciální kanibalizace

### Sample check

10 new pages → *"má smysl vytvořit tuto URL? Je content_type správný?"* Shoda < 7/10 = ladit `content_types` v params.yaml nebo intent klasifikaci (fáze 5).

---

## Fáze 11 — Export & Deliverables

### Klíčové metriky

Export nemá quality metriky — je to finální kompilace. Kritéria jsou **ostrost klientského dokumentu**:

| Položka | 🎯 Ideální | ✓ Akceptovatelné | ⚠ Signál |
|---------|------------|------------------|-----------|
| Executive summary položky | Všech 5 sekcí (top metriky, P1, quick wins, content gaps, recommendations) | 3-4 sekce | <3 — summary je prázdný |
| Per-segment sheety | Jeden list per produkt (pokud > 1 produkt) | Agregované | Per-segment zapnuto ale jen 1 list |
| Rendering check | Otevře se v Excelu i Google Sheets bez chyb | Excel only | Chyby při otevření (encoding, formulace) |

### Done checklist

- [ ] `11_FINAL_<client>_<date>.xlsx` existuje v `data/output/`
- [ ] Executive summary obsahuje konkrétní čísla (ne placeholders)
- [ ] Action plan je seřazený podle priority × gap_type
- [ ] Per-segment sheety jsou kompletní
- [ ] **Žádné** `NaN`, `None`, `null` values v klientských sheetech
- [ ] Audit trail sloupce skryté (nebo odstraněné)
- [ ] Pokud `google_sheets_export: true` — sync proběhl a klient má link

### Red flags

- **Executive summary obsahuje `TODO` nebo `<placeholder>`** → AI generation selhala
- **P1 KW v Action Plan = 0** → nic "akce jako první" = buď chyba scoringu nebo nesprávný dataset
- **Encoding problems** (`å`, `ł` místo `á`, `ý`) → UTF-8 BOM nedodržen

### Sample check (POVINNÝ před předáním)

Otevři finální XLSX a zkontroluj:
1. `01_Executive_Summary` — přečti jako klient, dává smysl?
2. `02_Action_Plan` prvních 20 řádků — opravdu bych toto řešil první?
3. `03_Full_Keyword_List` — náhodných 20 řádků, správné hodnoty?
4. `04_Per_Segment_<seg>` pro každý segment — kompletní?
5. `08_Methodology` (pokud zapnuto) — transparentní pro klienta?

Pokud cokoliv z výše = NE → vrátit se k fázi 11 (nebo výše, pokud je problém v datech).

---

## Obecná pravidla napříč fázemi

### Před každým full AI run (fáze 4, 5)

- [ ] `--test 20` (fáze 5) nebo `--test 50` (fáze 4) proběhl
- [ ] Výsledky testu **ručně zkontrolované** (ne jen metriky)
- [ ] Params.yaml upravený podle zjištění
- [ ] Odhad nákladů (batch × cena modelu × počet KW)

### Před předáním klientovi

- [ ] Žádná metrika v ⚠ signálu není ignorovaná bez rozhodnutí
- [ ] Finální Excel ručně projitý — otevři, pročti 30 KW z každé kategorie
- [ ] Executive summary obsahuje čísla ze `Summary` sheetu (cleaning) + `categorization_issues` count

### Kdy zastavit a vrátit se

- **Fáze 3 má ⚠ u 2+ metrik** → oprav, neposouvat se dál s nekvalitními daty
- **Fáze 4 ANO < 20 %** → špatná relevance pravidla nebo špatný seed
- **Fáze 5 sample check < 16/20** → prompt / few-shot ladit, ne pokračovat

---

## Jak číst tiered hodnoty

- **🎯 Ideální** = cíl pro standardní e-commerce projekt s jasně definovanými produkty.
- **✓ Akceptovatelné** = pásmo, které je OK i pro specializované / těžší domény.
- **⚠ Signál** = zastav se. Neznamená to, že je projekt špatný, ale že **někde je třeba rozhodnutí** (opravit konfiguraci, akceptovat limitaci dat, nebo změnit scope).

Pokud projekt **opakovaně** padá do ⚠ ve více fázích, framework pravděpodobně není ideální fit — zvaž manuální klasifikaci nebo jiný přístup.
