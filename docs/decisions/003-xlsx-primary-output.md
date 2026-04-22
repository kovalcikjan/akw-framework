# ADR-003: XLSX multi-sheet jako primární output formát

- **Status:** accepted
- **Date:** 2026-04-23
- **Validated by:** mBank, CPP, DeLonghi mixery, svářečky (4 projekty)

## Context

Klient / SEO konzultant / stakeholder dostává výstup keyword research analýzy. Otázka: v jakém formátu?

Experimentálně jsme zkoušeli:
- Čistý CSV → klient se v tom ztrácí, nemůže filtrovat pohodlně
- Google Sheets → problém s velkými datasety (>10k řádků), permissions, versioning
- Notion databáze → impraktická exports/imports
- PDF report → nedá se s tím pracovat, jen číst

## Decision

**Primární output = XLSX multi-sheet**. CSV zůstává jako sekundární (pro pipeline mezi fázemi).

Povinné listy v každém klientském deliverable:

1. **Final Keywords** — čisté, klasifikované, připravené
2. **Money Keywords** — priority subset
3. **Variant Clusters** — audit trail dedup
4. **Summary** — metriky (počty, ratios, rozdělení)
5. **Schema / Legend** — vysvětlení sloupců, enum hodnot

## Reasoning

- **Klienti pracují v Excelu.** Čemukoli jinému se brání — podpora je v pořadí: Excel > Google Sheets > všechno ostatní
- **Multi-sheet = separace concerns**. Surový list KW vedle exekutivního summary vedle auditní stopy
- **Filtry, conditional formatting, pivoty** — Excel je v tom mistrem, datový konzument to očekává
- **Auditovatelnost**: klient vidí, kolik KW bylo sloučeno a proč (Variant Clusters)
- **Offline capabilty**: pošlu to mailem, funguje i bez internetu

## Consequences

**Pozitivní:**
- Klient je spokojen, bez další edukace
- Snadno se posílá, komentuje, uchovává
- Audit trail je součást výstupu
- Summary sheet = elevator pitch na klient call

**Negativní:**
- Velké datasety (100k+ KW) otevírání chvíli trvá
- Diakritika + encoding občas potrápí (řeší `openpyxl` default UTF-8 + BOM)
- Generování přes Python je pomalejší než CSV dump

## Technická implementace

- Knihovna: `openpyxl` (**ne pandas.to_excel**, pandas defaultně nezachovává styles a je pomalejší)
- Pojmenování listů: `snake_case_ascii` (bez mezer, česká jména rozbíjejí některé Excel verze)
- Formátování: vždy header row bold + freeze pane na prvním řádku
- Široké sloupce: auto-width po naplnění dat

## When to revisit

- Pokud klient začne preferovat **Looker Studio / Tableau** jako deliverable (pak CSV + dashboard)
- Pokud datasets pravidelně překračují 500k řádků (XLSX limit je cca 1M, ale výkon klesá)
- Pokud vstup bude přes API místo file drop (pak JSON)
