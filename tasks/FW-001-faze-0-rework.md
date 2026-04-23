# FW-001: Fáze 0 Rework — Iterativní Brief + In-Flow Research

**Status:** PROPOSED
**Autor:** Jan Kovalčík
**Datum:** 2026-04-23
**Scope:** `/akw` skill (primární) + `.claude/skills/akw/SKILL.md` v repo (mirror)

---

## 1. Context

### Proč tento rework

Fáze 0 (Project Setup) má dnes 5 volných otázek v briefu, research probíhá mimo Claude Code (Claude Desktop s web search), user ručně kopíruje výsledky zpět. Audit (chat 2026-04-23) identifikoval tyto problémy:

- **Brief není strukturovaný** — AI se ptá povrchně, kritické info (deadline, očekávaný počet KW, explicit out-of-scope, review owner) chybí
- **Research externí** — user přepíná mezi nástroji, ztrácí flow, nemá traceability
- **Research ad-hoc** — každý projekt vrací jinou strukturu, nelze validovat kompletnost
- **params.yaml je black box** — AI generuje hodnoty bez vysvětlení zdroje
- **Chybí acceptance criteria pro Fázi 0** — fáze 1-6 je mají, Fáze 0 ne

### Intended outcome

Fáze 0 produkuje **kompletní popis projektu** který:
1. Zachytí všechny povinné parametry bez dodatečných otázek později
2. Má plně auditovatelný research (5 standardních sekcí)
3. Obsahuje `params.yaml` s traceability (odkud se hodnota vzala)
4. Běží celá v Claude Code (bez přepínání nástrojů)

### Out of scope (této iterace)

- 0.4 (Project Create — sanity check, decision log, scope/timeline dokumenty) → **FW-002**
- Acceptance criteria pro Fázi 0 v `docs/acceptance-criteria.md` → **FW-003**
- Python tooling pro Fázi 0 (např. interaktivní brief CLI) → neplánováno

---

## 2. Current State

Zdroj: `/Users/admin/.clause/commands/akw.md` (řádky 56-134).

```
0.1  BRIEF         — 5 volných otázek najednou
0.2  RESEARCH      — AI vygeneruje copy-paste prompt pro Claude Desktop
0.3  USER VRACÍ    — user kopíruje výsledek zpět do Claude Code
0.4  PARAMS.YAML   — AI generuje z brief+research (bez traceability)
0.5  PROJECT       — vytvoří adresář + CLAUDE.md + soubory
```

4 checkpointy: po 0.1, po 0.2, po 0.4, po 0.5.

---

## 3. Proposed Changes

Nová struktura (po rozhodnutích z chatu):

```
0.1  BRIEF         — 13 polí, otázky POSTUPNĚ po jedné
0.2  RESEARCH      — iterativní v Claude Code, AI se PTÁ během research
0.3  PARAMS.YAML   — generování s inline traceability komentáři
```

0.4 zatím TBD (FW-002).

---

### 3.1 BRIEF — postupné otázky

**Mechanismus:** AI klade otázky JEDNU PO DRUHÉ. Po každé odpovědi potvrdí, ukáže progress (např. "3/10"), a pokračuje. Pokud je odpověď nejasná, AI okamžitě zpřesňuje.

**Pole (povinné 1-10, volitelné 11-13):**

| # | Pole | Typ | Příklad otázky | Validace |
|---|------|-----|----------------|----------|
| 1 | `client_name` | str | "Jak se jmenuje klient?" | Ne-prázdný |
| 2 | `domain` | str | "Jaká je doména?" | Obsahuje `.` |
| 3 | `languages` | list | "Jaký jazyk? CS / SK / oboje?" | ≥1 z [cs, sk, en, ...] |
| 4 | `countries` | list | "Cílové země?" | ≥1 ISO kód |
| 5 | `business_type` | enum | "Typ byznysu? e-shop / služba / info / mix" | 1 ze 4 hodnot |
| 6 | `primary_goal` | str | "Co chceš dosáhnout?" | ≥10 znaků |
| 7 | `deadline` | date | "Do kdy?" | Budoucí datum |
| 8 | `expected_kw_count` | int | "Kolik KW očekáváš? 1K / 5K / 10K / 50K" | Pro AI model selection |
| 9 | `in_scope` | list | "Jaké produkty/služby jsou IN?" | ≥1 položka |
| 10 | `out_of_scope` | list | "Co NENÍ scope?" | ≥1 položka (forces user to think) |
| 11 | `competitors` | list | "Znáš konkurenci? Pokud ne, dohledám." | ≥0 (AI dohledá v 0.2 pokud prázdné) |
| 12 | `priority_products` | list | "Priorita? (launch, focus)" | ≥0 |
| 13 | `insider_info` | str | "Něco co SEO tool nevidí?" | ≥0 |

