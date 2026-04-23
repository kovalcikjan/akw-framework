# ADR-005: Checkpoint/resume pattern v AI skriptech

- **Status:** accepted
- **Date:** 2026-04-23
- **Validated by:** DeLonghi (25 000 KW run, 3 přerušení), eVisions, llentab

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
2. Při spuštění nejdřív načti checkpoint (pokud existuje) a pokračuj od neprocessed batchů
3. Po úspěšném dokončení celého runu checkpoint smaž

Konkrétní soubory:
- `checkpoint_relevance.json` (v project root)
- `checkpoint_categorization.json` (v project root)

## Reasoning

- **API náklady jsou reálné.** Přerušený 10k run = ztráta $5-30 při full restartu
- **Čas je dražší než API cost.** Běh trvá 20-60 min, čekat dvakrát je plýtvání dne
- **Přerušení je kdy-ne-jestli.** Ne zda, ale kdy přijde rate limit / síťový výpadek
- **Neukládej mid-batch.** Ukládat po KAŽDÉM KW = nadměrný IO. Ukládat po batch = rozumný kompromis

## Consequences

**Pozitivní:**
- Přerušený běh = pokračování, ne restart
- Možnost debugovat na část dat, pak pokračovat
- Resilience proti všem typům přerušení (síť, rate limit, user Ctrl+C)

**Negativní:**
- Extra kód v každém AI skriptu (čtení/zápis JSON)
- Checkpoint soubory se musí udržovat čisté (smazat po úspěšném runu, jinak confusion při dalším spuštění)
- **Aktuálně bez params_hash verifikace** → pokud uprostřed runu změníš params.yaml, výsledky budou nekonzistentní (viz TODO níže)

## Implementace — současný stav

### Formát checkpointu

```json
{
  "processed_batches": [0, 1, 2, 3, ...],
  "results": {
    "keyword_one": {"relevance": "ANO", "reason": "...", "confidence": "high"},
    "keyword_two": {"relevance": "NE", "reason": "...", "confidence": "high"}
  }
}
```

- `processed_batches` — indexy dokončených batchů (pro skip-logiku)
- `results` — dict keyed by `keyword_normalized`, obsahuje AI odpověď

### Funkce (obě skripty mají identickou strukturu)

```python
def load_checkpoint(project_root: Path) -> dict:
    path = project_root / "checkpoint_<phase>.json"
    if path.exists():
        return json.load(open(path))
    return {"processed_batches": [], "results": {}}

def save_checkpoint(project_root: Path, checkpoint: dict) -> None:
    path = project_root / "checkpoint_<phase>.json"
    json.dump(checkpoint, open(path, "w"), ensure_ascii=False, indent=2)

def cleanup_checkpoint(project_root: Path) -> None:
    path = project_root / "checkpoint_<phase>.json"
    if path.exists():
        path.unlink()
```

### Doprovodné patterns

**Exponential backoff** při API errorech (v `ai_classify_batch`):

```python
for attempt in range(max_retries):    # max_retries = 3
    try:
        return call_ai(...)
    except Exception as e:
        delay = 2 ** attempt            # 1s, 2s, 4s
        time.sleep(delay)
```

**Fallback při neúspěchu všech retries:** KW dostane `relevance=MOZNA` s reason `"AI error after retries"`, confidence `low`. Bezpečný default — skript nespadne, chybné KW jdou do review.

**`time.sleep(0.5)` mezi batchi** — rate limit protection (ani ne tak pro samotné API, jako pro provider throttling při burstu desítek requestů).

**High-volume MOZNA retry (jen fáze 4):** KW s `volume > 500`, které po první AI pass zůstaly MOZNA, dostanou druhý pokus s potenciálně větším kontextem. Důvod: hodnotné KW si zaslouží víc energie na rozhodnutí.

## TODO — plánovaná vylepšení

### 1. Atomický zápis checkpointu

**Současný stav:** `json.dump(..., open(path, "w"))` — pokud spadne mezi `open` a `write`, checkpoint je poškozený/prázdný.

**Plán:** použít tempfile + rename:

```python
def save_checkpoint(project_root: Path, checkpoint: dict) -> None:
    path = project_root / "checkpoint_<phase>.json"
    tmp_path = path.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)
    tmp_path.replace(path)   # atomický rename
```

**Priorita:** střední — v praxi se zatím nestalo, ale je to latent bug při crash uprostřed zápisu.

### 2. `params_hash` kontrola

**Současný stav:** žádná ochrana — pokud mezi přerušením a rerunem změníš `params.yaml`, checkpoint se načte s novými pravidly a výsledky budou inkonzistentní (část KW zpracovaná starými pravidly, část novými).

**Plán:** ukládat hash `params.yaml` do checkpointu; při resume porovnat:

```json
{
  "params_hash": "a7f3c9e2...",
  "processed_batches": [...],
  "results": {...}
}
```

```python
if checkpoint.get("params_hash") != current_hash:
    log.error("params.yaml changed since last run. Delete checkpoint or revert params.")
    sys.exit(1)
```

**Priorita:** vyšší — riziko tichých chyb při úpravě pravidel mid-run. Důležité zejména po neúspěšném testu, když se rozhodneš upravit params a zapomeneš smazat checkpoint.

## When to revisit

- Pokud přejdeme na streaming API se server-side resume (některý provider by to mohl nabídnout)
- Pokud batch size vzroste na 1000+ (pak by byl checkpoint per-batch příliš hrubý)
- Po implementaci TODO 1 a 2 → update status souboru a description
