# ADR-003: XLSX multi-sheet audit trail ve fázi 3, CSV pro pipeline, Google Sheets pro klienta

- **Status:** accepted
- **Date:** 2026-04-23
- **Validated by:** llentab, mBank, CPP, DeLonghi mixery, svářečky

## Context

Potřebujeme formát pro tři různé účely:

1. **Interim výstup fáze 3 (cleaning)** — dedup informace, cluster audit trail, summary statistiky. Nutno mít na jednom místě, aby se dalo snadno ověřit, co se sloučilo a proč.
2. **Pipeline mezi fázemi** — výstup jedné fáze čte další fáze. Musí být rychlé, jednoduché, spolehlivé.
3. **Finální deliverable pro klienta** — sdílený, editovatelný, vhodný pro komentáře a prezentaci.

Dříve se všechno dělalo v CSV + manuálním Excelu. Trpělo to:
- CSV neumí více listů → dedup audit trail se ztrácel mezi soubory
- Manuální Excel byl neshareable, nemohlo se komentovat
- Klient se v čistém CSV ztrácel

## Decision

**Rozlišujeme tři formáty podle use case:**

| Fáze | Output | Formát | Účel |
|------|--------|--------|------|
| 3 (cleaning) | `keywords_clean.xlsx` | XLSX multi-sheet (5 listů) | Interim audit trail |
| 3 (cleaning) | `keywords_clean.csv` | CSV | Vstup pro fázi 4 |
| 4, 5, 6 | `keywords_*.csv` | CSV only | Pipeline mezi fázemi |
| 7+ (dashboard, finální) | Google Sheets | Cloud spreadsheet | Klientský deliverable |

### Fáze 3 — XLSX listy

| List | Obsah |
|------|-------|
| Final Keywords | Čisté KW (odpovídá `keywords_clean.csv`) |
| All Keywords | Všechny s flagy |
| Merged Variants | Odebrané varianty + `merged_into` + `_score` |
| Variant Clusters | Canonical selection audit (`cluster_key`, `cluster_type`, …) |
| Summary | Metriky: input, dedup counts, filtered, final |

### Fáze 4, 5, 6 — jen CSV

Pipeline output. Žádné XLSX, žádné styling. Rychlost a jednoduchost.

### Finální deliverable — Google Sheets

Vytváří se **mimo aktuální skripty** (fáze 7+, manuální nebo budoucí automatizace). Tvorba Sheets není v scope fází 3-6.

## Reasoning

**Proč XLSX jen ve fázi 3:**
- Cleaning generuje **audit trail**, který má smysl držet pohromadě: final / all / merged / clusters / summary
- Bez multi-sheet bys musel udržovat 5 CSV souborů a při debugging skákat mezi nimi
- Je to jediné místo, kde *"jeden dataset = víc pohledů"* dává smysl

**Proč CSV pro fáze 4-6:**
- Pipeline — další fáze čte výstup. CSV je jednoduché, univerzální, rychlé
- Není potřeba audit trail v multi-sheet (jedna fáze = jeden pohled)
- XLSX by přidal zátěž bez přínosu (pandas `to_excel` je pomalejší než `to_csv`)

**Proč Google Sheets pro klienta:**
- Klient chce **komentovat, sdílet, filtrovat online**, ne stahovat XLSX soubor
- Umožňuje collaboration (klient + konzultant současně)
- Přirozeně napojitelné na Looker Studio pro dashboardy

## Consequences

**Pozitivní:**
- Fáze 3 má konsolidovaný audit trail (dedup decisions jsou dohledatelné)
- Fáze 4-6 běží rychle na CSV (read/write)
- Klient dostane formát, který skutečně používá

**Negativní:**
- Tvorba Google Sheets deliverable je **manuální krok** (nebo TODO pro automatizaci)
- Když klient chce XLSX soubor jako backup, musí se export Sheets → XLSX udělat ručně
- `keywords_clean.xlsx` a `keywords_clean.csv` jsou **duplikát dat** (CSV = obsah listu "Final Keywords"). Je to záměr — CSV pro pipeline, XLSX pro review.

## Implementation

### Použitá knihovna

```python
with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
    final_df.to_excel(writer, sheet_name="Final Keywords", index=False)
    # ... další 4 listy
```

Používáme `pandas.ExcelWriter` s engine=`openpyxl`. Ne čisté `openpyxl` API, ne `xlsxwriter`.

### Žádné styling

Aktuálně **nepoužíváme** bold headers, freeze panes, auto-width. Důvod: interim soubor není klientský deliverable, klient ho nevidí. Debugging přes `to_excel` stačí.

Pokud by se to v budoucnu změnilo (např. klient začne chtít XLSX deliverable s styling), přidání `openpyxl.styles` je jednoduché.

## When to revisit

- **Klient začne chtít XLSX soubor místo Google Sheets** → přidat styling do `cleaning.py`, rozšířit na fáze 4-5
- **Fáze 7+ budou scripted** a generují Google Sheets programaticky → popsat v novém ADR (Google Sheets API workflow)
- **Datasets > 500k KW** → XLSX ve fázi 3 začne být pomalé, zvažit Parquet nebo jen CSV s samostatnými audit soubory
