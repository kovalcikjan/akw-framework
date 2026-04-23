---
name: akw
description: AKW - Analyza klicovych slov. Framework pro keyword research projekty. Faze 0-10 od sběru dat po deliverables.
---

# AKW - Analyza klicovych slov

## Kontext

Framework pro analyzu klicovych slov. Pouziva se opakovane pro klienty (e-shopy, sluzby, weby).
Vytvoren na zaklade 6 realnych projektu (Delonghi, mBank, CPP, eVisions, svarecky, Delonghi mixery).

**Framework dokumentace:** `/Users/admin/Documents/Akws/Akw_framework/`
**Known issues:** `/Users/admin/Documents/Akws/Akw_framework/ISSUES.md`
**Referencni projekty:** `/Users/admin/Documents/Akws/`

---

## Jak pouzivat

### Novy projekt (params.yaml neexistuje)

1. **Uzivatel zada brief** - v chatu odpovi na otazky (viz Faze 0)
2. **AI zapise** `docs/analysis_brief.md`
3. **AI vygeneruje deep research prompt** → uzivatel spusti v Claude Desktop
4. **Uzivatel vlozi vysledek** → AI vytvori `docs/business_research.md`
5. **AI vygeneruje `params.yaml`** z obou dokumentu (uzivatel jen zkontroluje)
6. **AI vytvori projekt** (adresar, CLAUDE.md, data/)
7. Pokracuje Fazi 1

### Rozpracovany projekt (params.yaml existuje)

Precti CLAUDE.md a params.yaml → zjisti kde se skoncilo → pokracuj od dalsi faze.

---

## Prehled fazi

```
FAZE 0: Project Setup ............ brief → research → params.yaml
FAZE 1: Seed Keywords + Expansion  seed sber + namnozeni (Marketing Miner)
FAZE 2: EDA (optional) .......... distribuce, outliers, n-gramy (notebook)
FAZE 3: Cleaning + Dedup ★ ...... normalizace, dedup, filtering
FAZE 4: Relevance ★ ............. ANO/NE/MOZNA + duvod
FAZE 5: Kategorizace ★ .......... typ, produkt, intent, funnel
FAZE 6: SERP Clustering (opt) ... Marketing Miner SERP data
FAZE 7: Dashboard ............... grafy, kontingencni tabulky
FAZE 8: Competitive Gap ......... quick wins, content gaps
FAZE 9: Scoring ................. prioritizace P1-P4
FAZE 10: Content Mapping ........ KW → URL → content type
FAZE 11: Validation + Export ..... QA, Excel deliverable
```

---

## Faze 0: Project Setup

### Cil
Pochopit byznys klienta, definovat cile analyzy, vytvorit projekt.

### Kroky

Vsechno se drzi v chatu az do posledniho kroku. Projekt se vytvori az kdyz je vse potvrzene.

**0.1 Uzivatel zada brief (v chatu)**

AI se pta:
- Pro koho? (klient, domena)
- Jaky SEO cil? (optimalizace kategorii, novy obsah/blog, prestavba URL struktury, competitive gain...)
- Jaky scope? (jake produkty/sluzby, co je IN/OUT)
- Specificke pozadavky? (jen CZ/SK, inventory only, agilni vs kompletni...)
- Inside info od klienta? (plany, priority, omezeni)

CHECKPOINT: AI shrnuje brief → "Sedi to? Chces neco upravit?"
NIKDY nepokracuj dal dokud uzivatel neodpovi na vsechny otazky a nepotvrdí brief.

**0.2 AI vygeneruje deep research prompt a UKAZE ho uzivateli**

AI musi vytvorit KONKRETNI prompt (hotovy text, copy-paste ready) na zaklade briefu.
Prompt musi obsahovat:
- Kontext z briefu (klient, domena, cil, scope)
- Co prozkoumat: web klienta, produkty, kategorie, znacky, ceny, strukturu webu
- Co prozkoumat: konkurenci, trh, cilovou skupinu
- Pozadavek na strukturovany vystup (fakta, ne doporuceni)

AI MUSI tento prompt vypsat do chatu jako hotovy text ktery uzivatel zkopiruje.

CHECKPOINT: "Zkopiruj tento prompt do Claude Desktop (s webovym vyhledavanim) a vysledek mi posli sem"
(ceka na uzivateluv vstup - NEDELA nic dal dokud uzivatel nevlozi vysledek)

**0.3 Uzivatel vlozi deep research vysledek**

AI si ho zapamatuje (zatim NEPISE zadne soubory).

**0.4 AI vygeneruje params.yaml a UKAZE ho v chatu**

Z briefu + research automaticky vygeneruje:
- client info (name, domain, language, country)
- relevance kriteria (products, excluded, competitors)
- categorization schema (typ, produkt, brand, specifikace)
- cleaning config (word_order_dedup, volume_strategy, filters)

AI UKAZE params.yaml v chatu (zatim NEPISE soubor).

CHECKPOINT: "Zkontroluj - sedi produkty, konkurenti, excluded?"
(ceka na OK nebo upravy)

**0.5 AI vytvori cely projekt naraz**

