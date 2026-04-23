# AKW Framework — Known Issues

## OPEN

### ISSUE-001: Categorization full run skips few-shot review
**Date:** 2026-04-01
**Phase:** 5 (Categorization)
**Severity:** HIGH

**Problem:** `python src/categorization.py` runs rule-based + AI in one go. No opportunity to review/approve few-shot examples before AI gets them. User should be able to check what examples AI will use.

**Real case:** Llentab project — test mode (30 KW, 80% rule-based) looked fine, but full run was launched without reviewing the 20 few-shot examples that would guide AI on 261 low-confidence keywords.

**Fix:** Split into two commands:
```bash
python src/categorization.py --rule-only     # step 1: rule-based only, save result + show few-shot
# user reviews few-shot + rule-based results, adjusts params.yaml
python src/categorization.py --continue-ai   # step 2: AI on low-confidence only
```

**Status:** FIXED — `--rule-only` and `--continue-ai` flags added

---

### ISSUE-002: Relevance test mode originally skipped AI
**Date:** 2026-04-01
**Phase:** 4 (Relevance)
**Severity:** MEDIUM

**Problem:** Original test mode (--test 50) only ran rule-based, skipping AI. Made test useless for validating AI quality.

**Fix:** DONE — test mode now runs rule-based + AI + reasoning column. Both phases 4 and 5.

**Status:** FIXED

---

### ISSUE-005: Always test stěžejní fáze on 25 KW sample before full run
**Date:** 2026-04-19
**Phase:** 3, 4, 5 (všechny stěžejní)
**Severity:** HIGH

**Problem:** Stěžejní fáze (Cleaning, Relevance, Kategorizace) se spouští rovnou na plném datasetu. U 44k KW = drahé (AI volání) + riziko, že rule-based/AI logika neodpovídá záměru klienta. Feedback přijde až po plném runu.

**Real case:** form_factory — 44 000 KW po namnožení. Logika cleaning/relevance se musí ověřit na malém vzorku dříve, než se pustí celé.

**Fix:** Framework pravidlo — každá stěžejní fáze MUSÍ mít default workflow:
1. `--sample 25` (stratified sample — různé typy KW)
2. User review výstupu + feedback
3. Úprava pravidel (`params.yaml`, patterns, few-shot)
4. Až pak `--full` na celý dataset

Žádný full run bez explicitního user approval po sample testu.

**Navazuje na:** `feedback_test_mode_review.md` v auto-memory (už aktivní jako user preference, teď kodifikováno do frameworku).

**Status:** OPEN

---

### ISSUE-004: Swap order of Fáze 2 (EDA) and Fáze 3 (Cleaning)
**Date:** 2026-04-19
**Phase:** 2, 3
**Severity:** MEDIUM

**Problem:** Při velkém objemu dat (např. 44 000 KW z namnožení) nemá smysl dělat EDA před cleaningem — analyzujeme duplicity, šum, varianty s/bez diakritiky. EDA by se měla dělat až na vyčištěných datech pro reálný insight.

**Real case:** form_factory projekt — 44 000 KW po namnožení. EDA před cleaningem = plýtvání času a zkreslené histogramy.

**Fix:** Prohodit pořadí fází:
- Fáze 1: Seed Expansion
- Fáze 2: **Cleaning** (bylo 3)
- Fáze 3: **EDA** (bylo 2)
- Fáze 4+: beze změny

Aktualizovat: `KEYWORD_RESEARCH_FRAMEWORK.md`, `CLAUDE.md` (framework), přejmenovat `akw_framework_faze_2.md` ↔ `akw_framework_faze_3.md`.

**Status:** OPEN

---

### ISSUE-003: High-volume MOZNA retry was 1-by-1
**Date:** 2026-04-01
**Phase:** 4 (Relevance)
**Severity:** LOW

**Problem:** Keywords with volume > 500 that stayed MOZNA after AI were retried one-by-one (expensive).

**Fix:** DONE — now batched.

**Status:** FIXED

---

