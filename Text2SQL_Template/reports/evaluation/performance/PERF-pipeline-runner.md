## Performance Analysis: Text2SQL Pipeline Runner

### Data Source

Timing data extracted from batch results at `logs/batch_result/2026-03-26_10-22-50.json` (20 queries).
Code analysis from `pipeline/runner.py`, `pipeline/retry_handler.py`, `pipeline/sql_generation/llm_sql_generator.py`, `pipeline/intent_detection/intent_ranker.py`, `pipeline/domain_router/selector.py`, `pipeline/entity_extraction/ner_local.py`, and `core/NER/ner_inference.py`.

---

### 1. Where Time Is Actually Spent (Ranked by Latency)

| Step | Component | Typical Latency | Worst Observed | Notes |
|------|-----------|-----------------|----------------|-------|
| 5 | **SQL Generation (LLM)** | **64-65s** | 65.2s | Single LLM call via `urlopen` with 120s timeout. This is the dominant cost when template-fill does not fully satisfy the query. |
| 6 | **Validation (with retry)** | 0.001-0.2s (no retry) | **130.4s** | When retry triggers LLM regeneration, validation step includes one or more additional LLM calls at ~65s each. Worst case: 130s = 2 LLM calls inside the retry loop. |
| 3 | **Entity Extraction (NER)** | 0.001s (warm) | **1.52s (cold)** | First call loads a PhoBERT-based `AutoModelForTokenClassification` from disk. After warm-up, pure inference is sub-ms. Falls back to regex (near-zero cost) on failure. |
| 1 | **Schema Router** | 0.001-0.03s | 0.042s | Keyword-based table ranking. Negligible. If `use_embedding=True`, adds one SentenceTransformer encode call per query. |
| 2 | **Intent Detection** | 0.001-0.01s | 0.01s | Keyword matching by default. If `use_embedding=True`, loads `intfloat/multilingual-e5-base` SentenceTransformer (first load ~5-15s, subsequent calls cached). |
| 0 | **Domain Router** | 0.0-0.001s | 0.001s | Pure keyword scoring. Near-zero. |
| 4 | **Template Fill** | 0.0s | 0.001s | String substitution. Near-zero. |
| 7 | **DB Execution** | 0.005-0.054s | 0.054s | Fast for the observed queries. |

**Key finding**: On a non-cached query that requires LLM generation, ~99% of wall-clock time is spent waiting for the LLM endpoint. Everything else combined is under 2 seconds even cold.

---

### 2. Worst-Case LLM Call Count (Single Query)

The retry logic in `runner.py` (Step 6 + Step 7) has **three independent validation gates**, each capable of triggering retries:

| Gate | What triggers retry | Actions per retry |
|------|--------------------|--------------------|
| **Structure validation** (`validate_all`) | Schema/syntax errors in generated SQL | 1. Attempt regex repair (no LLM). 2. If repair fails and retries remain, call LLM to regenerate. |
| **Semantic validation** (`validate_semantic`) | Semantic mismatch (wrong columns, missing filters) | 1. Attempt regex repair (no LLM). 2. If repair fails and retries remain, call LLM to regenerate. |
| **EXPLAIN validation** (`explain_query`) | DB rejects the SQL syntax | 1. Attempt regex repair (no LLM). 2. If repair fails and retries remain, call LLM to regenerate. |
| **DB Execution** (Step 7) | Runtime DB error on actual execution | 1. Attempt regex repair (no LLM). 2. If repair fails and retries remain, call LLM to regenerate + validate + re-execute. |

The `RetryHandler` is initialized with `max_retries=2` (from `config/settings.py: MAX_RETRY_ATTEMPTS = 2`). The retry budget is **shared** across all gates via a single `RetryHandler` instance. The `should_retry()` check is `len(self.attempts) < self.max_retries` (i.e., max 2 recorded attempts total).

However, the `should_attempt_repair()` is tracked **per error type** independently. Repairs are regex-based (no LLM cost). But each gate can also call `should_regenerate()` which checks the same `len(self.attempts) < 2` counter.

**Worst-case LLM call count for a single query**:

```
1  Initial SQL generation (Step 5)
1  Structure validation retry regeneration (records attempt #1)
1  Semantic validation retry regeneration (records attempt #2)
-- budget exhausted, no more regenerations --
```

But there is a subtle issue: the EXPLAIN gate and DB execution gate each check `retry.should_retry()` independently. If structure validation consumes 0 retries (repair succeeds) and semantic consumes 0 retries (repair succeeds), then EXPLAIN and DB exec can each consume 1 retry.

**Absolute worst case: 1 (initial) + 2 (retries) = 3 LLM calls**.

Additionally, if the primary `openai_compatible` backend fails, `generate_sql()` falls back to Ollama, adding a second LLM call per generation attempt. So with fallback:

**True worst case: 3 generations x 2 backends = 6 LLM calls**.

At ~65s per call, worst case is **~195-390 seconds** (3-6.5 minutes) for a single query.

---

### 3. What Loads Per Request vs. Cached (Singleton)

