# ADR-005: Checkpoint/resume pattern v AI skriptech

- **Status:** accepted
- **Date:** 2026-04-23
- **Validated by:** DeLonghi (25 000 KW run, 3 přerušení), eVisions

## Context

AI běh na 10 000+ KW trvá desítky minut. Během toho může selhat:
- **Síťový výpadek** (timeout, DNS failure)
- **Rate limit** (OpenAI/Anthropic limity za minutu/den)
- **Kvóta / insufficient funds**
- **Lokální problém** (Mac usne, baterie, uživatel omylem Ctrl+C)
- **Model downtime** (provider outage)

Bez recovery logiky přerušení = ztráta celé práce + API nákladů za zpracované KW.

## Decision

**Každý AI skript ve framework implementuje checkpoint/resume pattern**:

1. Po každém batch (30-50 KW) ulož stav do JSON souboru
2. Při spuštění nejdřív načti checkpoint (pokud existuje) a pokračuj od posledního neuloženého batche
3. Po úspěšném dokončení celého runu checkpoint smaž

Konkrétní soubory:
- `data/interim/checkpoint_relevance.json`
- `data/interim/checkpoint_categorization.json`

## Reasoning

- **API náklady jsou reálné.** Přerušený 10k run = ztráta $5-30 při full restartu
- **Čas je dražší než API cost.** Běh trvá 20-60 min, čekat dvakrát je plýtvání dne
- **Přerušení je kdy-ne-jestli.** Ne zda, ale kdy přijde rate limit / síťový výpadek. Při desítkách běhů ročně = každoměsíčně
- **Nejedno uložení mid-batch.** Ukládat po KAŽDÉM KW = nadměrný IO. Ukládat po batch = rozumný kompromis

## Consequences

**Pozitivní:**
- Přerušený běh = pokračování, ne restart
- Možnost debugovat na část dat, pak pokračovat
- Resilience proti všem typům přerušení (síť, rate limit, user Ctrl+C)

**Negativní:**
- Extra kód v každém AI skriptu (čtení/zápis JSON)
- Checkpoint soubory se musí udržovat čisté (smazat po úspěšném runu, jinak confusion při dalším spuštění)
- Pokud se mění params.yaml mid-run, musíš checkpoint smazat ručně (otherwise nekonzistence)

## Implementace

### Formát checkpointu

```json
{
  "started_at": "2026-04-23T10:15:00",
  "last_batch": 42,
  "total_batches": 167,
  "processed_count": 1260,
  "params_hash": "a7f3c9...",
  "results_so_far": [...]
}
```

### Pravidla

1. **Check params_hash**: pokud se params.yaml změnil od checkpointu, zastav s erroem a pokyny (smazat checkpoint nebo vrátit params)
2. **Exponential backoff** při API errorech: retry 3× s delay 1s → 2s → 4s, pak ulož checkpoint a ukonči
3. **Atomický zápis**: `tempfile → rename` aby se checkpoint nekorupoval při crashi během zápisu
4. **Vymazat po úspěchu**: po dokončení runu checkpoint smaž (jinak další běh bude thinking it's resumed)

### tqdm progress bar

Checkpoint pattern jde ruku v ruce s `tqdm` progress bar — uživatel vidí, kde je, kolik zbývá, kolik bude stát dokončit.

## When to revisit

- Pokud přejdeme na streaming API s server-side resume (některá provider by to mohl nabídnout)
- Pokud batch size vzroste na 1000+ (pak by byl checkpoint per-batch příliš hrubý)