### ISSUE-006: Fáze 7-11 byly "TBD" bez specifikace
**Date:** 2026-04-23
**Phase:** 7, 8, 9, 10, 11 (+ nová 6.5)
**Severity:** HIGH

**Problem:** Fáze 7 (Dashboard), 8 (Competitive Gap), 9 (Scoring), 10 (Content Mapping), 11 (Export) byly v `/akw` skillu jen `> Zatim nespecifikovano`. Reálné projekty je řešily ad-hoc ve sdíleném Google Sheetu, kde se vrstvy slévaly (dashboard + scoring + content mapping v jednom listu). Důsledky:

- duplikovaná logika napříč projekty (každý měl vlastní scoring vzorec — `SV × CPC × 100` v delonghi_2_mixery vs. P1-P4 v CPP)
- chybějící audit trail (proč je KW priorita A?)
- scope creep v klientském deliverable (grafy se mísily s doporučeními)

**Real case:** `delonghi_2_mixery` projekt — všech 17 Google Sheets listů v jednom souboru, implicitní scoring ve filteru, žádný oficiální prioritizační mechanismus. CPP obdobně.

**Fix:**

1. **Přidána fáze 6.5 SERP Enrichment** — explicitní krok pro pozice klienta + konkurence + KD + SERP features (nezbytné pro fáze 7-9, které to používají).
2. **Fáze 7 Dashboard** — pure deskriptivní vrstva, NESMÍ obsahovat priority/doporučení. Output: `07_dashboard.xlsx` s pivoty a embedded grafy.
3. **Fáze 8 Competitive Gap** — rule-based gap typology (defended, quick_win, close_gap, content_gap, no_opportunity, monitor) + recommended_action + gap_traffic_potential.
4. **Fáze 9 Scoring** — jediný oficiální prioritizační mechanismus. Transparentní komponenty (business_value + ranking_probability + traffic_potential, váhy konfigurovatelné). `ranking_probability` konzumuje `gap_type` jako modifier. `scoring_reason` sloupec s human-readable breakdown pro audit.
5. **Fáze 10 Content Mapping (optional)** — KW → URL → content_type. Řízeno `params.yaml: content_mapping.enabled`.
6. **Fáze 11 Export & Deliverables** — samostatná fáze (oddělená od dashboardu), konsolidace interních artefaktů do klientského XLSX s executive summary, action plan, methodology sheet. Google Sheets sync on-demand.

**Architektonická rozhodnutí:**
- XLSX primární output, Google Sheets on-demand sync (ne automatický — jinak přepisuje klientské úpravy)
- Feed-forward data flow (6.5 → 7 → 8 → 9 → 10 → 11), každá fáze přidává sloupce
- Separation of concerns: každá fáze má explicit "NESMÍ obsahovat" seznam

**Updated dokumenty:**
- `/Users/admin/.claude/commands/akw.md` — kompletní specifikace fází 6.5-11
- `docs/data-contracts.md` — schema + enum hodnoty pro nové sloupce (gap_type, priority_tier, url_status, content_type, ranking_bucket)
- `docs/acceptance-criteria.md` — klíčové metriky + done checklist + sample check pro každou novou fázi

**Implementace scriptů:** NENÍ součástí tohoto fixu — Python scripty (`src/serp_enrichment.py`, `dashboard.py`, `gap.py`, `scoring.py`, `content_mapping.py`, `export.py`) se implementují later na konkrétním projektu. Referenční kód pro reuse:
- `Delonghi/src/google_sheets_helper.py` → fáze 11 `--to-sheets` flag
- `mbank/src/relevance_analyzer.py` → vzor pro ordered decision tree ve fázi 8
- `cpp/` quick_wins pattern → fáze 8 layout
- `llentab/notebooks/01_eda_executed.ipynb` → vzor grafů pro fázi 7
- `delonghi_2_mixery/` → vzor pro fázi 11 17-sheet Excel

**Status:** FIXED — specifikace doplněna, implementace bude na nejbližším projektu (doporučen `LLENTAB` — má kompletní SERP data pro smoke test fází 6.5-9).
