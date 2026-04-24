---
name: akw
description: AKW - Analyza klicovych slov. Framework pro keyword research projekty. Faze 0-11 od sběru dat po klientský deliverable.
---

# AKW - Analyza klicovych slov

## Kontext

Framework pro analyzu klicovych slov. Pouziva se opakovane pro klienty (e-shopy, sluzby, weby).
Vytvoren na zaklade 6 realnych projektu (Delonghi, mBank, CPP, eVisions, svarecky, Delonghi mixery).

**Framework dokumentace:** `/Users/admin/Documents/Akws/Akw_framework/`
**Known issues:** `/Users/admin/Documents/Akws/Akw_framework/ISSUES.md`
**Referencni projekty:** `/Users/admin/Documents/Akws/`

---

## HARD RULES (ctete nez cokoliv udelate)

1. **Faze 0.2 — deep research v Claude Desktop, NE v Claude Code.** AI vygeneruje prompt → user spusti externe → vlozi vysledek zpatky. AI **nespousti** research automaticky v Claude Code (mala hloubka).
2. **Faze 1A/1B — seed sber dela ciste clovek.** AI **NESMI** generovat seedy pres DFS MCP, Ahrefs MCP ani zadne keyword API. AI muze jen v konverzaci *navrhnout* co pouzit a ceka az user nahraje data do `data/raw/`.
3. **`data/raw/` je READ-ONLY.** AI nesmi prepisovat ani doplnovat — je to ground truth od uzivatele.
4. **Nikdy nespustit `export.py --to-sheets` automaticky.** Google Sheets sync jen on-demand, jinak prepise klientske upravy.
5. **Vzdy `--test N` pred full run** (cleaning, relevance, categorization) — ne kvuli cene (AI je levna), ale pro **validaci kvality promptu + schema + dat**. Po testu projit vysledky s userem nez pustis full.

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
FAZE 6.5: SERP Enrichment ....... pozice klienta + konkurence, KD, SERP features
FAZE 7: Dashboard ............... deskriptivni vrstva — "jak data vypadaji"
FAZE 8: Competitive Gap ......... diagnosticka vrstva — "kde jsou mezery"
FAZE 9: Scoring ................. prioritizacni vrstva — "co resit jako prvni" (P1-P4)
FAZE 10: Content Mapping (opt) .. akcni vrstva — KW → URL → content type
FAZE 11: Export & Deliverables ... klientsky package (executive summary, XLSX, opt. Sheets)
```

---

## Faze 0: Project Setup

### Cil
Pochopit byznys klienta, definovat cile analyzy, vytvorit projekt.
Vystupem je kompletni popis projektu: brief + research + params.yaml.

### Prehled

```
0.1  BRIEF         — 11 poli, otazky POSTUPNE po jedne    [checkpoint]
0.2  RESEARCH      — iterativni v Claude Code, 5 sekci    [checkpoint]
0.3  PARAMS.YAML   — generovani s inline traceability     [checkpoint]
0.4  PROJECT       — vytvoreni projektu (TBD, FW-002)
```

Vsechno se drzi v chatu az do 0.4. Projekt se vytvori az kdyz je vse potvrzene.

---

### 0.1 BRIEF — otazky POSTUPNE po jedne

AI klade otazky **jednu po druhe** (ne vsechny najednou). Po kazde odpovedi:
- kratce potvrdi pochopeni
- **ukaze progress jako checklist s checkboxy** (ne jen "X/11 hotovo" — user chce videt co uz odpovedel)
- pokud je odpoved nejasna, IHNED zpresnuje ("rekl jsi 'novy obsah' - myslis blog nebo nove kategorie?")

**Format progress displaye** (po kazde odpovedi zobraz cely seznam, zaskrtle polozky maji odpoved v hranate zavorce):

```
Progress: 3/11

- [x] 1. client_name — Braun
- [x] 2. domain — braun.cz
- [x] 3. languages — CS
- [ ] 4. countries
- [ ] 5. business_type
- [ ] 6. primary_goal
- [ ] 7. in_scope
- [ ] 8. out_of_scope
- [ ] 9. competitors (volitelne)
- [ ] 10. priority_products (volitelne)
- [ ] 11. insider_info (volitelne)

Dalsi otazka: **Cilove zeme? CZ / SK / oboje?**
```

**Povinna pole (1-8, blokuji pokracovani):**

| # | Pole | Priklad otazky |
|---|------|----------------|
| 1 | `client_name` | "Jak se jmenuje klient?" |
| 2 | `domain` | "Jaka je domena? (napr. klient.cz)" |
| 3 | `languages` | "Jaky jazyk? CS / SK / oboje?" |
| 4 | `countries` | "Cilove zeme? CZ / SK / oboje?" |
| 5 | `business_type` | "Typ byznysu? e-shop / sluzba / info / mix?" |
| 6 | `primary_goal` | "Co chces touto analyzou dosahnout?" |
| 7 | `in_scope` | "Jake produkty/sluzby jsou IN scope? (vyjmenuj hlavni)" |
| 8 | `out_of_scope` | "Co explicitne NENI scope? (co vyloucit)" |

**Volitelna pole (9-11, lze skip):**

| # | Pole | Priklad otazky |
|---|------|----------------|
| 9 | `competitors` | "Znas konkurenci? (2-5 jmen/domen). Pokud ne, dohledam v research." |
| 10 | `priority_products` | "Je nejaky produkt/tema priorita? (launch, focus area)" |
| 11 | `insider_info` | "Vis neco co SEO tool nevidi? (klientovy plany, omezeni)" |

**Validace behem dotazovani:**
- `primary_goal` ma byt konkretni — ne "chceme vic traffic"
- `out_of_scope` MUSI mit >=1 polozku (nuti usera premyslet nad hranicemi)

CHECKPOINT 0.1: AI shrne vsech 11 poli v tabulce → "Sedi to? Chces upravit?"
(ceka na OK nebo upravy; NIKDY nepokracuje dal bez potvrzeni)

---

### 0.2 RESEARCH — externi (Claude Desktop deep research)

Research **NEbezi v Claude Code** — in-code research nema dostatecnou hloubku (male coverage, slabe scraping, zadne pretrvale browsing session). Misto toho AI vygeneruje **hotovy prompt** ktery user zkopiruje do **Claude Desktop s web search** nebo jineho deep-research nastroje (ChatGPT Deep Research, Perplexity Pro). Vysledek user vlozi zpet do chatu.

**Workflow:**

```
STEP 1  AI vygeneruje prompt na miru briefu
        (sablona: docs/DEEP_RESEARCH_PROMPT_TEMPLATE.md + vyplnene placeholdery z 0.1)
  ↓
STEP 2  AI ukaze prompt v chatu jako copy-paste ready text
        + instrukci "spust v Claude Desktop (s web search) a vysledek vloz sem"
  ↓
STEP 3  USER spusti research externe, vlozi cely vystup zpatky do chatu
  ↓
STEP 4  AI validuje vystup (kontrola ze vsech 6 sekci je vyplnenych)
        Pokud nejaka sekce chybi → rekne: "Sekce X chybi, doplnis rucne nebo spustit znovu?"
  ↓
STEP 5  AI ulozi vystup do docs/business_research.md (bez modifikace, jen header + date)
  ↓
