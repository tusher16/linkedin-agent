# AGENTS.md

Briefs any AI coding assistant (Claude, Codex, Gemini, Copilot, etc.) on this codebase.
Read this before touching any code.

---

## Project

Autonomous LinkedIn content agent. Author: **Mohammad Obaidullah Tusher** (AI Engineer, Berlin).
Stack: Python 3.12 · LangGraph 1.x · pgvector · FastAPI · Streamlit · PostgreSQL.
Self-hosted on Linux via Cloudflare Tunnel. Publishes to LinkedIn via PostBoost API.

**Authoritative docs (read before coding):**
- `IMPLEMENTATION_PLAN.md` — day-by-day plan with test gates
- `TASK.md` — checklist of what's done / in-progress / pending
- `WALKTHROUGH.md` — what has been built and tested

---

## Project Structure

```
src/linkedin_agent/
├── schemas/        # Pydantic models — AgentState, all I/O contracts
├── tools/          # @tool functions, one per file
├── graph/          # LangGraph StateGraph + node functions
├── api/            # FastAPI app + JWT auth
├── db/             # session.py, models.py, repository.py — async SQLAlchemy
├── dashboard/      # Streamlit app (talks to FastAPI only — never DB directly)
└── guardrails/     # Prompt-injection detection (Day 8)

alembic/            # at REPO ROOT — async migrations
├── env.py
├── versions/0001_init.py    # vector ext + 3 tables
└── alembic.ini  (one level up at repo root)

tests/
├── unit/           # Pure logic, no I/O — schemas, tools, graph nodes
├── integration/    # DB + LLM cassettes (VCR) — repository, graph_flow, migrations
├── e2e/            # Full agent run against real services
├── security/       # Auth, injection, rate-limit tests
└── eval/           # Cross-model eval (Gemini drafts, GPT-4o-mini judges)

scripts/
├── refresh.sh      # Update graphify graph + pgvector RAG index together
├── run_eval.py     # Full 15-topic eval run → LangSmith
└── smoke_publish.py # Manual PostBoost test publish

docs/
├── adr/            # Architecture Decision Records — read before reconsidering design
├── rules/          # Extended hard rules (security.md, coding.md)
└── v2-roadmap.md   # Parked features — anything not in the 14-day plan goes here
```

---

## Architecture Rules (never violate)

1. **Typed I/O everywhere.** Every tool, node, and endpoint takes and returns Pydantic models. No raw `str`/`dict` across module boundaries.
2. **Bounded loops.** Re-draft loop: ≤2 iterations AND ≤$0.05/run. Both checked inside LangGraph state on every pass.
3. **Outline before draft.** Never call `draft_post` without an approved outline.
4. **Context-grounded.** Every LLM call retrieves from pgvector. No static file loading after Day 4.
5. **LangSmith always on.** `LANGCHAIN_TRACING_V2=true`. Never bypass tracing.
6. **VCR cassettes for LLM tests.** Commit cassettes; CI must run free (no live LLM calls in CI).
7. **Coverage gate.** ≥75% line coverage on `src/`; ≥85% on `schemas/` and `tools/`.
8. **Dashboard → API → DB.** Dashboard never touches DB or LLM directly. Keeps v2 additions purely additive.

---

## Coding Conventions

See [`docs/rules/coding.md`](docs/rules/coding.md) for full detail. Summary:

- **Functions:** ≤40 lines, one responsibility, verb-noun names (`build_outline`, `publish_post`)
- **Pydantic models:** `CamelCase`; fields `snake_case`; always use `model_validator` over raw `__init__`
- **Imports:** stdlib → third-party → local, separated by blank lines; absolute paths only
- **Tests:** Arrange / Act / Assert with blank lines between; test one behaviour per test function
- **Comments:** Only when the WHY is non-obvious; no docstring novels; no TODO without a ticket
- **No print statements** in `src/` — use `structlog` logger; `print()` only in scripts
- **Type hints on every function** — no `Any` unless unavoidable, document why if used

---

## Security Rules

See [`docs/rules/security.md`](docs/rules/security.md) for full detail. Hard limits:

- **Never commit `.env`** or any file with a real key. `.env.template` is placeholders only.
- **All FastAPI endpoints require `Depends(get_current_user)`** unless explicitly marked public.
- **Sanitise every user input** before it reaches an LLM prompt (guardrails node runs first).
- **Rate-limit all public API routes** (`slowapi`; configured in `api/middleware.py`).
- **No auto-connection-request code** — LinkedIn ToS violation; reject any PR containing it.
- **No feature after Day 5** — new ideas go to `docs/v2-roadmap.md`, not into the codebase.

---

## Environment

- **Python 3.12** — do not upgrade (3.14 caused import hangs in early experiments)
- **Package manager: uv** — `pyproject.toml` + `uv.lock`. Do not regenerate `requirements.txt`.
- **Venv:** `.venv/bin/python3` (path has spaces — always quote in bash)
- **Dev DB:** `docker compose up -d postgres-pgvector` then `alembic upgrade head`
- **Run command:** `uv run <command>` or `source .venv/bin/activate`
- **graphify is a global tool, NOT a project dep.** Install with `uv tool install graphifyy`. Never `uv add graphifyy` — its 27 tree-sitter packages make `import pytest` take 90+ seconds.

### Required `.env` keys

```
GOOGLE_API_KEY            # Drafter LLM (Gemini 2.5 Flash)
OPENROUTER_API_KEY        # Judge LLM (GPT-4o-mini)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=linkedin-agent
LANGCHAIN_API_KEY
POSTBOOST_API_KEY
JWT_SECRET
ADMIN_USERNAME
ADMIN_PASSWORD_HASH       # bcrypt hash
DATABASE_URL              # postgresql+asyncpg://...
B2_ACCESS_KEY_ID          # Backblaze B2 nightly backup
B2_SECRET_ACCESS_KEY
```

---

## Common Tasks

| Task | Where to start |
|---|---|
| Add a tool | `schemas/` → `tools/<name>.py` → register in `graph/` → unit test + cassette |
| Add a node | Type with `AgentState` → unit test → wire in `graph/builder.py` → integration test |
| Add an endpoint | Pydantic models → `api/routes/` → 4 tests (200, 401, 422, 404) |
| Re-record cassettes | `uv run pytest --record-mode=rewrite path/to/test` → commit cassette |
| Add a migration | `alembic revision -m "<msg>"` → edit `alembic/versions/<rev>.py` → `alembic upgrade head` |
| Run eval | `uv run python scripts/run_eval.py` → updates README eval table |
| Update context memory | `./scripts/refresh.sh` (graph + RAG together) |