Az po potvrzeni params.yaml. Zepta se na cestu (default: ~/Documents/Akws/[nazev]/).
Vytvori:
- adresar + data/raw/, data/interim/, data/output/, docs/, src/
- docs/analysis_brief.md (z briefu)
- docs/business_research.md (z research vystupu)
- params.yaml (potvrzeny)
- CLAUDE.md s kontextem projektu + checklist fazi

CHECKPOINT: "Faze 0 hotova. Projekt vytvoren v [cesta]. Pokracujeme Fazi 1?"

### Projekt struktura

```
projekt_nazev/
├── CLAUDE.md
├── params.yaml
├── docs/
│   ├── analysis_brief.md
│   └── business_research.md
├── data/
│   ├── raw/               # READONLY - vstupni data
│   ├── interim/           # Mezivysledky
│   └── output/            # Finalni deliverables
└── src/                   # Python kod (az kdyz je potreba)
```

### params.yaml schema

```yaml
client:
  name: ""
  domain: ""
  language: "cs"
  country: "CZ"

cleaning:
  word_order_dedup: false
  volume_strategy: "sum_volumes"

filters:
  min_search_volume: 10
  min_length: 3
  max_length: 100
  blacklist: []

relevance:
  client_description: ""
  products: []
  target_groups: []
  excluded: []
  competitors: []

categorization:
  typ: []
  produkt: {}
  brand:
    own: []
    competitor: []
  specifikace: []

ai:
  default_model: "gpt-4o-mini"        # or gpt-4o, claude-3-haiku
  batch_size: 30                       # keywords per API call (30-50)
  temperature: 0.1                     # low = deterministic
  test_sample_size: 50                 # for --test mode
  few_shot_count: 20                   # examples in categorization prompt

scoring:
  weights:
    business_value: 0.40
    ranking_probability: 0.35
    traffic_potential: 0.25
  intent_scores:
    TRANS: 10
    COMM: 7
    INFO: 3
    NAV: 1

paths:
  raw_data: "data/raw"
  interim: "data/interim"
  output: "data/output"
```

---

## Faze 1: Seed Keywords + Expansion

### Cil
Sebrat co nejsirsi zaklad keywords ze vsech relevantnich zdroju.

### Kroky

**1A: Seed sber (ciste clovek)**

Specialista sebere seed keywords mimo tento projekt (Ahrefs, GSC, product feed, vlastni analyza...).
Nahraje vysledek do data/raw/.
AI do toho nevstupuje.

**1B: Namnozeni + hledanosti (ciste clovek)**

Specialista vezme seedy → Marketing Miner (suggestions, related, questions + doplneni hledanosti).
Nahraje vysledek do data/raw/.
AI do toho nevstupuje.

CHECKPOINT: "Nahraj vsechny soubory do data/raw/ a dej vedet"
(ceka na upload - v data/raw/ muze byt vic souboru z ruznych zdroju)

**1C: Slouceni + initial dedup (AI)**

AI slouci VSECHNY soubory z data/raw/, initial dedup (exact + lowercase).

CHECKPOINT: "X keywords z Y souboru. Rozlozeni: [tabulka]. Pokracujeme?"
→ data/interim/keywords_raw.csv

### Output schema (data/interim/keywords_raw.csv)

| Sloupec | Typ | Required | Poznamka |
|---------|-----|----------|---------|
| keyword | str | YES | Original, case-preserved |
| keyword_normalized | str | YES | lowercase, stripped |
| source | str | YES | competitor_[domain], gsc, client_seed, ahrefs, marketing_miner, reddit, paa |
| volume | int | NO | 0 pokud neznamy |
| kd | int | NO | 0-100 |
| position | float | NO | 1.0-100.0 |
| url | str | NO | Ranking URL |

---

## Faze 2: EDA (optional)

> Tato faze je volitelna. Zeptej se: "Chces udelat EDA (prohlednout data v notebooku), nebo rovnou pokracovat cistenim?"

### Cil
Poznat co je v datech - jake patterns, co chybi, co je navic.
Vystupy primo ovlivnuji Fazi 3 (co vycistit) a Fazi 4-5 (jak klasifikovat).

### Jak — KONVERZACNI PRUCHOD

EDA je **konverzace, ne jen notebook**. AI vygeneruje notebook, uzivatel ho spusti,
a pak AI provazi uzivatele vysledky po jednotlivych bunkach — vysvetluje, upozornuje na zajimavosti,
navrhuji akce.

**Setup Jupyter notebooku:**

```bash
# 1. Aktivuj venv projektu (pokud jeste neni)
cd ~/Documents/Akws/[projekt]/
python -m venv .venv
source .venv/bin/activate

# 2. Nainstaluj zavislosti (jednorazove)
pip install jupyter pandas matplotlib openpyxl pyyaml

# 3. Registruj kernel pro tento projekt (jednorazove)
pip install ipykernel
python -m ipykernel install --user --name=[projekt]_kernel --display-name="[Projekt] Python"

# 4. AI vygeneruje notebook
python src/eda_notebook_generator.py

# 5. Spust notebook
jupyter notebook notebooks/01_eda.ipynb
# Vyber kernel: [Projekt] Python
```

Alternativa bez Jupyter (pokud uzivatel nechce notebook):
```bash
# Spust jako Python script — vypise vysledky do terminalu
python src/eda_notebook_generator.py --run-as-script
```

