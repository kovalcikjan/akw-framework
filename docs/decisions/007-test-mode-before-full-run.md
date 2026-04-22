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

1. Zpracuje jen `N` náhodných KW (default 20-50)
2. Uloží výsledek do `data/interim/categorization_test_N.csv` (neovlivní hlavní pipeline)
3. Ukáže reasoning u každého KW
4. Ukáže metriky: rule coverage, AI souhlas, distribuce verdiktů

**Full run (`python src/relevance.py` bez flagu) je zakázaný, dokud test neproběhl a nebyl zkontrolovaný.**

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

- `--dry-run` flag: ukáže, jak vypadá prompt, **bez** volání API — nulová cena, catch issues v prompt engineeringu
- Checkpoint (viz [ADR-005](005-checkpoint-resume-pattern.md)): test mode nepoužívá checkpoint (příliš malý run, zbytečné)

## When to revisit

- Pokud AI cena klesne 10× → možná by bylo levnější jen "pilot batch" 1000 KW místo 20 KW test
- Pokud přejdeme na custom fine-tuned model → test mode stále relevantní pro validaci schema a promptu