**Checkpoint 0.1:** AI shrne všech 13 polí v tabulce → user potvrdí / opraví.

**Acceptance criteria:**
- Všechna povinná pole (1-10) vyplněna před pokračováním
- `primary_goal` je konkrétní (ne "chceme víc traffic")
- `out_of_scope` má ≥1 položku (nutí user přemýšlet nad hranicemi)
- Deadline je konzistentní s `expected_kw_count` (5K KW ≠ 2 týdny)

---

### 3.2 RESEARCH — iterativní v Claude Code

**Mechanismus:** Best practice pattern inspirovaný Claude Desktop deep research:

```
STEP 1   AI ukáže plán research ("zkoumám A/B/C/D/E, čas 5-10 min")
  ↓
STEP 2   Iterativní zkoumání (pro každou sekci):
         a) AI volá tools (WebFetch, WebSearch, DFS MCP)
         b) Ukáže partial findings v chatu (user vidí progress)
         c) Když narazí na nejednoznačnost → PTÁ SE user a čeká
         d) Pokračuje
  ↓
STEP 3   Strukturovaný summary (5 sekcí A-E) v chatu
  ↓
STEP 4   CHECKPOINT — user: "OK" / "doplň X" / "pusť znovu B"
  ↓
STEP 5   (soubor se zatím NEPÍŠE — zapíše se až v 0.4 při project create)
```

**Research output contract (STANDARDNÍ, 5 sekcí):**

```markdown
## A. Web klienta ({{domain}})
A.1  Existující kategorie (URL + odhad produktů)
A.2  Chybějící kategorie (vs. competitors — GAP)
A.3  Blog sekce (co je, témata, kolik článků)
A.4  USP / Unique selling points

## B. Konkurenti ({{competitor_list}})
Pro každého:
B.1  Content strategy summary
B.2  Top blog témata (3-5)
B.3  Authority signal (DR z DFS, top-ranked keywords)
B.4  Co mají, co klient nemá

## C. Trh & Segmenty
C.1  Trendy (3-5 bodů)
C.2  Edukační obsah (YouTube, fóra)
C.3  Pain points uživatelů

## D. Keyword Opportunities (TOP 15)
Tabulka: keyword | intent | SV (DFS) | KD (DFS) | opportunity

## E. Priority Product Deep-Dive
Pro každý priority_product z briefu:
E.1  Otázky zákazníků
E.2  Srovnání s competitors
E.3  Content assets needed
```

**Povolené tools:**

| Nástroj | Použití |
|---------|---------|
| `WebFetch` | Web klienta + competitorů (homepage, sitemap, kategorie, blog) |
| `WebSearch` | Trendy, pain points, edukační obsah |
| `mcp__dfs-mcp__dataforseo_labs_google_keyword_overview` | SV + KD + intent |
| `mcp__dfs-mcp__dataforseo_labs_google_keyword_suggestions` | Keyword expansion (sekce D) |
| `mcp__dfs-mcp__dataforseo_labs_google_ranked_keywords` | Co competitor/klient rankuje (A.2, B.3) |
| `mcp__dfs-mcp__dataforseo_labs_google_competitors_domain` | Najít další competitors |
| `mcp__dfs-mcp__dataforseo_labs_google_domain_rank_overview` | DR signal (B.3) |
| `mcp__dfs-mcp__dataforseo_labs_search_intent` | Klasifikace intentu (sekce D) |
| `mcp__dfs-mcp__serp_organic_live_advanced` | SERP analýza pro top KW |
| `mcp__dfs-mcp__on_page_content_parsing` | Fallback když WebFetch selže (JS-rendered sites) |

**NE použít:** Ahrefs MCP (auth komplikace), Chrome DevTools MCP (overhead), Exa MCP (rozhodnuto: jen DFS).

**Kdy se AI ptá uživatele (best practice):**

AI přeruší research a zeptá se když:

