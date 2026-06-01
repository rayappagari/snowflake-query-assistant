# Snowflake Query Assistant

Ask questions about your Snowflake data in plain English. A multi-agent pipeline powered by Claude translates your question into SQL, runs it against Snowflake, and returns a plain-language answer — with syntax-highlighted SQL, a scrollable results table, and CSV export.

**Live demo:** https://laudable-clarity-production.up.railway.app
**Client overview:** [PRODUCT.md](PRODUCT.md)

---

## Features

| | |
|---|---|
| **Natural language queries** | Ask anything — no SQL knowledge required |
| **Conversation memory** | Follow-up questions resolve correctly ("filter that by region", "now just the top 3") |
| **Domain skills** | Keyword-matched skills inject domain-specific SQL patterns and analysis guidance for revenue, customers, inventory, cohorts, coding standards, and performance optimization |
| **Model routing** | Simple lookups use Haiku; complex analytics use Opus 4.8 — automatically |
| **Result caching** | Identical SQL skips Snowflake entirely; ⚡ badge shown on cached responses |
| **Syntax-highlighted SQL** | Collapsible SQL block with highlight.js |
| **CSV export** | Download any result table in one click |
| **Query history** | Sidebar tracks every question in the session |
| **Audit log** | Every query logged with status, latency, row count, cache hit, and PII flags — viewable in sidebar |
| **Read-only enforcement** | Only `SELECT`/`WITH` queries reach Snowflake — writes blocked at the validator |
| **PII detection** | Results scanned for email, SSN, phone, credit card — warning shown in UI |
| **JWT authentication** | Individual user accounts with bcrypt passwords and JWT tokens (PostgreSQL-backed) |
| **User management UI** | Admin panel to add, edit, activate/deactivate, reset passwords, and delete users |
| **Password fallback** | Shared `APP_PASSWORD` gate when PostgreSQL is not configured |
| **Rate limiting** | 20 req/min/IP sliding window; Redis-backed when available |
| **Circuit breaker** | Stops hammering Snowflake after 5 consecutive failures; auto-recovers |
| **Prometheus metrics** | `/metrics` endpoint — query volume, latency, cache hits, PII, circuit state |
| **5 themes** | Dark, Midnight, Ocean, Sunset, Light — persisted to `localStorage` |
| **Mobile responsive** | Sidebar becomes a drawer on small screens |

---

## Architecture

```mermaid
flowchart TD
    User(["🧑 User question + conversation history"])

    subgraph Auth ["Auth layer"]
        AM{"Auth mode?"}
        JWT["JWT bearer token\n(individual accounts)"]
        PW["APP_PASSWORD\n(shared gate)"]
    end

    subgraph Agents ["Multi-Agent Pipeline"]
        direction TB
        R["🧭 Router\n─────────\nHaiku vs Opus 4.8\n(regex heuristic)"]
        SK["🎯 Skills Router\n─────────────\nKeyword match →\ndomain skill"]
        A["🔍 Schema Agent\n─────────────\nFilters INFORMATION_SCHEMA\n(Claude Haiku)"]
        B["✍️ SQL Gen\n─────────────\nSELECT query +\nconversation context\n+ skill hints"]
        C{"🔎 Validator\n─────────────\n1. Read-only check\n2. Snowflake EXPLAIN"}
        CA["🗄️ Result Cache\n─────────────\nRedis / in-process TTL\n(skip Snowflake on hit)"]
        D["⚙️ Executor\n─────────────\nSnowflake via pool\n+ circuit breaker"]
        E["💬 Interpreter\n─────────────\nPlain-language summary\n+ conversation context"]
        F["🛠️ Error Recovery\n─────────────\nRewrite SQL on\nexecution failure"]
        P["🔍 PII Scanner\n─────────────\nemail · SSN · phone\ncredit card"]
        G[("📋 Audit Log\n─────────────\nPostgreSQL / SQLite\n+ stdout JSON")]
        M[("📊 Metrics\n─────────────\nPrometheus /metrics\nGrafana-ready")]
    end

    Result(["✅ Answer + SQL + Results + PII warning"])

    User --> AM
    AM -- JWT mode --> JWT --> R
    AM -- password mode --> PW --> R
    R --> SK
    SK --> A --> B --> C
    C -- blocked --> Result
    C -- "invalid (retry ×3)" --> B
    C -- valid --> CA
    CA -- hit --> E
    CA -- miss --> D
    D -- success --> E
    D -- "error (retry ×3)" --> F --> B
    E --> P --> Result
    P --> G
    G --> M
```

Each stage is a plain synchronous function call — no framework, no message bus, no async.

