# CURRENT.md

Tento dokument slúži ako snapshot aktuálneho stavu projektu so všetkými detailmi potrebnými na pochopenie kde projekt je. Nezaznamenávaj tu žiadne lessons learned — tie patria do ISSUES.md.

**Posledná aktualizácia:** 2026-04-23

---

## 📖 Ako používať tento súbor

**CURRENT.md je navigačný dokument, nie úložisko detailov.**

Prečítaj tento súbor PRVÝ pred tým než začneš pracovať na projekte.

### ✅ AKTUALIZUJ keď:
- Dokončíš fázu frameworku (pridaj do "Čo funguje" s dátumom)
- Zmeníš štruktúru projektu alebo pridáš novú fázu
- Pridáš / zmeníš ADR
- Implementuješ TODO položku (atomic write, params_hash, --dry-run v relevance)

### ❌ NEPRIDÁVAJ:
- Detailné popisy fáz → patria do CLAUDE.md a /akw skillu
- Datové schémy → patria do `docs/data-contracts.md`
- Architektonické rozhodnutia → patria do `docs/decisions/`
- Known issues a bugy → patria do `ISSUES.md`

---

## 📋 Prehľad projektu

**Názov:** AKW Framework — Analýza klíčových slov
**Popis:** Framework pro opakovanou keyword research analýzu pro klienty (e-shopy, služby, weby). 12 fází od sběru dat po finální deliverable.
**Stav:** Aktivní vývoj — fáze 0-6 implementované, 7-11 ještě ne
**Verze:** v1.1 (viz CLAUDE.md)
**Repo:** https://github.com/kovalcikjan/akw-framework (private)

---

## 🏗️ Tech Stack

- **Jazyk:** Python 3.11+
- **Knihovny:** pandas, openpyxl, pyyaml, tqdm, dotenv
- **AI providery:** OpenAI (GPT-4o-mini, GPT-4o), Anthropic (Claude Sonnet 4.5), Google (Gemini 2.0 Flash)
- **Datové formáty:** CSV (pipeline), XLSX (fáze 3 audit), Google Sheets (finální klientský deliverable, mimo skripty)
- **Verze control:** Git + GitHub
- **Vývojové prostředí:** Claude Code + /akw skill

---

## 📁 Štruktúra projektu

```
akw-framework/
├── CLAUDE.md                    # Plná framework specifikace (952 řádků, mirror skillu)
├── CURRENT.md                   # Tento soubor
├── ISSUES.md                    # Known issues (5 total, 2 open, 3 fixed)
├── akw_framework_faze_8.md      # Legacy dokument (TODO: migrovat nebo smazat)
├── README.md                    # NEEXISTUJE (TODO)
├── pyproject.toml               # NEEXISTUJE (TODO pro onboarding 10 kolegů)
├── .gitignore
│
├── docs/                        # Reference dokumentace (AS IS)
│   ├── README.md                # Rozcestník
│   ├── data-contracts.md        # Datové schéma mezi fázemi
│   ├── acceptance-criteria.md   # Kdy je fáze "hotová" (WIP — čeká na tiered rewrite)
│   └── decisions/               # 7 ADR
│       ├── 001-static-diacritics-map.md
│       ├── 002-batch-size-30-50.md
│       ├── 003-xlsx-primary-output.md
│       ├── 004-rule-based-before-ai.md
│       ├── 005-checkpoint-resume-pattern.md
│       ├── 006-few-shot-examples.md
│       └── 007-test-mode-before-full-run.md
│
├── src/                         # Python skripty pro fáze 1C-6
│   ├── .env.template            # Šablona API klíčů
│   ├── ai_client.py             # Sdílený AI client (OpenAI/Anthropic/Gemini) — 144 ř
│   ├── merge_sources.py         # Fáze 1C: sloučení zdrojů — 269 ř
│   ├── eda.py                   # Fáze 2: EDA utils — 397 ř
│   ├── eda_notebook_generator.py# Fáze 2: Jupyter generator — 595 ř
│   ├── cleaning.py              # Fáze 3: čištění + dedup — 517 ř
│   ├── relevance.py             # Fáze 4: ANO/NE/MOZNA klasifikace — 634 ř
│   ├── categorization.py        # Fáze 5: typ/produkt/intent/funnel — 749 ř
│   └── serp_clustering.py       # Fáze 6: SERP clustering — 279 ř
│
└── tasks/                       # TO BE / changes (prázdné, placeholder)
    └── .gitkeep
```

**Kľúčové súbory:**
- `CLAUDE.md` — plná operační specifikace frameworku, zrcadlí `/akw` skill
- `docs/data-contracts.md` — zdroj pravdy pro datové schéma (ověřeno proti llentab projektu)
- `docs/decisions/` — hard-won rozhodnutí (proč diacritics map ne NFD, proč batch 30, proč XLSX v fázi 3, atd.)
- `ISSUES.md` — 5 known issues, workflow pro jejich tracking

---

## ✅ Čo funguje

### Implementované fáze (src/)