### Prubeh konverzace

AI vygeneruje notebook. Uzivatel spusti vsechny bunky (nebo Run All).
Potom AI provadi uzivatele vysledky — sekci po sekci:

**2.1 Zakladni prehled dat**

AI rekne:
- "Mas X keywords z Y zdroju. Rozlozeni: [tabulka]."
- "Volume distribuce: median je Z, to je [normalni/nizke/vysoke] pro tento typ projektu."
- "X% keywords nema volume — to je [ok/hodne], znamena to [vysvetleni]."
- Upozorni na zajimavosti (napr. "90% dat pochazi z jednoho zdroje — mozna doplnit")

CHECKPOINT: "Vidis neco neocekavaneho? Pokracujeme kvalitou dat?"

**2.2 Kvalita dat**

AI rekne:
- "Nasli jsme X duplicit (Y%). Priklady: [top 5 skupin]."
- "Preview pro fazi 3: diakritika slouci ~Z variant (napr. 'svarecka' + 'svářečka')."
- "Head terms (top 5 volume): [seznam]. Tyto budou mit velky vliv na analyzu."
- "Outliers: [pripad/zadne]. Doporuceni: [akce]."

CHECKPOINT: "Neco podezreleho? Pokracujeme n-gramy?"

**2.3 N-gram analyza**

AI rekne:
- "Uni-gramy — nejcastejsi slova v datasetu: [top 10 s komentarem]."
  - Upozorni co je ocekavane ("'svarecka' na 1. miste, sedi")
  - Upozorni co je prekvapive ("'kurz' se objevuje 45x — to je nerelevantni, dat do blacklistu?")
  - Upozorni co chybi ("V params.yaml mas produkt 'TIG' ale v datech se nevyskytuje — chybi data?")
- "Bi-gramy — nejcastejsi dvojice: [top 10]."
  - Produktove patterny: "svarecka mig (120x), elektroda bazicka (45x)"
  - Intent patterny: "jak svarovat (30x) = INFO, cena svarecka (25x) = TRANS"
- "Tri-gramy: [top 5] — tyto pomuzou definovat kategorii v fazi 5."

CHECKPOINT: "Vidis neco co chybi? Navrhuji tyto akce pred fazi 3: [seznam]. Sedi?"

**2.4 Doporuceni a akce**

AI na zaklade vsech predchozich sekci navrhne KONKRETNI akce:
- "Navrhuji pridat do params.yaml blacklist: ['kurz', 'skoleni', 'prace'] — souhlasis?"
- "Navrhuji pridat do excluded: ['bazar', 'wiki'] — souhlasis?"
- "Produkt 'TIG' z params.yaml ma jen 5 keywords — zvaz doplnit seedy"
- "N-gram 'svarecka mig' (120x) navrhuji jako produkt pattern pro fazi 5"

Pokud uzivatel souhlasi → AI ROVNOU updatne params.yaml.

CHECKPOINT: "EDA hotova. Params.yaml aktualizovany. Pokracujeme fazi 3 (cleaning)?"

### Co notebook MUSI obsahovat (technicke sekce)

**Sekce 1: Zakladni prehled**
- Pocet keywords, zdroju, unikatnich
- Volume distribuce (histogram + buckety)
- Source breakdown tabulka

**Sekce 2: Kvalita dat**
- Duplicity preview (exact, diacritics, word-order)
- Outliers (top 20 volume, podezrele nizke)
- KD distribuce (pokud dostupne)
- Source overlap (kolik KW z 2+ zdroju)

**Sekce 3: N-gram analyza**
- Uni-gramy top 30 (s vizualizaci)
- Bi-gramy top 20 (s vizualizaci)
- Tri-gramy top 15
- Pokryti produktu z params.yaml
- Pokryti competitors z params.yaml

**Sekce 4: Doporuceni**
- Navrh blacklist slov pro fazi 3
- Navrh excluded patterns pro fazi 4
- Navrh intent/produkt patterns pro fazi 5
- Chybejici temata (zpetna vazba do faze 1)

### Output
- `notebooks/01_eda.ipynb` (vizualizace, tabulky)
- Data se NEMENI — jen analyza
- params.yaml se UPDATNE pokud uzivatel souhlasi s navrhy

---

## Faze 3: Cleaning + Dedup

### Cil
Vytvorit cisty, deduplikovany dataset. Stezejni faze - kvalita vystupu zavisi na cistote dat.

### Jak
Python skript `src/cleaning.py`. AI vytvori a spusti.
Reference: mBank `keyword_cleaner.py` (470 radku), CPP session log (480 duplicit).

### Priklad workflow

