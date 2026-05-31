# CLAUDE.md

Guidance for Claude Code when working in this repository.

---

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # fill in credentials — see section below
cd frontend && npm install
```

## Running locally

```bash
# Terminal 1 — backend (auto-reloads on file change)
uvicorn api.main:app --reload

# Terminal 2 — frontend dev server
cd frontend && npm run dev
```

Open http://localhost:5174. The frontend calls `/query` and `/audit` on the
same origin so the backend must be on port 8000.

**CLI mode** (no frontend):
```bash
python main.py                                  # interactive loop
python main.py -q "Top 5 customers by revenue"  # single query, then exit
python main.py -q "..." --quiet                 # suppress per-step logs
```

---

## Architecture

```
User question + conversation history
  │
  ▼
agents/schema.py         identify_relevant_schema()  [Haiku — filter INFORMATION_SCHEMA]
  │
  ▼
agents/router.py         choose_model()              [heuristic — Haiku vs Opus]
  │
  ▼
agents/sql_gen.py        generate_sql()              [chosen model — produces SELECT SQL]
  │
  ▼
agents/validator.py      validate_sql()              [1. read-only check  2. EXPLAIN]
  │        │
  │   invalid (retry, max 3)
  │        │
  │        └──────────────────────────────► back to sql_gen
  │
  ▼
db/result_cache.py       result_cache.get(sql)       [cache hit → skip Snowflake]
  │
  ▼ (cache miss)
db/connection.py         execute_query()             [pool + circuit breaker]
  │        │
  │     error (retry, max 3)
  │        │
  │        ▼
  │   agents/error_recovery.py  suggest_fix()        [Opus — rewrite SQL]
  │        │
  │        └──────────────────────────────► back to sql_gen
  │
  ▼
agents/interpreter.py    interpret_results()         [same model as sql_gen]
  │
  ▼
agents/pii.py            scan(rows)                  [regex PII detection]
  │
  ▼
db/audit.py              record(...)                 [SQLite WAL + stdout JSON]
  │
  ▼
