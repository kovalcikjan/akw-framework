# ADR-007: Test mode (`--test N`) před full AI run

- **Status:** accepted
- **Date:** 2026-04-23
- **Validated by:** CPP (`classify_xlsx_test.py` pattern), všechny následné projekty

## Context

Full AI run na 10 000+ KW trvá 30-60 min a stojí $5-30. Pokud:
- Rule-based pravidla jsou špatně nastavená
- Prompt má bug
- Schema se neshoduje s daty
- Model je špatně vybraný

→ Celý run je promarněný + musíš znovu zaplatit.

Ranější projekty na tohle narazily několikrát (eVisions, pre-refactor mBank).

## Decision

**Každý AI skript (fáze 4, 5) má `--test N` flag**, který:

1. Zpracuje jen `N` náhodných KW (příklady v kódu: fáze 4 = 50, fáze 5 = 20)
2. Uloží výsledek do `data/interim/<phase>_test_<N>.csv` (neovlivní hlavní pipeline)
3. Spustí rule-based + AI na **všech** test KW (ne jen low-confidence) + reasoning sloupec
4. Vypíše metriky: rule coverage, AI souhlas, distribuce verdiktů, příklady neshod

**Full run bez testu NENÍ technicky vynucen — jde o disciplinovaný workflow, ne hard-blocker.** Doporučení: vždy `--test` před full run, ale uživatel má volnost to obejít.

**Test mode `--test-round N` flag** umožňuje iterativní rozběh s jinou náhodnou sadou KW mezi koly (random seed = `42 + test_round`).

## Reasoning

- **Test 20 KW × $0.002 = $0.04.** Skoro zdarma vs $5-30 za full run
- **Rychlý iterační cyklus**: test → review → upravit params.yaml → test → full run. 5-10 min per iteraci, ne hodinu
- **Catch bugs early**: špatný prompt, chybějící pole ve schématu, rule false positives — vše v testu viditelné
- **Confidence boost**: uživatel vidí konkrétní výstupy předtím, než commitne penězi

## Consequences

**Pozitivní:**
- 10× méně zbytečných full runů
- Rychlejší iterace parametrů
- Framework je odolnější proti nekontrolovaným chybám
- Uživatel (nebo klient) má důvěru v kvalitu před plným rozsahem

**Negativní:**
- Extra krok v procesu — uživatel se musí naučit, že test je **povinný**
- `--test-round N` pattern (druhé kolo s jinými KW) komplikuje API skriptu
- 20 KW nemusí odhalit všechny edge cases — full run stále potřebuje validaci

## Workflow

```bash
# Krok 1: Test
python src/relevance.py --test 20
# → vygeneruje data/interim/relevance_test_1.csv
# → ukáže statistiky a sample výstupy

# Krok 2: Review (uživatel)
# - Otevřít CSV, pročíst 20 KW manuálně
# - Souhlasí verdikt s očekáváním?
# - Pokud ne → upravit params.yaml, rerun

# Krok 3: Další testkolo nebo full run
python src/relevance.py --test 20 --test-round 2  # jiná náhodná sada
# nebo
python src/relevance.py  # full run, až když jsi spokojen
```

## Implementace v skriptu

```python
parser.add_argument("--test", type=int, default=None,
                    help="Test mode: process N random KW")
parser.add_argument("--test-round", type=int, default=1,
                    help="Test round number (for multiple iterations)")
parser.add_argument("--dry-run", action="store_true",
                    help="Ukáže prompt bez API call")

if args.test:
    keywords = keywords.sample(n=args.test, random_state=args.test_round)
    output_path = f"data/interim/{phase}_test_{args.test_round}.csv"
else:
    output_path = f"data/interim/{phase}.csv"
```

## Related patterns

- **`--dry-run` flag** (pouze v `categorization.py`, **ne v `relevance.py`**): ukáže, jak vypadá prompt, **bez** volání API — nulová cena, catch issues v prompt engineeringu. TODO pro `relevance.py`.
- **Checkpoint** (viz [ADR-005](005-checkpoint-resume-pattern.md)): test mode nepoužívá checkpoint (příliš malý run, zbytečné)
- **Model switching**: `--model gpt-5.5 / gpt-4o-mini / gpt-4o / gemini-2.0-flash / claude-sonnet-4-5-*` — test umožňuje porovnat konkurenční modely na stejné sadě KW

## When to revisit

- Pokud AI cena klesne 10× → možná by bylo levnější jen "pilot batch" 1000 KW místo 20 KW test
- Pokud přejdeme na custom fine-tuned model → test mode stále relevantní pro validaci schema a promptu