```
INPUT: keywords_raw.csv (2500 keywords)

KROK 3.1: Text normalizace
  "Svarecka MIG 200A"     → "svarecka mig 200a"
  "svarecka  mig  200a"   → "svarecka mig 200a"

KROK 3.2: Exact dedup
  "svarecka mig 200a" (vol: 300) ← keep
  "svarecka mig 200a" (vol: 150) ← drop, volume se secte (450)
  2500 → 2100 (-16%)

KROK 3.3: Diacritics dedup
  "svarecka mig" (vol: 500) + "svářečka mig" (vol: 600)
  → keyword: "svářečka mig" (prefer CZ), volume: 1100 (sum)
  → canonical scoring: (has_diacritics=True, volume=600, length=13) WINS
  2100 → 1950 (-7%)

KROK 3.4: Word-order dedup (OPTIONAL, jen e-commerce)
  "mig svarecka 200a" + "svarecka mig 200a" → merge
  1950 → 1850 (-5%)

KROK 3.5: Filtering
  min_volume: 10, blacklist: ["kurz", "skoleni", "prace"]
  1850 → 1600 (-14%)

OUTPUT: keywords_clean.xlsx (XLSX multi-sheet)
  Sheet "Final Keywords": 1600 clean keywords
  Sheet "All Keywords": vsechny s flagy (is_duplicate, has_variant...)
  Sheet "Merged Variants": odebrane varianty s merged_into
  Sheet "Variant Clusters": cluster_id, type, vsechny KW v clusteru, canonical
  Sheet "Summary": metriky (input, exact dupes, diacritics, word-order, filtered, final)
+ data/interim/keywords_removed.csv (odebrane pri dedup - pro kontrolu)
+ data/interim/keywords_filtered_out.csv (odebrane filterem - pro kontrolu)
```

### Kroky

**3.1 Text normalizace**
- lowercase, strip whitespace
- multiple spaces → single space
- remove special characters (zachovat pismena, cisla, mezery)
- POZOR: nezahodit +, -, & v brand keywords (C++, H&M)

**3.2 Exact dedup**
- Groupby keyword_normalized, sum volumes
- Track: is_exact_duplicate, duplicate_of (pro audit trail)

**3.3 Diacritics dedup**
- Pouzit STATIC DIACRITICS MAP (ne NFD decomposition - NFD obcas rozbije specialni znaky):
```python
DIACRITICS_MAP = str.maketrans(
    "áäčďéěíĺľňóôŕřšťúůýž",
    "aacdeeillnoorrstuuyz"
)
```
- PREFERUJ variantu S diakritikou (ne ASCII)
- **Canonical selection scoring** (mBank pattern): vybira se varianta s nejvyssim skore
  - Score = (has_diacritics: bool, volume: int, -length: int)
  - Priklad: "svářečka" (diacritics=True, vol=600) > "svarecka" (diacritics=False, vol=500)
- Volume: sum volumes vsech variant (default strategie)
- Uloz all_variants (separator: |) a variant_count
- **Cluster report**: pro kazdy cluster zaznamenej vsechny varianty + ktera byla vybrana a proc

**3.4 Word-order dedup (OPTIONAL)**
- Word signature: sorted(remove_diacritics(lowercase).split())
- POZOR: muze zmenit intent ("pojisteni auta" ≠ "auta pojisteni")
- Pouzit jen pro e-commerce produkty (params.yaml: word_order_dedup: true)

**3.5 Filtering**
- Volume threshold (params.yaml: min_search_volume)
- Length filter (min_length, max_length)
- Blacklist (params.yaml: blacklist + navrhy z EDA Faze 2)
- **Odebrane KW ulozit zvlast** s duvodem (keywords_filtered_out.csv) pro pripadnou kontrolu

CHECKPOINT: "X → Y keywords (Z% removed). Priklady sloucenych duplicit: [sample]. Ok?"

### Volume strategie (params.yaml: volume_strategy)

| Strategie | Kdy pouzit | Priklad |
|-----------|------------|---------|
| sum_volumes (default) | Celkovy potencial vsech variant | "svářečka mig" (500) + "svarecka mig" (600) → 1100 |
| keep_highest | Reporting, konzervativni odhad | "svářečka mig" (500) vs "svarecka mig" (600) → 600 |

### Output format

**Primarni output: XLSX multi-sheet** (klient/konzultant chce Excel)
- `data/interim/keywords_clean.xlsx` s 5 listy (viz priklad workflow vyse)

**Sekundarni outputy: CSV** (pro pipeline navaznost)
- `data/interim/keywords_clean.csv` (flat export Final Keywords sheetu)
- `data/interim/keywords_removed.csv` (odebrane pri dedup + duvod)
- `data/interim/keywords_filtered_out.csv` (odebrane filterem + duvod)

### Output schema (data/interim/keywords_clean.csv)

Vse z Faze 1 plus:

| Sloupec | Typ | Required | Poznamka |
|---------|-----|----------|---------|
| keyword_no_diacritics | str | NO | Pro matching |
| all_variants | str | NO | Sloucene varianty (separator: \|) |
| variant_count | int | NO | Pocet sloucenych variant |
| merged_into | str | NO | Cilove keyword (jen v removed.csv) |
| removal_reason | str | NO | exact_dedup / diacritics_dedup / word_order_dedup |
| filter_reason | str | NO | volume / length / blacklist: [term] |

---

## Faze 4: Relevance

### Cil
Rozhodnout u kazdeho keyword: je to pro klienta relevantni? ANO / NE / MOZNA.
Nerelevantni keywords se dal nezpracovavaji → uspora casu.