| Agent | Model | Role |
|---|---|---|
| Router | — | Regex heuristic selects Haiku or Opus per query |
| Skills Router | — | Keyword scoring selects a domain skill (revenue, customers, inventory, cohorts, coding standards, performance) or none |
| Schema | Haiku | Filters `INFORMATION_SCHEMA` to relevant tables |
| SQL Gen | Haiku / Opus 4.8 | Writes a `SELECT` query; injects skill hints + last 5 conversation turns |
| Validator | — | Enforces read-only; then runs Snowflake `EXPLAIN` |
| Error Recovery | Opus 4.8 | Rewrites SQL on execution failure |
| Interpreter | Haiku / Opus 4.8 | Summarises results with skill analysis focus; uses last 3 conversation turns |
| PII Scanner | — | Regex scan for email, SSN, phone, credit card |

---

## Stack

- **Backend** — Python 3.11, FastAPI, `snowflake-connector-python`, Anthropic SDK
- **Frontend** — React 18, Vite, highlight.js
- **Auth** — python-jose (JWT), bcrypt, PostgreSQL user store
- **Cache** — Redis (cross-worker) + in-process TTL fallback
- **Observability** — Prometheus client, PostgreSQL + SQLite audit log
- **Deployment** — Railway (Dockerfile: Node builds React, Python serves via FastAPI, 2 workers)

---

## Local setup

```bash
pip install -r requirements.txt
cp .env.example .env        # fill in credentials — see env vars section below
cd frontend && npm install
```

**Run locally:**

```bash
# terminal 1 — backend
uvicorn api.main:app --reload

# terminal 2 — frontend
cd frontend && npm run dev
```

Open `http://localhost:5174`.

**CLI mode** (no frontend):

```bash
python main.py                                    # interactive chat loop
python main.py -q "Top 5 customers by revenue"   # single query, then exit
python main.py -q "..." --quiet                   # suppress per-step logs
```

---

## Environment variables

Copy `.env.example` to `.env`. Required variables are marked *.

### Core (required)
```
ANTHROPIC_API_KEY=sk-ant-...          *
SNOWFLAKE_ACCOUNT=org-account.region  *
SNOWFLAKE_USER=your_username          *
SNOWFLAKE_PASSWORD=your_password      *
SNOWFLAKE_DATABASE=your_database      *
SNOWFLAKE_WAREHOUSE=your_warehouse    *
SNOWFLAKE_SCHEMA=PUBLIC               # optional, defaults to PUBLIC
```

### Authentication
```
APP_PASSWORD=your_password            # simple password gate (no DB needed)

# JWT mode — activated automatically when DATABASE_URL is set
JWT_SECRET_KEY=<openssl rand -hex 32> # required in prod; random default invalidates on restart
JWT_EXPIRE_HOURS=8
ADMIN_USERNAME=admin                  # auto-created admin on first startup
ADMIN_PASSWORD=strong-password
```

### PostgreSQL (enables JWT auth + user management + persistent audit log)
```
DATABASE_URL=postgresql://user:pass@host:5432/dbname
# On Railway: add a PostgreSQL service — URL is injected automatically
```

### Redis (enables cross-worker shared cache + rate limiting)
```
REDIS_URL=redis://localhost:6379
# On Railway: add a Redis service — URL is injected automatically
```

### Performance
```
SNOWFLAKE_POOL_SIZE=5           # persistent Snowflake connections
SNOWFLAKE_ACQUIRE_TIMEOUT=30    # seconds to wait for a pool slot
QUERY_TIMEOUT_SECONDS=120       # Snowflake network timeout
RESULT_CACHE_TTL=300            # seconds to cache identical SQL results
RESULT_CACHE_MAX=200            # max cached entries (evicts oldest)
RATE_LIMIT_RPM=20               # max requests per minute per IP
```

### Governance
```
AUDIT_DB_PATH=/tmp/audit.db     # SQLite fallback audit DB path
CB_FAILURE_THRESHOLD=5          # failures before circuit opens
CB_RECOVERY_TIMEOUT=60          # seconds before recovery probe
```

### Secrets manager (optional)
```
AWS_SECRET_ARN=arn:aws:secretsmanager:...   # AWS Secrets Manager
VAULT_ADDR=https://vault.example.com        # HashiCorp Vault
VAULT_TOKEN=s.xxxxxx
```

---

## Deploying to Railway

1. Push to GitHub
2. Railway → New Project → Deploy from GitHub repo
3. Set required environment variables in the Railway dashboard
4. Railway auto-detects the `Dockerfile` — no extra config needed
5. Settings → Networking → Generate Domain for a public URL

**Enable JWT auth + user management:**
```
Railway dashboard → New Service → Database → PostgreSQL
```
`DATABASE_URL` is injected automatically. Set `JWT_SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD` and redeploy — the admin account is created on first startup.

**Enable Redis-backed cache + rate limiting:**
```
Railway dashboard → New Service → Database → Redis
```
`REDIS_URL` is injected automatically. Redeploy to activate.