QueryResult (answer, sql, rows, row_count, cache_hit, pii_detected)
```

Each stage is a **plain synchronous function call** — no framework, no message
bus, no async.

---

## Module reference

### agents/

| File | Function | Model | Purpose |
|------|----------|-------|---------|
| `schema.py` | `identify_relevant_schema()` | Haiku | Filters full schema to relevant tables |
| `router.py` | `choose_model()` | — | Regex heuristic → Haiku or Opus |
| `sql_gen.py` | `generate_sql()` | Haiku / Opus | Produces SELECT SQL |
| `validator.py` | `validate_sql()` | — | Read-only check + EXPLAIN |
| `error_recovery.py` | `suggest_fix()` | Opus | Rewrites SQL on execution failure |
| `interpreter.py` | `interpret_results()` | Haiku / Opus | Plain-language summary |
| `pii.py` | `scan()` | — | Regex PII detection on result rows |
| `orchestrator.py` | `answer_question_full()` | — | Coordinates the full pipeline |

### db/

| File | Purpose |
|------|---------|
| `connection.py` | `execute_query()` and `explain_query()` via pool + circuit breaker |
| `pool.py` | Lazy-initialised thread-safe Snowflake connection pool |
| `circuit_breaker.py` | CLOSED/OPEN/HALF_OPEN state machine protecting Snowflake calls |
| `result_cache.py` | TTL cache keyed by normalised SQL; skips Snowflake on hit |
| `schema_cache.py` | 5-minute TTL cache for INFORMATION_SCHEMA queries |
| `audit.py` | File-based SQLite WAL audit log + stdout JSON streaming |

### api/

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app — auth, rate limiting, PII scan, audit, SPA serving |
| `rate_limit.py` | Per-IP sliding-window rate limiter |

---

## Key design decisions

### load_dotenv() must run first
All agents and db modules initialise clients at **import time**. `api/main.py`
calls `load_dotenv()` at the very top, before any `agents.*` or `db.*` import.
The pool and Anthropic clients read env vars at initialisation.

### Connection pool is lazily initialised
`db/pool.py` creates connections on first `acquire()` call, not at module import
time. This ensures env vars are loaded before the pool tries to connect.

### Model routing
`agents/router.py` uses regex heuristics to classify questions as simple or
complex and returns a model ID. The same model is used for both `sql_gen` and
`interpreter` in a given request so the complexity assessment is consistent.

Simple (Haiku): `list tables`, `count rows`, `what are the columns in X`
Complex (Opus): aggregations, trends, year-over-year, multi-table analysis

### Result caching
Cache key = SHA-256 of normalised SQL (lowercased, whitespace-collapsed).
Cached at the SQL execution level, not the question level — so different
phrasings that generate the same SQL still hit the cache.
Cache is in-process; with multiple workers each worker has its own cache.
For shared cache across workers, replace with Redis.

### Circuit breaker
5 consecutive Snowflake failures → OPEN (requests rejected for 60s).
After 60s → HALF_OPEN (one probe allowed).
Success → CLOSED. Failure → OPEN again.
Configurable via CB_FAILURE_THRESHOLD / CB_RECOVERY_TIMEOUT env vars.

### Audit log
File-based SQLite at AUDIT_DB_PATH (/tmp/audit.db by default). WAL mode
enables safe concurrent writes from multiple uvicorn workers. Every record
is also streamed as JSON to stdout for permanent capture by Railway logs.

### Read-only SQL enforcement
`validator.py` rejects anything not starting with SELECT or WITH (CTEs).
Blocked keywords: INSERT UPDATE DELETE DROP CREATE ALTER TRUNCATE MERGE CALL EXEC.
This runs before EXPLAIN so blocked queries never reach Snowflake.

### PII detection
`agents/pii.py` scans result rows for email, SSN, phone, credit card patterns
using compiled regex. Detected types are included in the API response
(`pii_detected`) and audit log. The UI shows a warning banner.

### Rate limiting
Sliding window (60s) per client IP. Default 20 RPM, configurable via
RATE_LIMIT_RPM. In-process — multiply by worker count for effective limit.
Rejected requests receive HTTP 429 with Retry-After header.

### Multiple workers
Dockerfile runs `uvicorn --workers 2`. Each worker is an independent Python
process. In-process state (cache, rate limiter, circuit breaker) is not shared.
This is acceptable at current scale; add Redis for shared state when needed.

---

## Environment variables

All optional variables have safe defaults. Required variables are marked *.

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` * | — | Anthropic API key |
| `SNOWFLAKE_ACCOUNT` * | — | `org-account.region` |
| `SNOWFLAKE_USER` * | — | Snowflake username |
| `SNOWFLAKE_PASSWORD` * | — | Snowflake password |
| `SNOWFLAKE_DATABASE` * | — | Target database |
| `SNOWFLAKE_WAREHOUSE` * | — | Compute warehouse |
| `SNOWFLAKE_SCHEMA` | `PUBLIC` | Default schema |
| `APP_PASSWORD` | _(none)_ | Web UI password gate |
| `SNOWFLAKE_POOL_SIZE` | `5` | Pool connection count |
| `SNOWFLAKE_ACQUIRE_TIMEOUT` | `30` | Seconds to wait for pool slot |
| `QUERY_TIMEOUT_SECONDS` | `120` | Snowflake network timeout |
| `RESULT_CACHE_TTL` | `300` | Cache TTL in seconds |
| `RESULT_CACHE_MAX` | `200` | Max cached SQL entries |
| `RATE_LIMIT_RPM` | `20` | Max requests/minute/IP |
| `AUDIT_DB_PATH` | `/tmp/audit.db` | SQLite audit DB path |
| `CB_FAILURE_THRESHOLD` | `5` | Failures before circuit opens |
| `CB_RECOVERY_TIMEOUT` | `60` | Seconds before recovery probe |

---

## Adding a new agent

1. Create `agents/your_agent.py` with a module-level `_client = anthropic.Anthropic()`
   and a single public function.
2. Import and call it in `agents/orchestrator.py`.
3. No registration, factory, or framework needed.

## Adding a new API endpoint

Add a route function in `api/main.py` **above** the `/{full_path:path}` wildcard
(which serves the SPA). Call `_check_password()` for protected endpoints.

## Invalidating the schema cache

```python
from db.schema_cache import invalidate
invalidate()   # forces a fresh INFORMATION_SCHEMA query on next request
```

## Invalidating the result cache

```python
from db.result_cache import result_cache
result_cache.invalidate()          # flush all
result_cache.invalidate(sql)       # flush one SQL entry
```

## Checking the circuit breaker state

```python
from db.circuit_breaker import snowflake_breaker
print(snowflake_breaker.state)   # "closed" | "open" | "half_open"
```
