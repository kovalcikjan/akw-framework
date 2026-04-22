# CLAUDE.md - Keyword Research Framework

## O projektu

Tento projekt obsahuje **kompletní metodiku pro keyword research** - od sběru dat až po finální deliverables pro klienta.

Framework vznikl na základě analýzy 4 reálných projektů (Delonghi, mBank, CPP, Evisions) a je určen pro opakované použití na SEO/content projektech.

---

## Struktura frameworku

```
FÁZE 0: SETUP
└── Příprava projektu, struktura, config

FÁZE 1-6: DATA PREPARATION
├── 1-3: Sběr & čištění
│   ├── 1: Seed Expansion (sběr z více zdrojů)
│   ├── 2: EDA (porozumění datům)
│   └── 3: Cleaning ★ STĚŽEJNÍ
│
└── 4-6: Klasifikace & obohacení
    ├── 4: Relevance ★ STĚŽEJNÍ
    ├── 5: Kategorizace ★ STĚŽEJNÍ
    └── 6: SERP Clustering (optional)

FÁZE 7+: ANALYSIS & STRATEGY
├── Dashboard / Overview (TODO - grafy, kontingenční tabulky)
├── 7: Competitive Gap
├── 8: Scoring
├── 9: Content Mapping
└── 10: Export
```

---

## Soubory v projektu

| Soubor | Popis |
|--------|-------|
| `KEYWORD_RESEARCH_FRAMEWORK.md` | Hlavní přehled frameworku |
| `akw_framework_faze_0.md` | Project Setup - struktura, config, dependencies |
| `akw_framework_faze_1.md` | Seed Expansion - sběr KW z konkurentů, GSC |
| `akw_framework_faze_2.md` | EDA - distribuce, histogramy, outliers |
| `akw_framework_faze_3.md` | Cleaning + Dedup - normalizace, diakritika |
| `akw_framework_faze_4.md` | Relevance - ANO/NE/MOŽNÁ + důvod |
| `akw_framework_faze_5.md` | Kategorizace + Entity Mapping |
| `akw_framework_faze_6.md` | SERP Clustering (optional) |
| `akw_framework_faze_7.md` | Competitive Gap - quick wins |
| `akw_framework_faze_8.md` | Scoring - prioritizace |
| `akw_framework_faze_9.md` | Content Mapping - KW → URL |
| `akw_framework_faze_10.md` | Validation + Export |

---

## Stav rozpracování

| Fáze | Status | Poznámka |
|------|--------|----------|
| 0-6 | ✅ Hotovo | Společně projito a validováno |
| 7-10 | 📝 Draft | Existuje dokumentace, neprojito detailně |
| Dashboard | ❌ TODO | Přidat fázi pro grafy a pivoty |

---

## Stěžejní fáze (3, 4, 5)

Kvalita celého výstupu závisí primárně na těchto fázích:

1. **Fáze 3 - Cleaning**: Deduplikace, normalizace diakritiky
2. **Fáze 4 - Relevance**: Je keyword pro klienta? (ANO/NE/MOŽNÁ + důvod)
3. **Fáze 5 - Kategorizace**: Typ, produkt, brand, intent, funnel

Všechny používají pattern: **Rule-based + AI + Validace**

---

## Klíčové koncepty

### Money Keywords
Keywords označené v Fázi 5 jako `priority=money_keyword`:
- Intent: TRANS nebo COMM
- Volume > 500 nebo má produkt match
- Není konkurenční brand
- Jdou do SERP Clustering (Fáze 6)

### Intent → Funnel
| Intent | Funnel | Content |
|--------|--------|---------|
| INFO | TOFU | Blog, průvodce |
| COMM | MOFU | Porovnání, recenze |
| TRANS | BOFU | Produkt, kalkulačka |
| NAV | BRAND | Homepage, kontakt |

### Scoring Formula
```
PRIORITY_SCORE = (
    business_value × 0.40 +
    ranking_probability × 0.35 +
    traffic_potential × 0.25
)
```

---

## Jak používat framework

### Pro nový projekt:
1. Zkopírovat šablonu z Fáze 0
2. Upravit `params.yaml` pro klienta
3. Projít fáze 1-10 postupně

### Pro úpravu frameworku:
1. Editovat příslušný `akw_framework_faze_X.md`
2. Aktualizovat `KEYWORD_RESEARCH_FRAMEWORK.md` pokud se mění přehled
3. Commitnout změny

---

## TODO

- [ ] Přidat fázi Dashboard/Overview (grafy, pivoty) mezi Fázi 6 a 7
- [ ] Detailně projít fáze 7-10
- [ ] Vytvořit reusable šablonu projektu (template folder)
- [ ] Dopsat Python moduly pro src/

---

## Příklad procesu (Claude Code)

### Situace
Nový klient **Pojišťovna ABC** - keyword research pro redesign webu.

### 1. Setup
```
cd ~/Documents/Akws/projects
mkdir pojistovna_abc && cd pojistovna_abc
claude

> "Připrav projekt pro keyword research podle frameworku
   /Users/admin/Documents/Akws/Akw_framework"
```
Claude Code vytvoří strukturu, zkopíruje šablony, inicializuje git.

### 2. Konfigurace
```
> "Uprav params.yaml pro klienta Pojišťovna ABC:
   - domain: pojistovnabc.cz
   - produkty: povinné ručení, havarijní, cestovní
   - konkurenti: allianz, generali, direct
   - excluded: životní pojištění, penze"
```

### 3. Sběr dat (Fáze 1)
```
> "Stáhni keywords pro pojistovnabc.cz a konkurenty z Ahrefs"
> "Nahraj GSC export a ulož do data/raw/"
```

### 4. EDA (Fáze 2)
```
> "Udělej EDA analýzu - distribuce volume, top keywords"
```

### 5. Cleaning (Fáze 3) ★
```
> "Vyčisti data podle Fáze 3 - exact dedup, diacritics dedup"
```
Výstup: "5234 → 3650 keywords (30% duplicit)"

### 6. Relevance (Fáze 4) ★
```
> "Projdi relevanci - ANO/NE/MOŽNÁ podle params.yaml"
> "Ukaž mi keywords označené jako MOŽNÁ"
> "Tyto označ jako ANO: [seznam]"
```
Výstup: "3650 → 2100 relevantních (58%)"

### 7. Kategorizace (Fáze 5) ★
```
> "Kategorizuj keywords - typ, produkt, intent, funnel"
> "Exportuj money keywords pro SERP clustering"
```

### 8. SERP Clustering (Fáze 6) - optional
```
> "Udělej SERP clustering pro money keywords"
```
Výstup: "180 money KW → 35 clusterů"

### 9. Analysis (Fáze 7-10)
```
> "Najdi quick wins - konkurent top 3, my pozice 4-20"
> "Vypočítej priority score"
> "Namapuj keywords na URL strukturu"
> "Vytvoř finální Excel pro klienta"
```

### 10. Finish
```
> "Ukaž souhrn projektu"
> "Commitni změny"
```

### Typické prompty

| Situace | Prompt |
|---------|--------|
| Review | "Ukaž sample 20 TRANS keywords" |
| Debug | "Proč je 'pojištění auta' označené jako INFO?" |
| Úprava | "Přidej 'srovnání' do COMM patterns" |
| Export | "Exportuj P1 keywords do CSV" |

---

## Historie

- **2026-02-26**: Vytvořen framework v1.1
  - Reorganizace fází (Relevance=4, Kategorizace=5, SERP=6)
  - Přidán money_keyword flag
  - Označeny stěžejní fáze (3, 4, 5)

---

*Framework version: 1.1*