STEP 6  CHECKPOINT — "Research ulozen. Sedi to? Pokracujeme na params.yaml?"
```

**Sablona promptu:** `docs/DEEP_RESEARCH_PROMPT_TEMPLATE.md` v repu. AI vezme sablonu + nahradi placeholdery (`<CLIENT>`, `<DOMAIN>`, `<SEO cil>`, `<B2B/B2C/B2B2C>`, ...) z odpovedi 0.1.

**Ocekavany output structure (co AI zkontroluje pri validaci):**

```markdown
## 1. Klient: <CLIENT>
   - Web struktura (navigace, landing pages, URL patterns)
   - Produktovy/sluzbovy katalog
   - Pozicionovani a cilovka
   - Technicke SEO signaly (hreflang, structured data)

## 2. Primi konkurenti
   Tabulka: domena | positioning | hlavni produktova rada | velikost

## 3. Neprimi konkurenti / substituty
   (3-5 alternativ ktere kradou navstevnost)

## 4. Retail / distribucni kanaly
   (3-5 marketplacu/retail hracu)

## 5. Trh a cilovka
   - Zakaznicke segmenty
   - Trendy 2-3 roku
   - Sezonni vzorce

## 6. Terminologie a intent signaly
   - Odborna terminologie v {{LANGUAGE}}
   - Synonyma, regionalni varianty
   - TRANS / INFO / COMM intent slova
```

**Ukazkovy vystup (snippet — jak ma research vypadat po vlozeni):**

```markdown
## 1. Klient: Braun CZ