### Jak
Python skript `src/relevance.py`. Rule-based pre-filtering + AI pro nejiste keywords.
Reference: mBank `relevance_analyzer.py` (425 radku, ordered decision tree), DeLonghi `analyze_relevance.py` (607 radku, hybrid AI + rules).

### Vazba na Fazi 0
- **Rule-based pravidla** se berou z `params.yaml` (products → ANO, excluded → NE, competitors)
- **AI kontext** se bere z `docs/business_research.md` (kdo je klient, co dela, jaky trh)
- Cim lepsi Faze 0, tim vic keywords se vyresi rule-based (rychle, zadarmo) a mene pres AI

### Priklad workflow

```
INPUT: keywords_clean.csv (1600 keywords)

KROK 4.0: Test mode (--test 50)
  Zpracuje jen 50 nahodnych KW pro validaci pravidel.
  Uzivatel zkontroluje → upravi params.yaml pokud neco nesedi.
  TEPRVE POTOM se spusti full run.

KROK 4.1: Rule-based (ordered decision tree)
  1. excluded patterns → NE (highest priority)
  2. product patterns → ANO
  3. competitor + product term → ANO (kontext!)
  4. competitor alone → MOZNA
  5. ambiguous terms → MOZNA
  6. partial product match → ANO
  7. default → MOZNA

  "svarecka mig 200a"        → ANO (product match: svarecka)
  "svarečsky kurz brno"      → NE (excluded: kurz)
  "esab svarecka"             → ANO (competitor + product term)
  "esab"                      → MOZNA (competitor alone, no product context)
  "invertor na svarovani"     → MOZNA (no clear match)
  ANO: 800, NE: 300, MOZNA: 500

KROK 4.2: AI klasifikace (jen MOZNA, batch 30-50 per prompt)
  "invertor na svarovani"     → ANO (reason: "invertor = svareci stroj")
  "argon plyn cena"           → ANO (reason: "prislusenstvi pro TIG svarovani")
  "kovarska vyhen"            → NE (reason: "kovarstvi, ne svarovani")
  
  Checkpoint: uklada progres do checkpoint_relevance.json (pro resume pri preruseni)
  High-volume MOZNA retry: KW s volume>500 co zustaly MOZNA → retry az 3x

KROK 4.3: Validace
  FLAG: "esab kontakt" = ANO ale competitor brand
  FLAG: "svarovani wiki" = NE ale volume 2000
  FLAG: MOZNA co zustaly po AI (low confidence)

KROK 4.4: Uzivatel review
  MOZNA zbytky + flagy → clovek rozhodne

OUTPUT: keywords_relevant.csv (1100 ANO keywords)
```

### Kroky

**4.0 Test mode (VZDY pred full run)**
- `python src/relevance.py --test 50` → zpracuje 50 random KW
- Uzivatel zkontroluje vysledky, upravi pravidla v params.yaml
- Teprve potom `python src/relevance.py` (full run)
- Pattern z CPP `classify_xlsx_test.py` — usetri cas a penize za AI

**4.1 Rule-based pre-filtering (ordered decision tree)**
Poradi pravidel JE DULEZITE (mBank pattern — 12 kroku):
1. Irrelevant patterns (excluded z params.yaml) → NE
2. Exact irrelevant terms → NE
3. Product patterns (products z params.yaml) → ANO
4. **Competitor + product context check** → ANO
   - Priklad: "esab svarecka" = competitor + product → ANO (relevantni pro porovnani)
   - Priklad: "esab" = competitor alone → MOZNA (potrebuje kontext)
5. Ambiguous single words → MOZNA
6. Partial product match → ANO
7. Default → MOZNA

**4.2 AI klasifikace pro MOZNA keywords**
- Batch processing (30-50 keywords per prompt, ne 10-20 — validated across projects)
- Prompt obsahuje: client_description, products, excluded z params.yaml + business_research context
- Output: relevance + reason + confidence
- **Checkpoint/resume**: uklada progres do `checkpoint_relevance.json` (DeLonghi pattern)
- **Exponential backoff**: pri API error retry 3x s doubling delay (1s, 2s, 4s)
- **High-volume MOZNA retry**: KW s volume>500 co zustaly MOZNA → retry az 3x s vetsim kontextem
- **tqdm progress bar** pro batch processing
- Model: `--model gpt-4o-mini` (default), `--model gpt-4o` pro vyssi presnost

**4.3 Validace**
- High volume + NE → double check (flag)
- ANO + competitor brand → double check (flag)
- Short reason → flag
- Remaining MOZNA after AI → flag

CHECKPOINT: "ANO: X, NE: Y, MOZNA: Z. Tady jsou MOZNA keywords - projdi a rozhodni."

**4.4 Uzivatel review MOZNA keywords**
AI ukaze MOZNA keywords, uzivatel rozhodni → AI zapise.

CHECKPOINT: "Relevance hotova. X relevantnich keywords. Pokracujeme kategorizaci?"

### Output schema (data/interim/keywords_relevant.csv - jen ANO)

Vse z Faze 3 plus:

| Sloupec | Typ | Required | Poznamka |
|---------|-----|----------|---------|
| relevance | str | YES | ANO / NE / MOZNA |
| relevance_reason | str | YES | Max 15 slov |
| relevance_source | str | NO | rule / ai |
| relevance_confidence | str | NO | high / medium / low |

