# Acceptance Criteria

Kdy je která fáze **hotová a správně**. Každá fáze má: měřitelné kritéria, red flagy, sample checks. Tento dokument je kontrolní seznam před pokračováním do další fáze — ve chvíli, kdy si říkáš *"je to OK?"*, se podívej sem.

## Princip

- **Každá fáze = checkpoint.** Před pokračováním projdi sekci této fáze.
- **Red flag ≠ blocker**, ale vyžaduje rozhodnutí (ignorovat / opravit).
- **Sample check = 20 KW ručně**, ne statistika. Statistika lže, KW pravdu řeknou.

---

## Fáze 1 — Seed Keywords + Expansion

### Done když

- [ ] Všechny plánované zdroje nahrané do `data/raw/` (GSC, Ahrefs, konkurenti, Marketing Miner)
- [ ] `keywords_raw.csv` obsahuje sloupec `source` s jasným označením původu
- [ ] Volume > 0 u alespoň 60 % KW (pokud míň, chybí MM expansion)
- [ ] Žádná fáze není reprezentovaná jen jedním zdrojem (diverzita)

### Red flags

- **90 % KW jen z jednoho zdroje** → chybí zdroje, málo dat pro validní analýzu
- **Vysoké % KW s volume=0** → Marketing Miner expansion neproběhla nebo selhala
- **KW jsou zjevně mimo obor** → špatná seed selection, vrátit se a opravit

### Sample check

Náhodných 20 KW → *"dává smysl, že je tu?"* Pokud < 15/20 ano, vrátit se k seed sběru.

---

## Fáze 3 — Cleaning + Dedup

### Done když

- [ ] Deduplication ratio 10-30 % (méně = nebyly duplicity; víc = nějaká fáze smazala víc než má)
- [ ] `keywords_clean.xlsx` má všech 5 listů (viz [data-contracts](data-contracts.md))
- [ ] `Variant Clusters` sheet obsahuje aspoň 5 clusterů s 2+ variantami
- [ ] Cluster report ukazuje smysluplnou canonical selection (preferuje diakritiku, pak volume)
- [ ] `keywords_filtered_out.csv` obsahuje `filter_reason` u každého záznamu

### Red flags

- **Dedup > 50 %** → word_order_dedup není pro tenhle projekt vhodný (vypnout)
- **Dedup < 5 %** → normalizace nebo diacritics logic nefunguje, ověřit sample
- **Canonical vybral ASCII variantu místo diakritiky** → bug v scoring logice
- **Blacklist odstřelil head terms** → špatná blacklist konfigurace

### Sample check

Z `Variant Clusters` sheet náhodných 10 clusterů → *"dává smysl, že se sloučily?"* + *"byla vybrána správná canonical?"*

---

## Fáze 4 — Relevance

### Done když

- [ ] Rule-based pokryl 60 %+ KW (pokud míň, rozšířit pravidla v params.yaml — viz fáze 5.0 preview)
- [ ] AI klasifikace běží jen na `MOZNA`, ne na celém datasetu
- [ ] Každý řádek má `relevance_reason` (max 15 slov)
- [ ] `relevance_source` = `rule` nebo `ai`, nikdy prázdné
- [ ] `relevance_review.csv` obsahuje flagged KW → **ručně projít před dalším krokem**

### Red flags

- **> 20 % NE s volume > 1000** → možná se odfiltrovaly relevantní KW, projít ručně
- **ANO + competitor brand** → zkontrolovat kontext (může být OK pro competitive)
- **Krátký reason (< 3 slova) u ai klasifikace** → prompt nedává dost kontextu
- **Rule coverage < 40 %** → params.yaml je moc obecné, víc peněz za AI

### Sample check

20 KW z každé kategorie (ANO/NE/MOZNA) → ruční verdikt vs model verdikt. Shoda < 85 % = ladit prompt/pravidla.

---

## Fáze 5 — Kategorizace

### Done když

- [ ] Rule-based pokryl 80 %+ (po rozšíření z EDA n-gramů)
- [ ] Few-shot examples obsahují 15-20 high-confidence případů z rule-based
- [ ] Každý řádek má `intent` a `funnel` (povinné)
- [ ] `intent × funnel` respektuje mapping ([data-contracts](data-contracts.md))
- [ ] Money keywords ≤ 30 % všech relevantních (víc = moc benevolentní kritéria)
- [ ] `categorization_issues.csv` projitý, issues vyřešené nebo akceptované

### Red flags

- **TRANS + dotazové slovo** (jak, co) → intent/typ mismatch, opravit
- **Brand keyword bez detected brand** → post-processing selhal
- **Money keywords > 50 %** → `money_threshold` je příliš nízký
- **Produkt prázdný u 30 %+ KW** → produkt patterns v params.yaml jsou nedostatečné

### Sample check

20 money keywords → *"opravdu je to TRANS/COMM a dává smysl pro business?"* Pokud < 16/20 ano, projít kritéria.

---

## Fáze 6 — SERP Clustering (optional)

### Done když

- [ ] Počet clusterů = 15-40 (méně = threshold moc volný; víc = moc přísný)
- [ ] Každý cluster má 2+ KW (single-KW clustery spíš prozrazují, že clustering nepomohl)
- [ ] `cluster_name` = highest volume KW v clusteru (konzistentně)
- [ ] Top 10 clusterů ručně projité a pojmenované smysluplně

### Red flags

- **Cluster > 30 KW** → threshold je moc volný, zvažit zpřísnění
- **80 % single-KW clusters** → KW jsou moc různorodé, nepoužít clustering
- **Clustery přes nesouvisející produkty** → SERP data jsou vadná nebo stale

### Sample check

5 největších clusterů → *"tyto KW patří opravdu na jednu stránku?"*

---

## Obecná pravidla napříč fázemi

### Před každým full AI run

- [ ] `--test 20` proběhnul
- [ ] Výsledky testu ručně zkontrolované (ne jen metriky)
- [ ] Params.yaml upravený podle zjištění z testu
- [ ] Odhad nákladů na full run (batch × cena modelu × počet KW)

### Před předáním klientovi

- [ ] Všechny fáze mají ≥ 80 % acceptance kritérií splněných
- [ ] Žádný red flag není ignorován bez rozhodnutí
- [ ] Finální Excel ručně projitý — otevři, podívej se na listy, pročti 30 KW
- [ ] Executive summary obsahuje čísla z `Summary` sheetu (cleaning) a `categorization_issues` count

### Kdy zastavit a vrátit se zpět

- **Fáze 3 selže acceptance** → oprav, neposouvat se dál s nekvalitními daty
- **Fáze 4 má ANO < 30 %** → špatná relevance pravidla, kompletně překontrolovat
- **Fáze 5 má 20 %+ chyb ve validaci** → prompt ladit, ne pokračovat
