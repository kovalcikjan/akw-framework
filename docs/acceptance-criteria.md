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
