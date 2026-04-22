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