- [x] **Fáze 1C — Merge sources** (`merge_sources.py`) — sloučení souborů z data/raw/, initial dedup
- [x] **Fáze 2 — EDA** (`eda.py`, `eda_notebook_generator.py`) — Jupyter notebook s distribucí, outliers, n-gramy
- [x] **Fáze 3 — Cleaning + Dedup** (`cleaning.py`) — normalizace, static diacritics map, canonical scoring, XLSX multi-sheet audit
- [x] **Fáze 4 — Relevance** (`relevance.py`) — rule-based + AI (MOZNA), checkpoint/resume, exponential backoff, high-volume retry
- [x] **Fáze 5 — Kategorizace** (`categorization.py`) — rule-based + AI, few-shot, `--rule-only`/`--continue-ai` inspection workflow, 4-mode run (test/rule-only/continue-ai/full)
- [x] **Fáze 6 — SERP Clustering** (`serp_clustering.py`) — URL overlap clustering

### Infrastruktura

- [x] **Multi-model AI** — GPT-4o-mini (default), GPT-4o, Gemini 2.0 Flash, Claude Sonnet 4.5
- [x] **Checkpoint/resume pattern** — přerušené AI běhy pokračují místo restartu
- [x] **Test mode** — `--test N` na každém AI skriptu s reasoning sloupcem
- [x] **Iterativní testing** — `--test-round N` pro různé náhodné sady KW
- [x] **Rule-based před AI** — úspora API nákladů, transparentnost, audit trail
- [x] **params.yaml konfigurace** — per-project, schema v CLAUDE.md

### Dokumentace

- [x] **`docs/` struktura** (vytvořeno 2026-04-23)
- [x] **7 ADR** — static diacritics, batch size, XLSX output, rule-before-AI, checkpoint, few-shot, test mode
- [x] **`docs/data-contracts.md`** — ověřeno proti reálnému llentab projektu
- [x] **GitHub repo** — synced, 4 commity (initial, sync CLAUDE.md, add docs/, verify against llentab)

---

## 🚧 Rozpracované

- [ ] **`docs/acceptance-criteria.md`** — sepsané prvotní draft, ale čísla (dedup 10-30%, rule coverage 60%+) jsou moc aspirační. Čeká na **tiered rewrite** (ideal / akceptovatelné / signal)
- [ ] **Verifikace všech čísel proti více projektům** (zatím jen llentab; chybí mBank, DeLonghi, CPP, eVisions, svarecky, delonghi mixery)

---

## ❌ Ešte neimplementované

### Fáze 7-11 (bez kódu, jen koncept v CLAUDE.md)

- [ ] **Fáze 7 — Dashboard / Overview** — kontingenční tabulky, grafy, pivot analýzy
- [ ] **Fáze 8 — Competitive Gap** — quick wins, content gaps, pozice 4-20 kde konkurent top 3
- [ ] **Fáze 9 — Scoring** — weighted prioritizace (business × ranking × traffic), P1-P4 tiery
- [ ] **Fáze 10 — Content Mapping** — KW → URL → content type → owner
- [ ] **Fáze 11 — Validation + Export** — QA, finální Google Sheets deliverable, executive summary

### Infrastruktura TODO

- [ ] **`README.md`** — onboarding dokumentace pro nové uživatele (priorita pro 10 kolegů)
- [ ] **`pyproject.toml`** — pinned verze, `pip install -e .` workflow
- [ ] **Skill do repa** (`.claude/skills/akw/`) — aby si kolegové nemuseli instalovat ručně
- [ ] **Test project** (`examples/test_project/`) — sample setup pro 30-min run-through
- [ ] **`docs/troubleshooting.md`** — FAQ pro běžné chyby

### ADR TODO (flagged v současných ADRs)

- [ ] **Atomický zápis checkpointu** (ADR-005) — tempfile + rename pattern
- [ ] **`params_hash` kontrola v checkpointu** (ADR-005) — ochrana před mid-run change
- [ ] **`--dry-run` flag v `relevance.py`** (ADR-007) — zatím jen v categorization

### Známé issues (ISSUES.md)

- [ ] **ISSUE-003:** (OPEN) viz `ISSUES.md`
- [ ] **ISSUE-005:** (OPEN) Test stěžejní fáze na 25 KW sample před full run — WIP policy
- [x] ISSUE-001: Categorization full run skips few-shot review — **FIXED**
- [x] ISSUE-002: Relevance test mode originally skipped AI — **FIXED**
- [x] ISSUE-004: (FIXED)

---

## 🔧 Konfigurácia

### Environment variables (`src/.env.template` → kopie do `.env`)

```
OPENAI_API_KEY     # GPT-4o, GPT-4o-mini
ANTHROPIC_API_KEY  # Claude Sonnet 4.5, Haiku
GEMINI_API_KEY     # Gemini 2.0 Flash, 2.5 Pro
```

### Per-project `params.yaml`

Každý projekt má vlastní `params.yaml` v root složce projektu. Schema kompletně v `CLAUDE.md` sekci "Fáze 0 → params.yaml schema". Klíčové bloky:

