# ADR-001: Static diacritics map (ne NFD decomposition)

- **Status:** accepted
- **Date:** 2026-04-23
- **Validated by:** mBank, aks_svarecky, DeLonghi

## Context

Ve fázi 3 (Cleaning + Dedup) potřebujeme odstraňovat diakritiku pro matching, aby se `svářečka` a `svarecka` mohly sloučit do jednoho clusteru.

Python standardní cesta je `unicodedata.normalize('NFD', ...)` následované filtrováním kombinačních znaků. Tento přístup fungoval v ranějších projektech, ale **způsobil tiché bugy**.

## Decision

Používáme **static diacritics map** pomocí `str.maketrans`:

```python
DIACRITICS_MAP = str.maketrans(
    "áäčďéěíĺľňóôŕřšťúůýž",
    "aacdeeillnoorrstuuyz"
)
text_ascii = text.lower().translate(DIACRITICS_MAP)
```

NFD decomposition **nepoužíváme**.

## Reasoning

- **NFD rozbíjí specifické znaky** v některých edge cases — např. složené znaky s diakritikou nad i pod, nebo některé typografické entity v source datech (Unicode 3.x+ combinace)
- Static mapa je **deterministická**: pro každý vstupní znak je známý výstup, snadno debuggovat
- Nemusíme řešit platform/locale rozdíly
- Pokrývá 100 % českých a 95 % slovenských znaků, což je naše primární CZ/SK doména

## Consequences

**Pozitivní:**
- Reproducibilita — test na dev stroji = test na produkci
- Transparentní chování
- Rychlejší (str.maketrans je C-level optimalizovaný)

**Negativní:**
- Nepokrývá jazyky mimo CZ/SK (polština, maďarština). Pokud bude projekt pro jiný trh, mapa se musí rozšířit
- Nová diakritická písmena = manuální edit mapy

## When to revisit

Pokud framework začne obsluhovat jazyky mimo CZ/SK, nebo pokud se objeví bug v specifickém edge case českého znaku.