Dalsi soubory:
- data/interim/keywords_with_relevance.csv (vsechny vcetne NE)
- data/interim/relevance_review.csv (flagged for review)
- checkpoint_relevance.json (pro resume pri preruseni)

---

## Faze 5: Kategorizace

### Cil
Otagovat kazde relevantni keyword: typ, produkt, brand, intent, funnel.
Oznacit money keywords pro SERP clustering.

### Jak
Python skript `src/categorization.py`. Pouziva `src/ai_client.py` (sdileny modul pro OpenAI/Anthropic/Gemini).
Reference: DeLonghi `category_analyzer.py` (few-shot, checkpoint), CPP `categorize_openai.py` (per-segment), mBank (16 dimenzi).

### Vazba na Fazi 0, 2, 4
- **Categorization schema** se bere z `params.yaml` (typ, produkt, brand, specifikace)
- **N-gram patterns z EDA (Faze 2)** se PRED spustenim pouziji k rozsireni params.yaml product patterns
- **Business research** dava AI kontext pro spravnou kategorizaci
- **Few-shot examples** se generuji z rule-based vysledku

### Priklad workflow

```
INPUT: keywords_relevant.csv (1100 ANO keywords)

KROK 5.0: Rozsireni params.yaml z EDA n-gramu (AI + clovek)
  AI precte eda_summary.json a navrhne:
  - Nove product patterny z bi-gramu ktere se nevyskytly v params.yaml
  - Nove intent patterns (TRANS: cenik, na prodej; INFO: jak postavit)
  - Nove typ patterns (legislativa, sluzba, komponenta, reference)
  Clovek schvali → AI updatne params.yaml
  CIL: rule-based pokryje 80%+ misto 60%

KROK 5.1: Test (--test 20, rule-based + AI + reasoning)
  Script vezme 20 nahodnych KW, udela:
  - Rule-based: pattern matching z params.yaml
  - AI: kategorizuje VSECHNY test KW (ne jen low-confidence)
  Vystup: categorization_test_1.csv se sloupci:
    typ, produkt, intent (rule-based)
    ai_typ, ai_produkt, ai_intent, ai_reason (AI)
    rule_ai_match (shoda/neshoda)

  AI ukaze vysledky uzivateli:
  - "Rule pokryl 16/20 (80%). AI souhlasi v 14."
  - "Neshody: 'argon 8l' rule=prazdne, AI=prislusenstvi. Pridat do params?"
  
  Uzivatel muze:
  - Upravit params.yaml
  - Dalsi kolo: --test 20 --test-round 2
  - Jiny model: --test 20 --model gemini-2.0-flash
  - Ukazat prompt: --dry-run

KROK 5.2: Rule-only (--rule-only)
  python src/categorization.py --rule-only
  → Spusti JEN rule-based, ulozi vysledek, UKAZE few-shot examples
  → Clovek zkontroluje few-shot + rule-based vysledky
  → Upravi params.yaml pokud treba → rerun --rule-only
  → Teprve kdyz sedi, pokracuje AI

KROK 5.3: Continue AI (--continue-ai)
  python src/categorization.py --continue-ai
  → Nacte rule-only vysledek, AI jen na low-confidence (~20%)
  → Few-shot examples z rule-based (15-20 prikladu)
  → N-gram kontext z EDA
  → Schema z params.yaml + business research
  → Checkpoint/resume do JSON

KROK 5.3: Money keywords
  TRANS/COMM + volume >= threshold (params.yaml) + ne competitor brand
  → priority = "money_keyword"

KROK 5.4: Validace
  FLAG: intent vs typ mismatch, brand bez brand detected

KROK 5.5: Post-processing
  Brand standardizace, remove brand z generic queries

KROK 5.6: Review (AI + clovek)
  AI ukaze: intent distribuce, top produkty, money KW count, issues

OUTPUT: keywords_categorized.csv + money_keywords.csv + categorization_issues.csv
```

### Kroky detail

**5.0 Rozsireni params.yaml z EDA (PRED test mode)**
Nejdulezitejsi zmena oproti predchozim projektum. AI:
1. Precte `data/interim/eda_summary.json` (n-gramy, bi-gramy)
2. Navrhne product patterny ktere chybi v params.yaml
3. Navrhne nove typ hodnoty (legislativa, sluzba, komponenta...)
4. Navrhne nove intent patterns (TRANS: cenik, na prodej...)
5. Clovek schvali → AI zapise do params.yaml
Bez tohoto kroku rule-based pokryva jen 60%. S timto krokem 80%+.

**5.1 Test mode (VZDY pred full run)**
- `python src/categorization.py --test 20` → rule-based + AI na 20 random KW
- AI klasifikuje VSECHNY test keywords (ne jen low-confidence)
- Vystup obsahuje reasoning sloupec pro kazde keyword
- Ukazuje kde se rule a AI neshoduji
- Iterativni: `--test-round 2` = jina sada slov, `--model gemini-2.0-flash` = jiny model
- `--dry-run` = ukaze prompt bez API callu

