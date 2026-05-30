# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in credentials
```

## Running

```bash
python main.py                             # interactive chat loop
python main.py -q "Top 5 customers by revenue"  # single query, then exit
python main.py -q "..." --quiet            # suppress per-step agent logs
```

## Architecture

The pipeline runs sequentially inside `agents/orchestrator.py:answer_question()`. Each stage is a plain function call — there is no framework, no message bus, no async.

```
User question
  → agents/schema.py       identify_relevant_schema()   [Haiku — filters INFORMATION_SCHEMA to relevant tables]
  → agents/sql_gen.py      generate_sql()               [Opus 4.8 — produces SELECT SQL]
  → agents/validator.py    validate_sql()               [Snowflake EXPLAIN — syntax/semantic check, no credits]
  → db/connection.py       execute_query()              [runs against Snowflake]
  → agents/interpreter.py  interpret_results()          [Opus 4.8 — plain-language summary]
```

On validation failure the orchestrator retries `generate_sql` with the error appended (`previous_error` param). On execution failure it calls `agents/error_recovery.py:suggest_fix()` first, then retries. `MAX_RETRIES = 3` in `orchestrator.py`.

### Snowflake connection

`db/connection.py` opens a new connection per call (not pooled). `execute_query()` uses `DictCursor` so rows come back as `dict[str, Any]` with **uppercase** column-name keys (Snowflake default). `explain_query()` prepends `EXPLAIN` to the SQL — raises `snowflake.connector.errors.ProgrammingError` on bad SQL, which `validate_sql()` catches.

### Schema cache

`db/schema_cache.py` keeps a module-level dict with a 5-minute TTL. It queries `information_schema.columns WHERE table_schema = CURRENT_SCHEMA()`. Call `invalidate()` to force a refresh (e.g. after a DDL change).

### Claude API usage

All agents initialise `anthropic.Anthropic()` at **module import time** as `_client`. This is why `load_dotenv()` in `main.py` must run before any `agents.*` import.

- **Schema agent** — `claude-haiku-4-5`, no thinking (cheap lookup task)
- **SQL gen, interpreter, error recovery** — `claude-opus-4-8`, `thinking: {"type": "adaptive"}`, `effort: "high"`
- **SQL gen system prompt** carries `cache_control: {"type": "ephemeral"}` so the static instruction is cached across repeated calls within the 5-minute TTL window

### Adding a new agent

1. Create `agents/your_agent.py` with a module-level `_client = anthropic.Anthropic()` and a single public function.
2. Import and call it in `agents/orchestrator.py`.
3. No registration or factory needed.

## Environment variables

All required vars are listed in `.env.example`. `SNOWFLAKE_SCHEMA` defaults to `PUBLIC` if omitted. The Anthropic SDK reads `ANTHROPIC_API_KEY` automatically; it does not need to be passed to `Anthropic()` explicitly.