| Situace | Příklad |
|---------|---------|
| Víc kandidátů na competitor | "Nad briefem se v SERP top 10 objevují: kuhtreiber.cz (#4), svarbazar.cz (#7). Zahrnout? [oba/jen první/žádný]" |
| Nejasný scope | "Klient má kategorii 'automaty' (20 produktů), v briefu specifikováno jen 'MIG/TIG/elektrodové'. Patří to dovnitř?" |
| Chybějící data | "DFS nevrátil SV pro 'argonový mix 8L'. Chceš odhad přes WebSearch?" |
| Konflikt s briefem | "Deadline do 30.6., ale competitor má jarní sezónní content (březen-květen). Priorita jarní KW?" |
| Hloubka | "Mám hledat i fóra (C.2) nebo stačí YouTube? +2-3 min." |

**Token budget mitigace:**
- Research běží v **hlavním kontextu** (ne subagent) — user vidí každý krok
- AI NESTÁHNE celé články — jen relevantní pasáže + URL reference
- Summary ~2-4K tokenů, detail se neukládá

**Checkpoint 0.2:** Research summary v chatu → user **"OK" / "doplň X" / "pusť znovu B"**.

**Acceptance criteria:**
- Všech 5 sekcí (A, B, C, D, E) vyplněno NEBO explicitně označeno "NEDOSTUPNÉ: důvod"
- Sekce B pokrývá všechny competitors z briefu (1-5 dle #11)
- Sekce D má ≥10 keywords se SV + KD (pokud DFS dostupné)
- User explicitně schválí ("OK") — ne implicit ticho

---

### 3.3 PARAMS.YAML — generování s traceability

**Mechanismus:** AI vygeneruje kompletní `params.yaml` podle schématu v `/akw` skillu, s **inline komentáři** odkazujícími na zdroj hodnoty (`brief #X` nebo `research Y.Z`).

**Příklad (zkrácený):**

```yaml
client:
  name: "Svářečky-obchod"           # brief #1
  domain: "svarecky-obchod.cz"      # brief #2
  language: ["cs", "sk"]            # brief #3
  country: ["CZ", "SK"]             # brief #4

cleaning:
  word_order_dedup: true            # business_type=e-shop → bezpečný
  volume_strategy: "sum_volumes"    # default

filters:
  min_search_volume: 5              # expected_kw_count=10K + priority=TIG launch → nízký SV OK
  blacklist:
    - "kurz"                        # research C.3 (pain point, ne nákup)
    - "skoleni"                     # research C.3
    - "wikipedia"                   # default AKW blacklist

relevance:
  client_description: >             # research A.1 + A.4
    E-shop + blog s články o svařování. MIG, TIG, elektrodové
    + příslušenství. Nový TIG invertor v launch.
  products:                         # brief #9 + research A.1 + D
    - "MIG svářečka"
    - "TIG svářečka"                # PRIORITY (brief #12)
    - "elektroda"
    - "argon"                       # research D.6 — GAP (competitors nemají)
  excluded:                         # brief #10 + research A.4
    - "servis"
    - "bazar"
    - "tezky prumysl"
  competitors:                      # brief #11 + research B
    - "esab"
    - "lincoln"
    - "hypertherm"
    - "kuhtreiber"                  # ADDED z research B (user schválil v 0.2)
```

**Checkpoint 0.3:** AI UKAZUJE params.yaml v chatu → user reviewuje → "OK" / "změň X". Soubor se zapíše až v 0.4 (FW-002).

**Acceptance criteria:**
- Každá ne-default hodnota má inline komentář s odkazem na zdroj
- `products` ⊃ `in_scope` z briefu (rozšířeno o research findings)
- `excluded` ⊃ `out_of_scope` z briefu
- `competitors` = brief #11 ∪ research B additions
- Schema validuje proti `params.yaml schema` v skillu (client/cleaning/filters/relevance/categorization/ai/scoring/paths)

---

## 4. Summary: Nová vs. Stará Fáze 0

| Aspekt | Stará | Nová |
|--------|-------|------|
| Počet polí v briefu | 5 volných | 10 povinných + 3 volitelné |
| Dotazování | Vše najednou | Po jedné, s validací |
| Research kde | Claude Desktop externě | Claude Code in-flow |
| Research tools | Claude Desktop web search | WebFetch + WebSearch + DFS MCP |
| Research iterativnost | Black box | AI klade otázky během research |
| Research struktura | Ad-hoc | Standardní 5 sekcí A-E |
| params.yaml traceability | Žádná | Inline komentáře |
| Checkpointy | 4 (po 0.1, 0.2, 0.4, 0.5) | 3 silné (po 0.1, 0.2, 0.3) |

---

## 5. Risks & Mitigations

| Riziko | Mitigace |
|--------|----------|
| Claude Code research mělčí než Desktop | Iterativní pattern + AI klade otázky + DFS MCP pro SEO data |
| Token budget v main context | Summary only (2-4K), žádné full články, URL reference |
| DFS MCP selže (auth, rate limit) | Fallback na WebSearch + WebFetch |
| User netrpělivý / neodpovídá | AI čeká, neimpovizuje. 3× ignorace → ukončí research, dá co má |
| Chybí data (nenalezeno) | AI explicitně napíše "CHYBÍ: X" v summary, user rozhodne |
| User preskočí validaci | Checkpointy explicitní — AI bez "OK" nepokračuje |
| Rozbitý mirror skillu (2 soubory, 1 se zapomene) | Implementation plan updatuje obojí ve stejném commitu |

---

## 6. Implementation Plan

### Files to modify

1. **`/Users/admin/.claude/commands/akw.md`** (primární, 1428 řádků)
   - Přepsat sekci "Faze 0: Project Setup" (dnes řádky ~56-134)
   - Zachovat ostatní fáze (1-11) beze změny
   - Přidat sekci o 0.4 TBD (FW-002 pending)

2. **`/Users/admin/Documents/Akws/Akw_framework/.claude/skills/akw/SKILL.md`** (mirror v repo, 957 řádků)
   - Identická změna jako v #1
   - Oba soubory musí být synced po commitu

### Neopustit v této iteraci

- `docs/acceptance-criteria.md` — Fáze 0 sekce (FW-003)
- `CURRENT.md` — update po merge (součást commitu)
- `CLAUDE.md` v repo — zůstává beze změny (je navigation doc)

### Dual source of truth

Podle `CURRENT.md` řádek 262-267: framework spec žije na 2 místech (skill + repo). Změny musí být **v obou**. Plánuje se zkrácení CLAUDE.md na navigaci (viz CURRENT.md "Next steps"), ale **teprve po** doplnění `docs/`. Tato iterace to neřeší.

---

## 7. Verification

### End-to-end test (před merge)

1. Otevřít nový projekt přes `/akw` (testovací klient)
2. Ověřit že AI klade otázky po jedné (ne všechny najednou)
3. Ověřit že všech 13 polí je procházeno (10 povinných blokuje pokračování, 3 volitelné lze skip)
4. Ověřit že research probíhá v Claude Code (ne Claude Desktop)
5. Ověřit že AI použije minimálně 2 DFS MCP endpointy
6. Ověřit že AI se během research **pozeptá** alespoň 1× (očekávaná situace)
7. Ověřit že summary má všech 5 sekcí (A-E) nebo explicit "NEDOSTUPNÉ"
8. Ověřit že `params.yaml` má inline komentáře s traceability na ≥80% non-default hodnot

### Regression check

- Stará Fáze 0 workflow (copy-paste z Claude Desktop) **nefunguje**, je to by-design breaking change. Stávající projekty jsou v Fázi 1+, neovlivněné.
- Fáze 1-11 (existing) **nezměněné**.
- Referenční projekty (`llentab`, `mbank`, atd.) **nezasažené**.

### Acceptance (FW-001 done when)

- [ ] 0.1 + 0.2 + 0.3 popsány v skillu (oba soubory)
- [ ] End-to-end test prošel (bod 1-8 výše)
- [ ] Oba skill soubory synced (diff = 0 mimo repo-specific frontmatter)
- [ ] CURRENT.md updatován (sekce "Čo funguje" přidá FW-001)
- [ ] 0.4 explicitně označeno jako TBD / FW-002 v skillu

---

## 8. Open Questions

- [ ] **0.4 Project Create** — sanity check? decision log? scope/timeline dokumenty? → FW-002
- [ ] **Acceptance criteria pro Fázi 0** — přidat do `docs/acceptance-criteria.md`? → FW-003
- [ ] **Behavior když user odmítá odpovědět na otázku 1-10** — AI se zeptá ještě 1×, pak ukončí? → před implementací rozhodnout

---

## 9. References

- Audit chat: konverzace 2026-04-23 (kompletní pros/cons analýza)
- Skill (dnes): `/Users/admin/.claude/commands/akw.md` řádky 56-134
- Mirror v repo: `/Users/admin/Documents/Akws/Akw_framework/.claude/skills/akw/SKILL.md`
- Framework context: `/Users/admin/Documents/Akws/Akw_framework/CURRENT.md`
- ADR o test mode (podobný pattern): `docs/decisions/007-test-mode-before-full-run.md`
