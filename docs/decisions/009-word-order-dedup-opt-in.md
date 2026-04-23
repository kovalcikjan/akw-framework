# ADR-009: Word-order dedup jako opt-in (default OFF)

- **Status:** accepted
- **Date:** 2026-04-23
- **Validated by:** mBank, eVisions (intent corruption risk identifikován v mBank)

## Context

Fáze 3 (Cleaning) má 3 úrovně deduplikace: exact → diacritics → word-order. Word-order dedup slučuje KW která obsahují stejná slova v jiném pořadí:

```
"mig svářečka 200A"  +  "svářečka mig 200A"  →  merge (stejný KW)
```

Otázka: má se tohle dělat automaticky pro všechny projekty?

## Decision

**`word_order_dedup: false` jako default.** Opt-in per projekt přes `params.yaml`:

```yaml
cleaning:
  word_order_dedup: false   # true jen pro e-commerce produkty
```

## Reasoning

### Proč ne default ON

Word-order dedup předpokládá, že pořadí slov nemění intent. To neplatí obecně:

```
"pojištění auta"    → TRANS (chci si koupit pojistku pro auto)
"auta pojištění"    → INFO nebo NAV (hledám info, možná pojišťovna)

"koupit notebook"   → TRANS
"notebook koupit"   → totéž — OK pro merge

"online marketing kurz"  → informační (vzdělávání)
"kurz online marketing"  → může být nabídka (rozdílný landing)
```

Sloučení `"pojištění auta"` a `"auta pojištění"` by:
1. Zkombinoval volume obou → přestřelený odhad
2. Vybral jeden canonical → druhý intent se ztratí
3. Poškodil few-shot examples ve fázi 5 (špatný intent v příkladech)

### Kdy je word-order dedup bezpečný

Pro e-commerce produkty kde pořadí slov opravdu nemění intent:

```
"svářečka mig 200"  ≈  "mig svářečka 200"   → bezpečné
"elektroda bazická"  ≈  "bazická elektroda"  → bezpečné
```

Společný jmenovatel: **produktové KW bez frázových vzorů** (žádná slovesa, žádné intentové signály v pořadí).

### Proč opt-in (ne opt-out)

- Conservative default = méně překvapení
- Chyba z nečekané deduplikace je těžko debugovatelná (KW tiše zmizí)
- Uživatel, který word-order chce, vědomě zapne

## Consequences

**Pozitivní:**
- Žádná neočekávaná ztráta KW
- Intent zachován i pro projekty s phrase-sensitive KW (pojišťovnictví, finance, B2B)
- Bezpečný default pro nový projekt kde neznáš data

**Negativní:**
- Více KW v datasetu u e-commerce projektů (zbytečné duplikáty)
- Vyšší AI batch ve fázích 4-5 (stejné KW posílá vícekrát, vyšší cena)
- Nutnost manuálně zapnout pro vhodné projekty

## Kdy zapnout

`word_order_dedup: true` nastavit pokud:
- Projekt je e-commerce s jasně definovanými produktovými KW
- EDA (fáze 2) ukazuje velké shluky word-order variant (bi-gram analýza)
- Doménový expert potvrdí, že pořadí slov nerozlišuje intent

## Related

- [ADR-001](001-static-diacritics-map.md) — diacritics dedup (vždy ON)
- [ADR-004](004-rule-based-before-ai.md) — word-order dedup ovlivňuje quality few-shot examples