**Enable Prometheus metrics:**
- `GET /metrics` is always available (no config needed)
- Point Prometheus at it using `monitoring/prometheus.yml`
- Alert rules: `monitoring/alerts.yml`
- Connect Grafana to Prometheus for dashboards

---

## API endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | None | Liveness probe |
| `GET` | `/verify` | Password | Validate app password |
| `GET` | `/metrics` | None | Prometheus metrics |
| `POST` | `/auth/login` | — | Exchange credentials for JWT |
| `POST` | `/auth/register` | Admin JWT | Create a new user |
| `GET` | `/auth/me` | JWT | Current user profile |
| `GET` | `/auth/mode` | — | Returns `jwt` or `password` |
| `GET` | `/auth/users` | Admin JWT | List all users |
| `PATCH` | `/auth/users/{username}` | Admin JWT | Update role, status, or password |
| `DELETE` | `/auth/users/{username}` | Admin JWT | Delete a user |
| `POST` | `/query` | JWT / Password | Run a natural language query |
| `GET` | `/audit` | JWT / Password | Retrieve audit log entries |

---

## Governance

| Control | Implementation |
|---|---|
| **Read-only enforcement** | `validator.py` rejects anything not starting with `SELECT`/`WITH`; blocks all write keywords |
| **JWT authentication** | Individual accounts with bcrypt passwords + python-jose JWT tokens; PostgreSQL-backed |
| **User management** | Full CRUD via `/auth/users/*` endpoints + built-in admin UI |
| **Password gate** | `APP_PASSWORD` fallback when PostgreSQL is not configured |
| **Rate limiting** | 20 req/min/IP sliding window; Redis sorted-set when available, in-process fallback |
| **Circuit breaker** | 5 failures → OPEN (60s) → HALF_OPEN → CLOSED |
| **PII detection** | Results scanned for email, SSN, phone, credit card before returning to client |
| **Audit logging** | PostgreSQL (persistent) + SQLite fallback + JSON stdout streaming |
| **Result caching** | TTL cache keyed by normalised SQL; Redis-backed when available |
| **Prompt caching** | SQL Gen system prompt carries `cache_control: ephemeral` |
| **Secrets manager** | `config/secrets.py`: AWS Secrets Manager → Vault → env vars |

---

## Project structure

```
agents/
  schema.py           # table discovery (Haiku)
  router.py           # model complexity routing (Haiku vs Opus)
  sql_gen.py          # SQL generation with conversation history + skill hints
  validator.py        # read-only enforcement + EXPLAIN validation
  interpreter.py      # results summarisation with conversation history + skill focus
  error_recovery.py   # SQL correction on execution failure
  pii.py              # PII detection (email, SSN, phone, credit card)
  orchestrator.py     # pipeline coordinator, retry logic, cache integration
skills/
  base.py             # Skill dataclass (name, prompt_hint, sql_hint, keywords, postprocess)
  router.py           # match_skill() — keyword scoring → domain skill or None
  revenue_trend.py    # revenue, sales, YoY/MoM/QoQ trend analysis
  customer_segmentation.py  # RFM, LTV, churn, top-N customers
  inventory_analysis.py     # stockout risk, turnover rate, reorder alerts
  cohort_analysis.py        # retention cohorts, funnel conversion, drop-off
  coding_standards.py       # SQL/schema naming conventions, anti-patterns, quality audits
  performance_optimization.py  # slow queries, credit cost, partition pruning, disk spillage
api/
  main.py             # FastAPI app — auth, rate limiting, PII scan, audit, SPA
  auth.py             # JWT auth, full user CRUD, /auth/* routes
  metrics.py          # Prometheus metrics definitions and helpers
  rate_limit.py       # sliding-window rate limiter (Redis + in-process)
config/
  secrets.py          # secrets loader (AWS Secrets Manager → Vault → env)
db/
  connection.py       # Snowflake execute/explain via pool + circuit breaker
  pool.py             # lazy-init thread-safe Snowflake connection pool
  circuit_breaker.py  # CLOSED/OPEN/HALF_OPEN state machine
  result_cache.py     # TTL result cache (Redis + in-process two-tier)
  schema_cache.py     # 5-minute TTL cache for INFORMATION_SCHEMA
  audit.py            # audit log (PostgreSQL + SQLite fallback + stdout)
  postgres.py         # PostgreSQL connection pool + schema migrations
  redis_client.py     # lazy Redis client
frontend/
  src/App.jsx         # React chat UI — login, user mgmt, themes, sidebar, audit
  src/App.css         # CSS custom properties, 5 theme definitions
monitoring/
  prometheus.yml      # Prometheus scrape config
  alerts.yml          # alert rules (error rate, circuit, latency, rate spike)
Dockerfile            # multi-stage: Node builds React, Python serves, 2 workers
main.py               # CLI entrypoint
PRODUCT.md            # client-facing feature overview (non-technical)
```