- `client` — name, domain, language, country
- `cleaning` — word_order_dedup, volume_strategy (sum_volumes default)
- `filters` — min_search_volume (10), min_length, max_length, blacklist
- `relevance` — products, excluded, competitors, client_description
- `categorization` — typ, produkt (schema klienta), brand (own/competitor), specifikace
- `ai` — volitelný blok (default_model, batch_size=30, temperature, few_shot_count=20)
- `scoring` — money_threshold (default 20), weights, intent_scores
- `paths` — raw_data, interim, output

### Dôležité nastavenia

- **Default AI model:** `gpt-4o-mini` (levný, dostatečně přesný pro rule+AI hybrid)
- **Default batch size:** 30 KW per prompt (hardcoded fallback)
- **Default few-shot count:** 20 (stratifikované napříč 4 intent hodnotami)
- **Checkpoint cesty:** `<project_root>/checkpoint_relevance.json`, `<project_root>/checkpoint_categorization.json`
- **CSV encoding:** UTF-8 se signaturou BOM (`utf-8-sig`) pro Excel kompatibilitu

---

## 🚀 Ako spustiť

### Setup (jednorázově pro nový projekt)

```bash
# 1. Vytvořit projekt (z Claude Code se skillem /akw)
cd ~/Documents/Akws
claude
# v chatu: /akw → projde setup (brief → research → params.yaml)

# 2. Nebo ručně
mkdir novy_projekt && cd novy_projekt
python -m venv .venv && source .venv/bin/activate
pip install pandas openpyxl pyyaml openai anthropic google-generativeai tqdm python-dotenv
cp /Users/admin/Documents/Akws/Akw_framework/src/.env.template .env
# doplnit API klíče
```

### Workflow fází

```bash
# Fáze 1C — merge sources (auto)
python src/merge_sources.py

# Fáze 2 — EDA (auto)
python src/eda_notebook_generator.py

# Fáze 3 — cleaning (auto)
python src/cleaning.py

# Fáze 4 — relevance (interactive)
python src/relevance.py --test 50       # 1. test
# review, upravit params.yaml
python src/relevance.py                 # 2. full run

# Fáze 5 — kategorizace (interactive, 4 módy)
python src/categorization.py --test 20     # 1. test
python src/categorization.py --rule-only   # 2. rule-based + show few-shot
# review few-shot, upravit params.yaml
python src/categorization.py --continue-ai # 3. AI on low-confidence

# Fáze 6 — SERP clustering (optional, auto)
python src/serp_clustering.py
```

---

## 🌐 Produkčné URL

- **GitHub repo:** https://github.com/kovalcikjan/akw-framework (private)
- **Referenční projekty** (lokálně, ne v gitu): `/Users/admin/Documents/Akws/`
  - llentab/ — ověřovací projekt pro data-contracts (architektonické haly)
  - mbank/, Delonghi/, cpp/, evisions_akw/, aks_svarecky/, delonghi 2 mixery/
- **Skill:** `/akw` v `~/.claude/skills/akw/` (lokálně)

---

## 📝 Poznámky pre pokračovanie

### Dual source of truth pre framework spec

Framework specifikace žije **na dvou místech**:

1. **`/akw` skill** v `~/.claude/skills/akw/` — operační, načítá se při `/akw` volání
2. **`CLAUDE.md` v repu** — mirror skillu, slouží jako dokumentace + backup

Při změně spec musíš aktualizovat **obě** místa. Plánuje se zkrácení CLAUDE.md na ~60 řádků (orientační) + přesunout spec do skillu jako jediný zdroj, ale teprve po doplnění `docs/` struktury (aby bylo kam redirektovat).

### Next steps v pořadí priorit

1. **Dokončit `docs/acceptance-criteria.md` — tiered rewrite** (rozpracované, čeká na rozhodnutí přístupu)
2. **Oprava `brand_type` enum** v `data-contracts.md` — přidat `retail` hodnotu (nalezeno v llentab datech)
3. **Verifikace metrik proti mBank/DeLonghi/CPP** (zatím jen llentab)
4. **README.md + pyproject.toml + skill do repa** (pro onboarding 10 kolegů)
5. **Implementovat TODO z ADRs** (atomic write, params_hash, --dry-run v relevance)
6. **Zkrátit CLAUDE.md** na ~60 řádků (až po 1-4)

### Kontext pre ďalšieho vývojára/agenta

- Framework je v **R&D fázi** — workflow se často mění, ADRs zachycují rozhodnutí
- `llentab` projekt je referenční **edge case** (90% MOZNA po rule-based, AI v fázi 4 nikdy neběžela) — validuje že framework funguje i pro těžkou doménu
- `projects/` složka v repu **není** v gitu — obsahuje klientská data
- **10 kolegů** má framework používat (read-only) — priorita na onboarding dokumentaci

### Co NE dělat

- Neodstranit `akw_framework_faze_8.md` (legacy, ale obsahuje detailní Scoring detaily, které nikde jinde nejsou)
- Nekomitovat `projects/` — obsahuje klientská data
- Nekomitovat `.env` (v .gitignore, ale opatrně)
- Neměnit `data/raw/` v klientských projektech — je READONLY