**5.2 Full run (rule-based + AI)**
- Rule-based: pattern matching na typ, produkt, brand, intent z params.yaml
- Few-shot extraction: 15-20 high-confidence prikladu z rule-based
- AI: jen low-confidence keywords, batch 30-50
- Multi-model: `--model gpt-4o-mini` (default), `gpt-4o`, `gemini-2.0-flash`, `claude-sonnet-4-5-20241022`
- Checkpoint/resume, exponential backoff, tqdm

**5.3 Intent + funnel**

| Intent | Signaly | Funnel |
|--------|---------|--------|
| INFO | co je, jak, proc, pruvodce, navod | TOFU |
| COMM | nejlepsi, recenze, porovnani, vs, hodnoceni | MOFU |
| TRANS | koupit, cena, cenik, objednat, kalkulacka, na prodej, levne | BOFU |
| NAV | login, kontakt, pobocka, [brand name] | BRAND |

**5.4 Money keyword flag**
- Intent: TRANS nebo COMM
- Volume >= money_threshold (params.yaml, default 20)
- NENI konkurencni brand
- → priority = "money_keyword"

**5.5 Validace konzistence**
- Intent vs typ mismatch (TRANS + dotaz = chyba)
- Brand keyword bez brand detected
- Product keyword bez produkt

**5.6 Post-processing**
- Brand standardizace (synonyma, akvizice z params.yaml)
- Remove brand z generic queries (KW neobsahuje brand explicitne)
- Reprocess missing values (AI vratilo prazdne pole)

CHECKPOINT: Ukazat sample 20 keywords → "Sedi intent a produkt? Neco spatne?"

### Output schema (data/interim/keywords_categorized.csv)

Vse z Faze 4 (jen ANO keywords) plus:

| Sloupec | Typ | Required | Poznamka |
|---------|-----|----------|---------|
| typ | str | NO | Dle schema klienta |
| produkt | str | NO | Dle schema klienta |
| brand | str | NO | Nazev brandu |
| brand_type | str | NO | own / competitor |
| specifikace | str | NO | Cilova skupina/varianta |
| intent | str | YES | INFO / COMM / TRANS / NAV |
| funnel | str | YES | TOFU / MOFU / BOFU / BRAND |
| priority | str | NO | money_keyword nebo null |
| categorization_reason | str | NO | Vysvetleni AI |

Dalsi soubory:
- data/interim/money_keywords.csv (subset s priority=money_keyword)
- data/interim/categorization_issues.csv (flagged inconsistencies)
- data/interim/categorization_test_N.csv (test round vysledky)
- checkpoint_categorization.json (pro resume pri preruseni)

---

## Faze 6: SERP Clustering (optional)

### Cil
Seskupit money keywords ktere patri na STEJNOU stranku (Google je vidi jako semanticky ekvivalentni).

### Kdy pouzit
- Hodne money keywords (100+) → ANO
- Malo money keywords (<50) → NE, rucni review staci
- Nejasne hranice mezi tematy → ANO
- Jasne produktove kategorie → NE, staci Faze 5

### Kroky

**6.1 SERP data collection**
- Jen pro money keywords (typicky 100-300)
- Ahrefs SERP overview nebo externi nastroj (Keyword Insights)

**6.2 URL overlap matrix**
- Pro kazdy par keywords: kolik URL se prekryva v top 10
- Overlap = intersection / 10 (ne Jaccard)
- Threshold: >30% = same cluster

**6.3 Clustering**
- Hierarchical clustering na distance matrix
- Nebo externi nastroj (Keyword Insights)

**6.4 Cluster naming**
- Pojmenovat podle highest volume keyword v clusteru

CHECKPOINT: "X clusteru z Y money keywords. Top 10 clusteru: [tabulka]. Dava smysl?"

### Output schema (data/interim/keywords_clustered.csv)

Vse z Faze 5 plus:

| Sloupec | Typ | Required | Poznamka |
|---------|-----|----------|---------|
| cluster_id | int | NO | Jen money keywords |
| cluster_name | str | NO | Highest volume KW v clusteru |

**Pokud Faze 6 nebezela:** pouzij `produkt` jako fallback pro cluster_name.

---

## Faze 7: Dashboard / Overview

> Zatim nespecifikovano - doplni se po otestovani Fazi 0-6.

Kontingencni tabulky, grafy, prehledy. Kolik keywords podle intent, funnel, produkt, brand.
Volume distribuce po kategoriich. Vizualni prehled pro klienta/konzultanta.
Cim: Jupyter notebook nebo Google Sheets.

---

## Faze 8: Competitive Gap

> Zatim nespecifikovano.

Kde konkurent rankuje a klient ne (nebo hur). Quick wins = klient pozice 4-20, konkurent top 3, nizke KD.
Content gaps = konkurent ma stranku, klient nema.
Cim: Data z Marketing Miner (SERP pozice) + Python analyza.

---

## Faze 9: Scoring / Prioritizace

> Zatim nespecifikovano.

Ohodnotit kazde keyword composite skorem. Business value (intent) x difficulty (KD) x traffic potencial (volume).
Rozdelit do tieru (P1, P2, P3, P4).
Cim: Python skript.

---

## Faze 10: Content Mapping

> Zatim nespecifikovano.

Priradit keywords na URL (existujici nebo nove stranky). Doporucit typ obsahu (blog, kategorie, produkt, LP).
Identifikovat co vytvorit, co optimalizovat, co nechat.
Cim: Python + manualni review.