| Resource | Load Strategy | First-call Cost | Subsequent Cost |
|----------|--------------|-----------------|-----------------|
| **NER Model** (PhoBERT TokenClassification) | Lazy singleton in `ner_inference.py` (`ner_engine: Optional[NERInference] = None`) | ~1.5s (load from disk + move to device) | ~0.001s (inference only) |
| **Embedding Model** (SentenceTransformer `intfloat/multilingual-e5-base`) | Lazy singleton in `intent_ranker.py` (`_embed_model = None`) | ~5-15s (download or load from cache) | ~0.01-0.05s (encode only) |
| **Embedding Model** (SentenceTransformer) in domain router | **Separate** lazy singleton in `selector.py` (`_embed_model = None`) | ~5-15s (loads the **same model again**) | ~0.01-0.05s |
| **Intent Embeddings** | Computed once, pickled to disk (`EMBEDDING_CACHE_DIR`) | ~0.1-1s (compute + save) | ~0.01s (load from pickle) |
| **Domain Registry** | Module-level singleton (`_registry = None`) | ~0.01s (JSON load) | Free |
| **Domain Resources** (profiles, intents, templates) | Per-domain singleton dict (`_domain_resources`) | ~0.01-0.05s per domain (file I/O) | Free |
| **LLM Model** (if `transformers` backend) | Lazy singleton with 4-bit quantization | **30-120s** (load + quantize) | Free |

**Critical finding**: The embedding model in `intent_ranker.py` and `selector.py` uses **two separate singletons** for the same model (`intfloat/multilingual-e5-base`). If `use_embedding=True`, the same model is loaded into memory twice.

---

### 4. Sequential Bottlenecks (Parallelization Opportunities)

#### 4a. Steps 1 + 2: Schema Router and Intent Detection per candidate domain (lines 296-330)

```
for domain_id in candidate_domains:      # Step 1: schema routing
    rank_tables(...)                      # sequential per domain

for domain_id in candidate_domains:       # Step 2: intent detection
    rank_intents(...)                     # sequential per domain
```

These two loops are **independent of each other** and could run in parallel. When there are 2 candidate domains (the shortlist can return up to 2), this means 4 sequential operations that could be 2 parallel groups.

However, measured latency is 0.01-0.04s total, so **parallelization here would save negligible time** (~20ms).

#### 4b. Step 0 + Step 1 + Step 2: Domain routing, schema routing, intent detection

Domain routing must complete before schema/intent routing (because it determines candidate domains). This is a correct dependency. No opportunity here.

#### 4c. Step 3: Entity Extraction vs. Steps 1-2

Entity extraction (`extract_entities_local`) does not depend on domain routing results in theory -- it receives `domain_id` only to select regex patterns (banking vs. HRM). But the NER model itself (`ner_predict`) is domain-agnostic. This step **could** run in parallel with Steps 0-2 if the domain routing were done first or if NER were domain-agnostic.

In practice, entity extraction is called after domain is resolved (line 388: `extract_entities_local(question, domain_id=final_domain)`), creating a sequential dependency. On cold start, this adds 1.5s sequentially.

#### 4d. Step 6: Three validation gates are sequential

Structure validation, semantic validation, and EXPLAIN validation run one after another. Each can trigger an LLM retry. They **cannot** be parallelized because each retry modifies the SQL that the next gate validates.

This is the correct design -- but it means worst-case latency compounds: up to 3 sequential LLM calls.

#### 4e. No streaming or async I/O for LLM calls

`llm_sql_generator.py` uses synchronous `urllib.request.urlopen` with a 120-second timeout. There is no async alternative. The 120s timeout means a hung LLM endpoint blocks the entire pipeline for 2 minutes before failing.

---

### 5. Additional Findings

#### 5a. Template-first fast path works well

When template slot-filling completes successfully (`template_complete = True`), the LLM is skipped entirely (line 431-440). In the batch data, queries that hit this path show `sql_generation: 0.0`. This is the single most effective optimization already in place.

#### 5b. LLM timeout is 120s but typical response is 65s

The `urlopen(req, timeout=120)` in both OpenAI-compatible and Ollama backends uses a 120s timeout. Observed LLM calls take ~65s consistently. The timeout provides ~55s of headroom, which is appropriate. However, a failed LLM call wastes the full 120s before triggering fallback.

#### 5c. Entity extraction cold-start is domain-dependent

The NER model is loaded lazily on first call. If the NER model import fails (e.g., model files missing), the code falls back to regex patterns which are near-instant. The 1.5s cold-start only applies when the PhoBERT model loads successfully.

#### 5d. No request-level timeout

There is no overall timeout for `run_pipeline()`. A query could theoretically take 390+ seconds (3 LLM calls x 120s timeout + retries) without the caller being able to abort.

---

### Summary: Optimization Priority

| Priority | Issue | Expected Gain | Effort |
|----------|-------|---------------|--------|
| 1 | **LLM call latency (~65s each)** -- model inference speed or switching to a faster model | 50-70% total time reduction | High (infra) |
| 2 | **Add pipeline-level timeout** -- cap total execution at e.g., 120s | Prevents worst-case 390s hangs | Low |
| 3 | **Deduplicate embedding model singletons** -- `intent_ranker._embed_model` and `selector._embed_model` load the same model twice | Saves ~200-500MB RAM + 5-15s on first embedding call | Low |
| 4 | **Pre-warm NER model at startup** -- call `ner_predict("test")` during app init | Eliminates 1.5s cold-start for first user query | Low |
| 5 | **Run NER extraction in parallel with schema+intent routing** -- entity extraction is mostly domain-agnostic | Saves ~1.5s (cold) or ~0ms (warm) | Medium |
| 6 | **Reduce LLM timeout from 120s to 90s** -- typical calls finish in 65s | Faster failure detection, saves 30s on hung endpoint | Low |
| 7 | **Consider async LLM calls** -- use `aiohttp` instead of `urlopen` for non-blocking I/O | Enables parallel validation retries (if safe) | High |