### 1.1 Web struktura
- Hlavni navigace: Kuchyne / Vlasy / Telo / Zubni pece / Maly spotrebic
- Landing pages: /kuchyne/mixery, /kuchyne/spenace, /kuchyne/tyckove-mixery
- URL pattern: /{kategorie}/{podkategorie}/{produkt-slug}/
- Blog: NENI (source: https://www.braun.cz/cs-cz/navigace)

### 1.2 Produktovy katalog
- Mixery: tyckove (MQ 5235 WH, MQ 7025X, ...), stolni
- Spenace: MixStart 5, PowerBlend 7, ...
- Cenovy model: fixni MSRP, distribuce pres Alza/Mall/Datart
- USP z webu: "75 let vyroby", "Swiss-quality engineering", "dozivotní zaruka motoru"

### 1.3 Pozicionovani
- Audience: "premium segment zakazniku hledajici spolehlivost"
  (source: https://www.braun.cz/cs-cz/about)
- 75 let na trhu, notable klienti: not found

## 2. Primi konkurenti

| Domena | Positioning | Hlavni rada | Velikost |
|--------|-------------|-------------|----------|
| bosch-home.cz | "German engineering pro kazdodenni kuchyn" | MUM, Cookit | not found |
| kitchenaid.cz | "Profesionalni vybaveni pro domaci kuchyn" | Artisan, Pro Line | not found |
| tefal.cz | "Smart cooking technology" | Optigrill, Easy Soup | not found |
| philips.cz | "All-in-one air fryer ecosystem" | Airfryer XXL, Avance | not found |

## 3. Neprimi konkurenti / substituty
- Profesionalni gastro (Robot Coupe, Vitamix) — lovi power usery
- DIY hobby kuchari (Thermomix, Monsieur Cuisine) — all-in-one substitut
- Low-cost ECG / Sencor — cena-driven segment

[...pokracuje sekce 4-6...]
```

**Validace AI:**
- Kazda ze 6 sekci ma minimalne 2-3 polozky (ne prazdne headery)
- "not found" je OK (explicit negativni info), ale nesmi byt vic nez 30 % vseho obsahu
- Sekce 2 a 3 maji aspon 3 konkurenty (pokud trh existuje)
- Konkretni URL citace — alespon 5-10 v celem dokumentu

Pokud validace selze → AI rekne: "Research je slaby v sekci X (Y% neprazdneho obsahu). Spustit znovu s vetsi hloubkou, nebo doplnit rucne?"

**Cilovy soubor:** `docs/business_research.md`

Format:

```markdown
# Business Research — <CLIENT>

**Zdroj:** Claude Desktop deep research
**Datum:** YYYY-MM-DD
**Prompt:** odpovida docs/DEEP_RESEARCH_PROMPT_TEMPLATE.md

---

[kompletni vystup 6 sekci, bez modifikace]
```

CHECKPOINT 0.2: "Research ulozen v docs/business_research.md (X slov, Y URL citaci). Pokracujeme na params.yaml?"

---

### 0.3 PARAMS.YAML — generovani s inline traceability

AI vygeneruje kompletni `params.yaml` (schema nize v tomto dokumentu). Kazda NE-default hodnota ma **inline komentar** odkazujici na zdroj:

- `# brief #N` — z odpovedi na otazku N v 0.1
- `# research X.Y` — z research sekce X podsekce Y
- `# default AKW` — framework default
- `# ADDED z research X — user schvalil v 0.2` — rozsireno behem research

**Priklad (zkraceny):**

```yaml
client:
  name: "Svarecky-obchod"           # brief #1
  domain: "svarecky-obchod.cz"      # brief #2
  language: ["cs", "sk"]            # brief #3
  country: ["CZ", "SK"]             # brief #4

cleaning:
  word_order_dedup: true            # business_type=e-shop → bezpecny
  volume_strategy: "sum_volumes"    # default AKW

filters:
  min_search_volume: 5              # priority=TIG launch → nizky SV OK
  blacklist:
    - "kurz"                        # research C.3 (pain point, ne nakup)
    - "skoleni"                     # research C.3
    - "wikipedia"                   # default AKW blacklist

relevance:
  products:                         # brief #9 + research A.1 + D
    - "MIG svarecka"
    - "TIG svarecka"                # PRIORITY (brief #12)
    - "argon"                       # research D.6 — GAP (competitors nemaji)
  excluded:                         # brief #10
    - "servis"
    - "bazar"
  competitors:                      # brief #11 + research B
    - "esab"
    - "kuhtreiber"                  # ADDED z research B — user schvalil v 0.2
```

**Pravidla:**
- `products` ⊃ `in_scope` z briefu (rozsireno o research findings)
- `excluded` ⊃ `out_of_scope` z briefu
- `competitors` = brief #11 ∪ research B additions (pokud user schvalil)
- Schema validuje proti `params.yaml schema` (nize)
- AI UKAZE params.yaml v chatu (zatim NEPISE soubor, zapise az v 0.4)

CHECKPOINT 0.3: user reviewuje params.yaml → "OK" / "zmenit X, Y"

---

### 0.4 PROJECT CREATE — TBD

Vytvoreni adresare, zapis docs/, CLAUDE.md, params.yaml. Mozne rozsireni: sanity check (smoke test na 20 KW), decision log, scope/timeline dokumenty.

**Status:** TBD — specifikace v FW-002 (nezavisi na FW-001, reseni az po merge).

Zatim po CHECKPOINT 0.3: AI se zepta "Pokracujeme vytvorenim projektu? Kam ho umistit? (default: ~/Documents/Akws/[nazev]/)" a vytvori minimalni strukturu (viz "Projekt struktura" nize).

---

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
  test_sample_size: 25                 # for --test mode (default 25 pro Faze 4)
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
  money_keyword_bonus: 2.0                 # pricteno k business_value pokud priority=money_keyword
  money_threshold: 20                       # min volume pro money_keyword flag (faze 5)
  gap_modifier:                             # pricteno k ranking_probability podle gap_type (faze 9)
    quick_win: 1.5
    close_gap: 0.5
    content_gap: 0.0
    defended: 0.0
    no_opportunity: -2.0
  tier_thresholds:                          # P1-P4 dle priority_score
    P1: 7.5
    P2: 5.0
    P3: 2.5
  ctr_estimates:                            # CTR per pozice (Advanced Web Ranking 2024)
    1: 0.31
    2: 0.15
    3: 0.10
    4: 0.07
    5: 0.05
    6: 0.04
    7: 0.03
    8: 0.025
    9: 0.02
    10: 0.02
    default: 0.005                          # pozice 11+

gap:
  quick_win_position_range: [4, 20]
  close_gap_position_range: [21, 50]
  quick_win_max_kd: 40
  competitor_top_threshold: 3               # konkurent top N = aktivni gap signal

enrichment:                                 # faze 6.5 SERP Enrichment
  serp_source: "marketing_miner"            # marketing_miner / ahrefs / manual
  tracked_competitors: []                   # domeny pro pozice tracking
  include_serp_features: true               # images, video, paa, featured_snippet

content_mapping:                            # faze 10 (optional)
  enabled: false                            # true = fáze 10 beží, false = skip
  url_base: ""                              # klientsky root pro URL navrhy
  content_types:                            # mapovani intent → default content_type
    TRANS_product: "product"
    TRANS_category: "category"
    COMM: "comparison"
    INFO: "blog"
    NAV: "landing"

export:                                     # faze 11
  client_name: ""                           # pouzito v nazvu final XLSX
  include_methodology_sheet: true
  per_segment_sheets: true                  # 1 list per produkt/segment
  google_sheets_export: false               # true = sync na konci (faze 11)
  google_sheets_id: ""                      # target spreadsheet ID

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

> ⚠️ **HARD RULE — Faze 1A a 1B dela ciste clovek.** AI **NESMI** generovat seed keywords pres DFS MCP / Ahrefs MCP / jakykoliv keyword API. AI NESMI spustit script ktery by generoval seedy automaticky. AI muze **pouze v konverzaci navrhnout** (napr. "z briefu + research bych jako seedy zkusil: mixer, blender, tyckovy mixer, ..."), ale finalni seedy sbira clovek z Ahrefs/GSC/product feedu/Marketing Mineru a nahrava je do `data/raw/`. Duvod: quality > quantity, seed sber je strategicke rozhodnuti specialisty, ne automatizace.

**1A: Seed sber (ciste clovek)**

**Krok 1 — AI vytvori prazdny template** (jednorazove, na zacatku Faze 1):

```bash
python /Users/admin/Documents/Akws/Akw_framework/src/create_seeds_template.py \
    --project-root <path> --client "<Client Name>"
```

Vytvori `data/raw/seeds_template.xlsx` — prazdny sheet `seeds` (sloupce keyword, source, volume, kd, position, url, notes) + sheet `instructions`. User do nej pak rucne vklada seedy.

**Krok 2 — Specialista sbira seedy mimo Claude Code:**
- **Ahrefs** (klient + konkurenti — Top pages, Organic keywords)
- **GSC** (Search Console — existing queries klienta)
- **Product feed** / sitemap (interni data klienta)
- **Marketing Miner UI** (CZ keyword database)
- **Vlastni brainstorm** na zaklade briefu + business_research
- Cilovy rozsah: **50-500 seedu** (kvalita > kvantita, ne tisice)

**Krok 3 — AI pomoc behem sberu (v chatu, ne v souboru):**
- **MUZE** v chatu navrhnout konkretni seedy ("z research #4 vidim terminy X, Y, Z — chces je pridat?")
- **MUZE** upozornit na mezery ("chybi ti seedy pro produkt X z params.yaml")
- **NESMI** spustit DFS/Ahrefs/MM API a automaticky generovat keywords
- **NESMI** zapisovat do `data/raw/seeds_template.xlsx` ani jineho souboru v `data/raw/`

Specialista ulozi vyplneny `seeds_template.xlsx` (pripadne prida dalsi soubory z Ahrefs/MM exportu) do `data/raw/`.

**1B: Namnozeni + hledanosti (ciste clovek)**

Specialista vezme seedy → Marketing Miner UI (ne API) — suggestions, related, questions + doplni search volume.
Nahraje vysledek do `data/raw/`.

AI do toho **nevstupuje** — zadne API volani, zadne "pokracuji s generovanim". AI ceka.

CHECKPOINT: "Nahraj vsechny soubory do data/raw/ a dej vedet"
(ceka na upload - v data/raw/ muze byt vic souboru z ruznych zdroju)

**1C: Slouceni + initial dedup (AI)**

AI slouci VSECHNY soubory z `data/raw/`, initial dedup (exact + lowercase). **Az tady AI poprve sahne na data.**

CHECKPOINT: "X keywords z Y souboru. Rozlozeni: [tabulka]. Pokracujeme?"
→ `data/interim/keywords_raw.csv`

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

> Tato faze je volitelna. Zeptej se: "Chces udelat EDA (prozkoumat data + doporuceni pro params.yaml), nebo rovnou pokracovat cistenim?"

### Cil
Poznat co je v datech - jake patterns, co chybi, co je navic.
Vystupy primo ovlivnuji Fazi 3 (co vycistit) a Fazi 4-5 (jak klasifikovat).

### Jak — Python script first, notebook optional

EDA bezi jako **Python script v terminalu** (bez Jupyter setup). AI spusti,
precte strukturovany JSON + stdout, a **v chatu** provede usera vysledky — sekci po sekci,
s komentari a konkretnimi doporucenimi pro `params.yaml`.

**Setup (jednorazovy pokud jeste neni venv):**

```bash
cd ~/Documents/Akws/<projekt>/
python3 -m venv .venv
source .venv/bin/activate
pip install pandas pyyaml matplotlib openpyxl
```

**Spusteni (default — zadny Jupyter):**

```bash
python /Users/admin/Documents/Akws/Akw_framework/src/eda.py --project-root .
```

Co se stane:
- Precte `data/interim/keywords_raw.csv`
- Analyzuje overview, kvalitu dat, n-gramy, coverage produktu/competitors, intent signaly
- Zapise `data/interim/eda_summary.json` (strukturovany vystup pro AI)
- Vytiskne human-readable summary do stdout
- **AI pak precte JSON + stdout a provede usera v chatu**

**Optional — interaktivni notebook pro deeper dive:**

```bash
python /Users/admin/Documents/Akws/Akw_framework/src/eda.py --project-root . --notebook
```

Navic vygeneruje `notebooks/01_eda.ipynb` ktery si user muze otevrit ve VS Code nebo Jupyter pro vlastni experimenty. **Neni potreba pro default flow** — jen kdyz user chce stourat rucne.

### Prubeh konverzace

Po spusteni `src/eda.py` AI precte JSON + stdout a provede usera vysledky — sekci po sekci:

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

### Co EDA MUSI obsahovat (technicke sekce — implementovane v `src/eda.py`)

**Sekce 1: Zakladni prehled**
- Pocet keywords, unikatnich, duplicitnich
- Source breakdown + multi-source overlap
- Volume distribuce (min/max/median/mean + buckety 0-10, 10-50, ...)
- KD distribuce (easy/medium/hard pokud dostupne)

**Sekce 2: Kvalita dat**
- Duplicity preview (exact match)
- Diacritics groups (kolik variant slouci Faze 3)
- Word-order groups
- Top 15 volume (head terms)

**Sekce 3: N-gram analyza**
- Uni-gramy top 30
- Bi-gramy top 20
- Tri-gramy top 15

**Sekce 4: Coverage checks**
- Pokryti produktu z `params.yaml` (jaky produkt ma kolik KW, flag MISSING)
- Pokryti competitors z `params.yaml` (KW + volume)

**Sekce 5: Intent signaly**
- Count INFO / COMM / TRANS / NAV slov (jak, nejlepsi, cena, kontakt ...)

**Sekce 6: Keyword length**
- Median words per KW, single-word count, long-tail (4+ words) ratio

### Output
- `data/interim/eda_summary.json` — strukturovany vystup pro AI
- stdout — human-readable summary
- `notebooks/01_eda.ipynb` — pouze s `--notebook` flagem
- `data/raw/` a `data/interim/keywords_raw.csv` se NEMENI — jen analyza
- `params.yaml` se UPDATNE pokud user souhlasi s navrhy (blacklist, excluded patterns, ...)

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

**3.6 Diacritics check (AI check na konci) — POVINNE**

Cleaning.py slouci varianty s/bez diakritiky **pouze pokud obe existuji v datech**. Pokud input obsahuje jen "kuchynsky robot" a "kuchyňský robot" chybi uplne, vystup zustane bez diakritiky. Proto za cleaningem VZDY bezi:

```bash
python /Users/admin/Documents/Akws/Akw_framework/src/diacritics_check.py \
    --project-root . --mode both
```

Modes:
- `heuristic` (default) — rychla, offline, detekuje typicke CZ patterny (kuchynsk → kuchyňsk, svarec → svářeč, ...)
- `ai` — AI batch (gpt-4o-mini default), pouzije se pro vsechny KW bez diakritiky
- `both` — heuristika + AI pro dvojitou kontrolu

Vystup: `data/interim/keywords_diacritics_review.xlsx` (jen suspects s `suggested_fix`).

**AI po behu precte XLSX a v chatu rekne:**
- "Nasli jsme X podezrelych KW (Y% datasetu). Top suspects: [priklad]"
- "Mam to automaticky aplikovat do `keywords_clean.csv`? [ano/ne/review]"
- User rozhodne — buhe approve all, review per-KW, nebo skip

CHECKPOINT: "X → Y keywords (Z% removed). Priklady sloucenych duplicit: [sample]. Diacritics check: Q suspects. Ok?"

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
- **Rule-based pravidla** se berou z `params.yaml` (products → ANO, excluded → NE, competitors) — slouzi jako **pre-annotation + konzistence**, ne jako "setreni na AI"
- **AI kontext** se bere z `docs/business_research.md` (kdo je klient, co dela, jaky trh)
- **AI bezi VZDY na vsech KW** (ne jen na MOZNA) — rule-based je heuristika, AI je autorita. Cena AI je zanedbatelna oproti hodnote kvalitnejsich vysledku.

### Priklad workflow

```
INPUT: keywords_clean.csv (1600 keywords)

KROK 4.0: Test mode (--test 25)  <-- default 25, MUSI vzdy
  Zpracuje 25 nahodnych KW: rule-based + AI check pro VSECHNY.
  Vysledky v tabulce: keyword | relevance | reasoning
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

KROK 4.2: AI klasifikace (VSECHNY KW, i ANO/NE z rule-based → AI validace)
  Proc: rule-based muze nadhazet false positives/negatives. AI je tam aby
  to overila — byt i jen kontrola — ne aby rozhodovala.

  - MOZNA z rule-based → AI rozhodne ANO/NE/MOZNA + reasoning
  - ANO z rule-based → AI validuje (staci? flag pokud nesedi)
  - NE z rule-based → AI validuje (staci? flag pokud high-volume)

  Checkpoint: uklada progres do checkpoint_relevance.json
  High-volume MOZNA retry: KW s volume>500 co zustaly MOZNA → retry az 3x

KROK 4.3: Validace + flagy
  FLAG: "esab kontakt" = ANO ale competitor brand
  FLAG: "svarovani wiki" = NE ale volume 2000
  FLAG: AI nesouhlasi s rule-based

KROK 4.4: Uzivatel review
  MOZNA zbytky + flagy → clovek rozhodne

OUTPUT: keywords_relevant.csv (X ANO keywords)
```

### Kroky

**4.0 Test mode (VZDY pred full run, default 25 KW)**

```bash
python src/relevance.py --test 25                    # default: gpt-4o-mini
python src/relevance.py --test 25 --model gpt-4o     # pro vyssi presnost
python src/relevance.py --test 25 --model claude-haiku-4-5-20251001
```

- Zpracuje **25 nahodnych KW** (zmenitelne `--test N`)
- Rule-based + AI pro vsechny → jeden kompletni pruchod na vzorku
- **AI VZDY vypise vystup v tabulce:**

  ```
  | keyword              | relevance | reasoning                          |
  |----------------------|-----------|-------------------------------------|
  | svarecka mig 200a    | ANO       | produkt match: svarecka, konkretni model |
  | esab kontakt         | NE (flag) | competitor brand contact, nekoupi tam |
  | invertor svarovani   | ANO       | invertor = druh svareciho stroje   |
  | kovarska vyhen       | NE        | kovarstvi, ne svarovani (mimo scope) |
  | ...                  | ...       | ...                                 |
  ```
- Uzivatel zkontroluje tabulku, upravi params.yaml (products/excluded/competitors)
- Teprve potom full run: `python src/relevance.py` (bez --test)

**Default model pro AI: `gpt-4o-mini`** — rychly a presny pro CZ texty.
Alternativy (uzivatel muze explicitne vybrat):
- `gpt-4o` — vyssi presnost, pro edge cases nebo nuance
- `claude-haiku-4-5-20251001` — Anthropic alternativa
- `gemini-2.0-flash` — Google alternativa

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

**4.2 AI klasifikace — VZDY, pro VSECHNY keywords (i ANO/NE z rule-based)**

> **HARD RULE:** AI bezi na **vsech** keywordech, ne jen na MOZNA. Rule-based je
> pre-annotation (konzistence + traceability), ale AI je **autorita** — dela
> rozhodnuti i na ANO/NE z rule-based. Duvod: rule-based nadhazuje edge cases
> (synonymy, dvojitý význam, regionalni varianty), ktere AI chyti. Cena AI je
> zanedbatelna oproti hodnote kvalitnejsich vysledku.

- Batch processing: **30-50 keywords per prompt** (validated across projects)
- Prompt obsahuje: `client_description`, `products`, `excluded` z params.yaml + business_research context
- AI dostane rule-based navrh jako hint, ale muze ho prebit ("rule-based rekl ANO ale toto je brand competitor context → NE")
- Output: relevance (ANO/NE/MOZNA) + reason + confidence + flag pokud nesouhlas s rule-based
- **Default model:** `gpt-4o-mini` (user muze prepsat `--model <other>`)
- **Checkpoint/resume**: uklada progres do `checkpoint_relevance.json` (DeLonghi pattern)
- **Exponential backoff**: pri API error retry 3x s doubling delay (1s, 2s, 4s)
- **High-volume MOZNA retry**: KW s volume>500 co zustaly MOZNA → retry az 3x s vetsim kontextem
- **tqdm progress bar** pro batch processing

**4.3 Validace**
- AI vs rule-based disagreement → flag
- High volume + NE → flag
- ANO + competitor brand → flag
- Short reason → flag
- Remaining MOZNA after AI → flag

CHECKPOINT: "ANO: X, NE: Y, MOZNA: Z. AI nesouhlasilo s rule-based u F pripadu. Tabulka [top 20 flagu] — review?"

**4.4 Uzivatel review MOZNA + flagy**
AI ukaze MOZNA keywords + vsechny flagy v tabulce keyword|relevance|reasoning|flag,
uzivatel rozhodni → AI zapise.

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

KROK 5.0: NAVRH KATEGORII A HODNOT (AI + clovek)  <-- DULEZITE, PRVNI KROK
  AI precte:
    - params.yaml (existujici categorization schema, pokud nejaky je)
    - business_research.md (kontext klienta)
    - eda_summary.json (n-gramy, produkty, intent signaly)
    - vzorek 50-100 keywords_relevant.csv
  A NAVRHNE kategorie + jejich hodnoty v tabulce:

    | Kategorie     | Hodnoty (navrh)                       | Pokryti |
    |---------------|----------------------------------------|---------|
    | typ           | produkt, sluzba, informace, reference  | 100%    |
    | produkt       | mixer, splech, kavovar, kuchyn. robot  | 70%     |
    | intent        | INFO, COMM, TRANS, NAV                 | 100%    |
    | funnel        | TOFU, MOFU, BOFU, BRAND                | 100%    |
    | brand         | Braun, Bosch, Philips, KitchenAid, ... | 30%     |
    | brand_type    | own, competitor, retail                | 30%     |
    | specifikace   | tyckovy, stolni, rucni, elektricky     | 50%     |

  Uzivatel:
    - Schvali navrh jako je ("OK")
    - Upravi hodnoty ("pridej 'airfryer' do produkt, smaz 'reference' z typ")
    - Smaze celou kategorii ("specifikace nebudeme pouzivat")
    - Prida kategorii ("pridej kategorii 'cenova_urovne': low, mid, premium")

  AI updatuje params.yaml (categorization sekce) → ukaze diff.
  Schema se muze BEHEM prubehu upravovat — po testu (5.2) muze user
  rict "pridej hodnotu X" a AI zase upravi params.yaml.

KROK 5.1: Rozsireni patternu z EDA n-gramu
  Az mame schvalene KATEGORIE, AI navrhne PATTERNS pro kazdou hodnotu.
  Priklad: produkt='mixer' → patterny ['mixer', 'mixéry', 'mixování', 'blender']
  Bi-gramy z EDA pomohou pokryt variant (tyckovy_mixer, stolni_mixer).

KROK 5.0b: Vyber AI modelu (dotaz pro usera)
  "Jaky model pouzit? 1=gpt-4o-mini (default) | 2=gpt-4o |
   3=claude-haiku-4-5 | 4=gemini-2.0-flash"

KROK 5.2: Test (--test 10, rule-based + AI + reasoning)
  Script vezme **10 nahodnych KW**, udela:
  - Rule-based: pattern matching z params.yaml
  - AI: kategorizuje VSECHNY 10 KW (ne jen low-confidence)
  Vystup VZDY jako tabulka v chatu: jeden radek per KW,
  sloupce = VSECHNY kategorie ze schvaleneho schema + reasoning

  AI ukaze vysledky uzivateli + highlightne neshody rule vs AI

  Uzivatel muze:
  - Schvalit → full run
  - Upravit params.yaml patterny → test znovu
  - Pridat/ubrat hodnoty v schema (zpet na 5.0a) → test znovu
  - Zmenit model → test znovu

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

**5.0 Navrh kategorii a jejich hodnot (PRVNI KROK, POVINNE)**

Pred jakoukoliv implementaci AI **navrhne schema** v tabulce. Bez tohoto
kroku se nesmi pokracovat — user musi vedet co budeme kategorizovat a s
jakymi hodnotami.

AI postup:
1. Precte `params.yaml` (existujici schema, pokud je)
2. Precte `docs/business_research.md` (kontext klienta)
3. Precte `data/interim/eda_summary.json` (n-gramy)
4. Samplne 50-100 `keywords_relevant.csv`
5. Ukaze tabulku:

   ```
   | Kategorie     | Hodnoty                                  | Pokryti (sample) |
   |---------------|------------------------------------------|------------------|
   | typ           | produkt, sluzba, informace               | 95%              |
   | produkt       | mixer, kavovar, robot, splech            | 70%              |
   | intent        | INFO, COMM, TRANS, NAV                   | 100%             |
   | funnel        | TOFU, MOFU, BOFU, BRAND                  | 100%             |
   | brand         | Braun, Bosch, Philips, KitchenAid, ...   | 30%              |
   | brand_type    | own, competitor, retail                  | 30%              |
   | specifikace   | tyckovy, stolni, rucni, elektricky       | 50%              |
   ```

6. User reaguje:
   - "OK, schvaluju" → AI zapise do params.yaml
   - "Uprav X" → AI aktualizuje a znovu ukaze
   - "Pridaj kategorii Y s hodnotami A,B,C" → AI prida
   - "Smaz specifikace" → AI odstrani

7. **Schema se muze menit i pozdeji** — po testu 5.2 user muze rict
   "v hodnotach produkt chybi 'airfryer'" → AI upravi params.yaml a
   test se spusti znovu.

Default kategorie (pokud user nic nerekne): **typ, produkt, intent,
funnel, brand, brand_type**. Hodnoty `intent`/`funnel` jsou pevne
(enum — viz Quick reference v CLAUDE.md). `produkt`, `brand` se odvodi
z business_research.

CHECKPOINT 5.0a: "Navrh kategorii ukazan. Schvalujes jak je, nebo upravit?"

**5.0b Vyber AI modelu (po schvaleni kategorii)**

Po schvaleni kategorii AI **vzdy zepta usera ktery model pouzit** pro
testovani + full run. Format dotazu:

```
Schema kategorii schvaleno. Jaky model pouzit pro AI klasifikaci?

1. gpt-4o-mini       (default, rychly, presny — doporucene)
2. gpt-4o            (vyssi presnost pro edge cases)
3. claude-haiku-4-5  (Anthropic alt)
4. gemini-2.0-flash  (Google alt)

[Napis 1/2/3/4 nebo plny model string]
```

User odpovi → AI si model pamatuje pro vsechny dalsi kroky v Fazi 5
(test + full run). Pokud user chce zmenit model behem procesu, muze
kdykoliv rict "prepni na gpt-4o".

CHECKPOINT 5.0b: "Model = X. Pokracujeme na test mode (10 KW)?"

**5.1 Rozsireni patternu z EDA (pro rule-based)**
Kdyz mame kategorie schvalene, AI navrhne **patterns** pro pattern matching:
1. Precte eda_summary.json (bi-gramy, tri-gramy)
2. Pro kazdou hodnotu kategorie (napr. produkt='mixer') navrhne regex/patterns
   ktere ji matchuji v textu KW
3. User schvali → AI zapise do params.yaml
Cil: rule-based pokryje 80%+ misto 60%.

**5.2 Test mode (VZDY pred full run, default 10 KW)**

```bash
python src/categorization.py --test 10 --model <model-z-5.0b>
```

- Rule-based + AI na **10 random KW** (default — maly test na validaci schema)
- AI klasifikuje VSECHNY test keywords (ne jen low-confidence)
- **Vystup VZDY tabulka:** pro kazde z 10 KW jeden radek se VSEMI kategoriemi
  ze schvaleneho schema (5.0a) + reasoning

  Priklad (podle schvaleneho schema z 5.0a):

  ```
  | keyword              | typ       | produkt | intent | funnel | brand | brand_type | specifikace | reasoning                          |
  |----------------------|-----------|---------|--------|--------|-------|------------|-------------|-------------------------------------|
  | braun tyckovy mixer  | produkt   | mixer   | TRANS  | BOFU   | Braun | own        | tyckovy     | konkretni produkt + brand klienta  |
  | jak vyzbrat mixer    | informace | mixer   | INFO   | TOFU   | -     | -          | -           | jak = info intent, produkt zminen |
  | nejlepsi kuchyn robot| produkt   | robot   | COMM   | MOFU   | -     | -          | stolni      | nejlepsi = comm, agnostic k brand |
  | ...                  | ...       | ...     | ...    | ...    | ...   | ...        | ...         | ...                                 |
  ```
  *(sloupce odpovidaji kategorii schvaleneho schema — pokud user smazal
  specifikace, neni sloupec; pokud pridal cenova_urovne, je navic)*

- Ukazuje kde se rule a AI neshoduji → flag radek
- Iterativni: `--test-round 2` = jina sada 10 KW (pro spot check)
- `--dry-run` = ukaze prompt bez API callu
- Po testu user muze:
  - **schvalit** → full run
  - **upravit params.yaml** patterny → test znovu
  - **pridat/ubrat hodnoty** v schema (zpet na 5.0a) → test znovu
  - **zmenit model** → test znovu s jinym

Model = ten co user zvolil v **5.0b** (default `gpt-4o-mini`).

**5.3 Full run (rule-based + AI)**
- Rule-based: pattern matching na typ, produkt, brand, intent z params.yaml
- Few-shot extraction: 15-20 high-confidence prikladu z rule-based
- AI: jen low-confidence keywords, batch 30-50
- Default model: `gpt-4o-mini`
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

## Faze 6.5: SERP Enrichment

### Cil
Doplnit k relevantnim keywords pozice klienta, pozice konkurence, KD a SERP features. Tato data jsou nezbytna pro fazi 7 (ranking distribuce), fazi 8 (gap typology) a fazi 9 (ranking_probability scoring).

### Jak
Python skript `src/serp_enrichment.py`. AI vytvori a spusti. Data z Marketing Miner (primarni), Ahrefs (doplnkove), optional manual/Google SERP.

### Vazba na params.yaml
- `enrichment.serp_source` — primarni zdroj (marketing_miner / ahrefs / manual)
- `enrichment.tracked_competitors` — seznam domen konkurentu pro pozice tracking
- `enrichment.include_serp_features` — jestli stahovat SERP features (images, video, paa, featured_snippet)

### Kroky

**6.5.1 Load input**
- Input: `keywords_clustered.csv` (pokud faze 6 bezela), jinak `keywords_categorized.csv`
- Filter: typicky jen `relevance=ANO` (mene API volani, nizsi naklady)

**6.5.2 Pozice klienta**
- Pro kazdy KW: Google pozice klientovy domeny (`client.domain` z params.yaml)
- Pokud pozice > 100 nebo neexistuje → `position_client = null` (nerankuje)

**6.5.3 Pozice konkurentu**
- Pro kazdy competitor v `enrichment.tracked_competitors`: Google pozice
- Ulozeno jako `position_<competitor_domain>` sloupce
- `best_competitor_position` = minimum ze vsech competitor pozic
- `best_competitor_domain` = ktery konkurent je nejvyse

**6.5.4 KD (Keyword Difficulty)**
- Pokud uz je v datech (z fáze 1 Ahrefs) → pouzij
- Jinak: dotaz na Ahrefs API nebo Marketing Miner difficulty score
- Normalizace na 0-100

**6.5.5 SERP features**
- Pro kazdy KW: jake features jsou v top 10 (pipe-separated)
- Priklady: `images|paa|featured_snippet|shopping|video|local_pack`
- `has_featured_snippet` (bool) — zda je featured snippet (velky dopad na CTR)

**6.5.6 Top 10 domains**
- Seznam domen v top 10 (pipe-separated) — pro rychly audit konkurentniho prostoru

**6.5.7 Checkpoint/resume**
- Uklada progres do `checkpoint_enrichment.json` — API rate limits, API errors recovery
- Exponential backoff pri rate limit (1s, 2s, 4s)

CHECKPOINT: "Enrichment hotovy. X KW ma pozici klienta, Y nerankuje. Median best competitor position: Z. Pokracujeme fazi 7?"

### Output schema (data/interim/keywords_enriched.csv)

Vse z predchozi faze plus:

| Sloupec | Typ | Required | Poznamka |
|---------|-----|----------|---------|
| position_client | float | NO | 1.0-100.0, prazdne = nerankuje |
| position_<competitor_domain> | float | NO | Jeden sloupec per tracked competitor |
| best_competitor_position | float | NO | Minimum ze vsech competitor pozic |
| best_competitor_domain | str | NO | Ktery konkurent je nejvyse |
| kd | int | NO | 0-100 (pokud uz neni z faze 1) |
| serp_features | str | NO | pipe-separated (images\|paa\|featured_snippet\|...) |
| has_featured_snippet | bool | NO | True/False |
| top_10_domains | str | NO | pipe-separated |

### Run mode
`auto` — deterministicke API calls, zadne rozhodovani.

---

## Faze 7: Dashboard

### Ucel
Deskriptivni vrstva nad daty. Odpovida na otazku **"Jak data vypadaji"** — struktura datasetu, distribuce, top listy.

NENI to vrstva rozhodovaci. Dashboard NESMI obsahovat:
- Priority P1-P4 (to je faze 9)
- Doporuceni akci (to je faze 8 + 10)
- Composite skore (to je faze 9)

### Jak
Python skript `src/dashboard.py`. Cte `keywords_enriched.csv`, produkuje `07_dashboard.xlsx` s pivoty a grafy. NEMENI main dataset (read-only vrstva).

### Kroky

**7.1 Distribuce**
Pivot tabulky napric dimenzemi:
- Count KW × intent × funnel
- Count KW × produkt × brand_type
- Count KW × priority (money_keyword / not)
- Volume sum × intent
- Volume sum × produkt
- CPC median × produkt (pokud data existuji)

**7.2 Top listy**
- TOP 100 podle volume
- TOP 100 podle CPC
- TOP 100 podle kombinovane hodnoty = `volume × CPC` (pattern z delonghi_2_mixery)
- TOP 100 podle volume v kategorii produkt (top 10 per produkt)

**7.3 Ranking distribuce**
Pivot: ranking bucket × segment:
- top_3 (pozice 1-3)
- top_10 (pozice 4-10)
- pos_11_20 (pozice 11-20)
- pos_21_50 (pozice 21-50)
- pos_51_100 (pozice 51-100)
- nerankuje (position_client prazdne)

**7.4 Basic grafy**
Nativni xlsxwriter grafy embedded v XLSX:
- Histogram volume (bucketed)
- Pie intent
- Bar funnel
- Heatmap produkt × intent (count)
- Bar ranking distribuce (vs. best competitor)

**7.5 Coverage check**
Summary metrics:
- Kolik % KW ma pozici klienta
- Kolik % KW ma priority=money_keyword
- Kolik % KW ma neprazdny produkt
- Median volume, median CPC
- Intent split (% TRANS, COMM, INFO, NAV)

CHECKPOINT: "Dashboard hotovy. Top metrika: X KW, median volume Y, intent split: Z. Pokracujeme fazi 8?"

### Input / Output

- **Input:** `data/interim/keywords_enriched.csv`
- **Output:** `data/output/07_dashboard.xlsx` (multi-sheet):
  - `Overview` — key metrics summary
  - `Dist_Intent_Funnel`, `Dist_Produkt_Brand`, `Dist_Priority` — pivots
  - `Top_Volume`, `Top_CPC`, `Top_Value` — top listy
  - `Top_Per_Produkt` — top 10 KW per produkt
  - `Ranking_Distribution` — pivot ranking bucket × segment
  - `Charts` — nativni xlsxwriter grafy
- **Sloupce pridane do main datasetu:** ZADNE. Dashboard je read-only.
- **Run mode:** auto

---

## Faze 8: Competitive Gap

### Ucel
Diagnosticka vrstva. Odpovida na otazku **"Kde mame mezeru proti trhu a jakeho typu"**.

Akcni vystup (gap_type + recommended_action), ale jeste ne finalni prioritizace. Faze 8 NESMI obsahovat:
- Finalni priority P1-P4 (to je faze 9)
- Content briefy (to je faze 10)
- Linkbuilding prospect list (out of scope)

### Jak
Python skript `src/gap.py`. Pure rule-based — zadne AI, deterministicke. Cte `keywords_enriched.csv`, zapisuje `keywords_with_gap.csv` + `08_gap.xlsx`.

### Vazba na params.yaml
- `gap.quick_win_position_range: [4, 20]`
- `gap.close_gap_position_range: [21, 50]`
- `gap.quick_win_max_kd: 40`
- `gap.competitor_top_threshold: 3`

### Kroky

**8.1 Gap typology (ordered decision tree)**

Pro kazdy KW klasifikuj do gap_type podle nasledujicich pravidel v poradi:

1. **defended** — `position_client` je v top 3 → klient uz rankuje dobre, monitor only
2. **quick_win** — `position_client` v [4, 20] AND `best_competitor_position` ≤ 3 AND `kd` ≤ 40
3. **close_gap** — `position_client` v [21, 50] AND `best_competitor_position` ≤ 10
4. **content_gap** — `position_client` je prazdny (nerankuje) AND `best_competitor_position` ≤ 10
5. **no_opportunity** — zadna z vyse + (nikdo nerankuje top 10 OR klient i konkurenti top 3 s KD > 70)
6. **monitor** — default fallback (ostatni pripady)

**8.2 Recommended action mapping**

| gap_type | recommended_action |
|----------|---------------------|
| quick_win | `optimize_existing` |
| close_gap | `optimize_existing` nebo `boost_authority` (podle velikosti rozdilu) |
| content_gap | `create_new_page` |
| defended | `monitor` |
| no_opportunity | `skip` |
| monitor | `monitor` |

**8.3 Gap sizing (traffic_potential)**

Odhad ztraceneho trafficu = `volume × (CTR_best_competitor − CTR_client)`:
- CTR per pozice z `params.yaml: scoring.ctr_estimates`
- Pokud klient nerankuje → `CTR_client = 0`
- Vysledek v `gap_traffic_potential` (celo cislo, navstevy/mesic)

**8.4 Validace**
- FLAG: `quick_win` s KD > 40 → review threshold
- FLAG: `content_gap` s volume < 100 → marginalni, zvaz priority
- FLAG: `best_competitor_position` chybí ale `gap_type != monitor` → chybejici SERP data

CHECKPOINT: "Gap hotovy. Quick wins: X, Close gaps: Y, Content gaps: Z, Defended: W. Pokracujeme fazi 9?"

### Input / Output

- **Input:** `data/interim/keywords_enriched.csv`
- **Output:** `data/output/08_gap.xlsx`:
  - `All_Gaps` — master list s gap_type + action + sizing
  - `Quick_Wins` — sortovano DESC podle gap_traffic_potential
  - `Close_Gaps`
  - `Content_Gaps`
  - `Defended` — monitoring subset
  - `Gap_Summary` — pivot gap_type × segment (count + sum volume)
- **Sloupce pridane do main datasetu (`keywords_with_gap.csv`):** `gap_type`, `recommended_action`, `gap_traffic_potential`
- **Run mode:** auto

---

## Faze 9: Scoring

### Ucel
Prioritizacni vrstva. Odpovida na otazku **"Co resit jako prvni"**.

Jediny oficialni prioritizacni mechanismus ve frameworku. Faze 9 NESMI obsahovat:
- URL mapping (to je faze 10)
- Content typ jako hlavni vystup
- Dashboardove grafy jako nahrada skore
- Black-box AI skore — model MUSI byt rozlozitelny

### Jak
Python skript `src/scoring.py`. Deterministicke — zadne AI, transparentni komponenty. Cte `keywords_with_gap.csv`, zapisuje `keywords_scored.csv` + `09_scoring.xlsx`.

### Scoring model

```
priority_score = (
    business_value × 0.40 +
    ranking_probability × 0.35 +
    traffic_potential × 0.25
)
```

Vsechny komponenty jsou 0-10. Vahy konfigurovatelne v `params.yaml: scoring.weights`.

### Komponenty

**9.1 business_value (0-10)**
- Z `intent` a `priority`:
  - `TRANS` = 10
  - `COMM` = 7
  - `INFO` = 3
  - `NAV` = 1
- Bonus `+scoring.money_keyword_bonus` (default 2.0) pokud `priority = money_keyword`
- Clamp na max 10

**9.2 ranking_probability (0-10)**
Funkce(KD, position_client, gap_type):
- base = `10 − (kd / 10)` (pokud KD neni, default 5)
- position bonus:
  - position_client v top 10 → +2
  - position_client v 11-20 → +1
  - position_client 21+ nebo prazdne → +0
- **gap_type modifier** (z `params.yaml: scoring.gap_modifier`):
  - quick_win = +1.5
  - close_gap = +0.5
  - content_gap = 0
  - no_opportunity = −2
- Clamp [0, 10]

**9.3 traffic_potential (0-10)**
- raw = `log10(volume + 1) × CTR_estimate(position_client)`
- CTR z `params.yaml: scoring.ctr_estimates` (default 0.005 pro nerankujici)
- Pro nerankujici: pouzij CTR pozice 10 × gap_discount (0.5) — odhad po optimalizaci
- Normalizace na 0-10 pres min-max per dataset (aby skore bylo srovnatelne napric KW)

**9.4 priority_score a priority_tier**

- `priority_score` = vazeny soucet (float 0-10)
- `priority_tier` podle `params.yaml: scoring.tier_thresholds`:
  - **P1** (≥ 7.5) — immediate action
  - **P2** (5.0-7.5) — next quarter
  - **P3** (2.5-5.0) — nice to have
  - **P4** (< 2.5) — ignore / monitor

**9.5 scoring_reason (audit trail)**

Kazdy KW ma human-readable breakdown:
```
"BV=9.0 (TRANS + money_keyword) | RP=6.5 (KD=40, pos=15, quick_win +1.5) | TP=4.2 (vol=1200, CTR=0.07) = 6.94 (P2)"
```

**9.6 Validace**
- FLAG: P1 s gap_type=no_opportunity → konflikt (high score ale nemame sanci)
- FLAG: P4 s money_keyword flag → review (nejspis chyba v scoring nebo kategorizaci)
- FLAG: priority_score chybi (null komponenta) → data quality issue

CHECKPOINT: "Scoring hotovy. P1: X, P2: Y, P3: Z, P4: W. Top 5 P1 KW: [seznam]. Pokracujeme fazi 10 nebo rovnou 11?"

### Input / Output

- **Input:** `data/interim/keywords_with_gap.csv`
- **Output:** `data/output/09_scoring.xlsx`:
  - `Scored` — full dataset, sortovane podle priority_score DESC
  - `Score_Breakdown` — per-KW: business_value, ranking_probability, traffic_potential komponenty
  - `P1_Actionable` — jen P1 subset (okamzita akce)
  - `Tier_Summary` — count per tier × segment
  - `Methodology` — vysvetleni modelu a vah (pro audit)
- **Sloupce pridane do main datasetu (`keywords_scored.csv`):** `business_value`, `ranking_probability`, `traffic_potential`, `priority_score`, `priority_tier`, `scoring_reason`
- **Run mode:** auto

---

## Faze 10: Content Mapping (optional)

### Ucel
Akcni vrstva. Odpovida na otazku **"Kam to patri a jaky typ stranky to ma byt"**.

Volitelna faze. Faze 10 NESMI obsahovat:
- Detailni copy briefy (out of scope — to je content strategy)
- Editorial kalendar
- Linkbuilding prospect list
- Cely dataset bez filtru (jen P1-P2, zbytek do archive sheetu)

### Kdy spustit

- **ANO** — klient ocekava konkretni URL plan (LLENTAB, Delonghi kategorie)
- **NE** — klient si mappuje sam (mBank styl), nebo framework jeste nema klientskou URL strukturu

Rizeno v `params.yaml: content_mapping.enabled`. Default `false`.

### Jak
Python skript `src/content_mapping.py`. Hybrid rule-based + AI — AI navrhuje content_type pri neurcitosti, uzivatel validuje.

### Kroky

**10.1 Cluster → URL candidate**
- Pokud faze 6 bezela → pouzij `cluster_id` jako URL skupinu
- Jinak: skupinuj podle `produkt + intent` kombinace
- Kazda skupina = 1 navrzena URL

**10.2 URL status detection**

Pro kazdy KW urci stav URL:
- **existing** — klient uz ma rankujici URL (`position_client` existuje) v top 50
- **new** — zadna URL neexistuje nebo rankuje > pozice 50
- **merge** — 2+ existujicich URL pokryva stejny cluster (konsolidovat)
- **update** — URL existuje (top 20), ale pokryva jen cast clusteru (mene KW nez cluster obsahuje)

**10.3 Content type assignment**

Z intent + typ (z faze 5):
- TRANS + produkt → `product` / `category`
- TRANS + porovnani (COMM signaly) → `comparison_lp`
- COMM → `guide` / `comparison`
- INFO → `blog` / `faq`
- NAV + brand → `landing`

Konfigurovatelne v `params.yaml: content_mapping.content_types`.

**10.4 Primary + secondary keywords**

Group by cluster:
- `primary_kw` = KW s nejvyssim `priority_score` v clusteru
- `secondary_keywords` = ostatni KW v clusteru (pipe-separated)
- `is_primary_kw` = True/False flag

**10.5 AI validation (optional)**
- Pro low-confidence content_type (neklare intent) → AI doplni suggestion
- User review checkpointu pred finalizaci

CHECKPOINT: "Content Mapping: X new pages, Y optimize_existing, Z merge_candidates. Top 10 new pages: [seznam]. Ok?"

### Input / Output

- **Input:** `data/interim/keywords_scored.csv`
- **Output:** `data/output/10_content_mapping.xlsx`:
  - `URL_Plan` — 1 radek = 1 cilova URL (primary KW + secondary KW list + content_type)
  - `New_Pages` — status=new, sortovano DESC podle sum(priority_score)
  - `Optimize_Existing` — status=existing
  - `Merge_Candidates` — status=merge
  - `Update_Existing` — status=update
- **Sloupce pridane do main datasetu (`keywords_mapped.csv`):** `target_url`, `url_status`, `content_type`, `primary_cluster`, `is_primary_kw`, `secondary_keywords`
- **Run mode:** interactive (AI + user review URL strategy)

---

## Faze 11: Export & Deliverables

### Ucel
Finalni klientsky package. Sloucenin internich artefaktu do prezentovatelneho Excelu + executive summary. Toto je fáze, ktera v realnych projektech chybela — mıśila se s dashboardem.

### Jak
Python skript `src/export.py`. Cte vsechny vystupy fazi 7-10, konsoliduje do 1 klientskeho XLSX. Optional Google Sheets sync on-demand.

### Vazba na params.yaml
- `export.client_name` — pouzito v nazvu finalniho XLSX
- `export.include_methodology_sheet` — pridat list s vysvetlenim metodiky
- `export.per_segment_sheets` — jeden list per produkt/segment
- `export.google_sheets_export` — true = sync na konci
- `export.google_sheets_id` — target spreadsheet ID (pokud export do Sheets)

### Kroky

**11.1 Konsolidace**
- Nacti vsechny `data/output/07_*.xlsx` az `10_*.xlsx`
- Nacti `data/interim/keywords_scored.csv` (nebo `keywords_mapped.csv` pokud faze 10 bezela)
- Vyber relevantni data pro klienta (skryt audit/debug sloupce)

**11.2 Executive summary sheet**
- Top metriky: celkovy pocet KW, total volume, P1 count, quick wins count, content gaps count
- Top 20 P1 KW se scoring_reason
- Top 5 quick wins (nejvyssi gap_traffic_potential)
- Top 5 content gaps (novy obsah s nejvyssim skore)
- Key recommendations (3-5 bulletu, generovane AI ze souhrnu)

**11.3 Per-segment sheety**
Pokud `export.per_segment_sheets: true`:
- Jeden list per unique hodnota `produkt` (nebo `typ`)
- Obsahuje filtered subset datasetu

**11.4 Action plan sheet**
Serazene podle priority × gap_type:
1. P1 + quick_win → top priority
2. P1 + content_gap → create new
3. P2 + quick_win → next sprint
4. P2 + content_gap, close_gap → long-term
5. P3/P4 → archive

**11.5 Methodology sheet (optional)**
Pokud `export.include_methodology_sheet: true`:
- Vysvetleni vah scoringu, gap typology, content_type mapping
- Pocet zdroju v seed, dedup ratio, rule coverage v kategorizaci
- Transparentnost pro klienta

**11.6 Google Sheets export (optional)**
Pokud `export.google_sheets_export: true`:
- `python src/export.py --to-sheets <spreadsheet_id>`
- Pouziva `google_sheets_helper.py` (pattern z Delonghi/mBank)
- **DULEZITE:** Sheets sync je on-demand, NE automaticky po kazde fazi (jinak prepisuje klientske upravy)

CHECKPOINT: "Export hotovy: `11_FINAL_<client>_<date>.xlsx` (X sheetu, Y MB). Chces sync na Google Sheets (ano/ne)?"

### Input / Output

- **Input:** `data/output/07_*.xlsx` az `10_*.xlsx` + `data/interim/keywords_scored.csv`
- **Output:** `data/output/11_FINAL_<client>_<date>.xlsx`:
  - `01_Executive_Summary` — klientske top metriky + doporuceni
  - `02_Action_Plan` — P1 + quick wins, serazene pro realizaci
  - `03_Full_Keyword_List` — kompletni dataset (vsechny sloupce, bez audit trail)
  - `04_Per_Segment_<seg>` — jeden list per produkt/segment (pokud zapnuto)
  - `05_Quick_Wins` — samostatny prehled (z faze 8)
  - `06_Content_Gaps` — samostatny prehled
  - `07_Content_Plan` — URL plan (pokud faze 10 bezela)
  - `08_Methodology` — transparentnost (pokud zapnuto)
- **Run mode:** interactive (user potvrdi klient name, output path, zahrnute sheety)

### Sample check pred predanim klientovi

Otevri finalni XLSX a zkontroluj:
- [ ] Executive summary obsahuje konkretni cisla (ne placeholders)
- [ ] Top 20 P1 KW rucne projite — davaji smysl?
- [ ] Action plan ma jasne priority (P1 prvni, P4 archive)
- [ ] Per-segment sheety jsou kompletni
- [ ] Zadne `NaN`, `None`, `null` values v klientskych sheetech

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
| 6.5 SERP Enrichment | auto | ANO | Deterministic API calls |
| 7 Dashboard | auto | ANO | Jen agregace, zadne rozhodovani |
| 8 Competitive Gap | auto | ANO | Pure rule-based |
| 9 Scoring | auto | ANO | Deterministic model |
| 10 Content Mapping | interactive | NE | AI + user review URL strategy |
| 11 Export | interactive | NE | User potvrzuje klient name, output path, sheety |

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
6. **AI na vsech KW** - rule-based je pre-annotation (konzistence), AI je autorita. Bezi na ANO/NE/MOZNA, ne jen na MOZNA. Cena je zanedbatelna oproti kvalite vysledku.
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