---

## Faze 11: Validation + Export

> Zatim nespecifikovano.

QA kontrola (sample check, konzistence). Finalni Excel deliverable pro klienta. Executive summary.
Cim: Python + manualni review.

---

## Enum hodnoty (STRICT)

```
relevance:  ANO | NE | MOZNA
intent:     INFO | COMM | TRANS | NAV
funnel:     TOFU | MOFU | BOFU | BRAND
brand_type: own | competitor
priority:   money_keyword | null
confidence: high | medium | low
```

---

## Run Modes

Kazdy skript podporuje 3 rezimy:

| Rezim | Flag | Popis |
|-------|------|-------|
| interactive | (default pro faze 4, 5) | Checkpointy, pta se, ceka na review |
| auto | `--auto` (default pro faze 1C, 2, 3, 6) | Probehne cela, vypise summary |
| test | `--test N` | Zpracuje N nahodnych KW pro validaci |

### Ktere faze mohou bezet v auto mode

| Faze | Default | Auto OK? | Duvod |
|------|---------|----------|-------|
| 1C Merge | auto | ANO | Jen slouceni souboru, zadne rozhodovani |
| 2 EDA | auto | ANO | Jen analyza, zadna zmena dat |
| 3 Cleaning | auto | ANO | Deterministicke, params.yaml ridi vse |
| 4 Relevance | interactive | NE | MOZNA keywords potrebuji lidsky review |
| 5 Kategorization | interactive | NE | Potreba validovat schema + few-shot |
| 6 SERP Clustering | auto | ANO | Jen vypocet, threshold z params |

### Jak pouzivat

```bash
# Faze 1C-3 muzou bezet za sebou bez interakce:
python src/merge_sources.py
python src/eda_notebook_generator.py
python src/cleaning.py

# Faze 4-5 VZDY nejdrive --test, pak review, pak full run:
python src/relevance.py --test 50
# ... review vysledky, uprav params.yaml ...
python src/relevance.py

python src/categorization.py --test 20
# ... review vysledky ...
python src/categorization.py
```

### V konverzaci s AI

Kdyz uzivatel rekne "spust fazi 2" nebo "udelej EDA":
- Pokud je faze auto-friendly → AI spusti a reportuje vysledek
- Pokud je faze interactive → AI ukazuje vysledky a pta se na review

Kdyz uzivatel explicitne rekne "auto" nebo "neptej se":
- AI spusti i interactive faze bez checkpointu (uzivatel prevzal zodpovednost)

---

## Pravidla

1. **Kazda faze = konverzace** - ne automaticky beh. Ukazuj vysledky, ptej se na review.
2. **Reason sloupec vzdy** - u relevance i kategorizace vzdy ukladej duvod (pro debugging).
3. **Contract-first** - dodrzuj datove schema presne. Enum hodnoty pouzivej PRESNE jak jsou definovane.
4. **data/raw je READONLY** - pipeline vystupy jdou do data/interim/.
5. **Prefer diacritics** - pri dedup preferuj ceskou variantu pred ASCII. Pouzivat STATIC DIACRITICS MAP (ne NFD).
6. **AI jen pro nejiste** - rule-based first, AI jen pro MOZNA/low-confidence keywords.
7. **Batch AI** - 30-50 keywords per prompt (validated across 4 projects). Nikdy 1 per call.
8. **Validace vzdy** - sample check po kazde AI klasifikaci.
9. **Test mode pred full run** - vzdy `--test` s 20-50 KW pred spustenim full AI klasifikace.
10. **Checkpoint/resume** - AI skripty ukladaji progres do JSON. Preruseny beh = pokracovani, ne restart.
11. **Few-shot examples** - AI kategorizace MUSI obsahovat 15-20 prikladu z rule-based vysledku.
12. **XLSX output** - klient/konzultant chce Excel. Primarni output = multi-sheet XLSX, CSV jako sekundarni.
13. **Audit trail** - dedup musi generovat cluster report (ktere varianty se sloucily a proc).
14. **Post-processing** - po AI kategorizaci vzdy zkontrolovat/opravit brandy a konzistenci.

---

## Kdyz neco nefunguje

Framework ma known issues: `/Users/admin/Documents/Akws/Akw_framework/ISSUES.md`

Pokud narazis na problem:
1. Oprav ho v aktualnim projektu
2. Zaznamenej do ISSUES.md
3. Aktualizuj tento skill pokud je to systemovy problem

---

## Reference projekty

| Projekt | Cesta | Co je uzitecne |
|---------|-------|---------------|
| aks_svarecky | ~/Documents/Akws/aks_svarecky/ | Testovaci projekt - cleaning.py, relevance.py, params.yaml |
| evisions_akw | ~/Documents/Akws/evisions_akw/ | Parallel GPT batch, content gap |
| Delonghi | ~/Documents/Akws/Delonghi/ | ML model, GPT kategorizace |
| mBank | ~/Documents/Akws/mbank/ | Iterace v2, Google Sheets helper |
| delonghi 2 mixery | ~/Documents/Akws/delonghi 2 mixery/ | Doporuceni dokument, LB analyza |
