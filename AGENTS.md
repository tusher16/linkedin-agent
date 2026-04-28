# AGENTS.md — AI Assistant Handoff

This file briefs any AI coding assistant (Claude, Codex, Gemini, OpenCode, etc.)
on how to continue work without re-deriving context. **Read this first.**

---

## Project at a glance

Autonomous LinkedIn content agent. Author: **Mohammad Obaidullah Tusher**
(AI Engineer, Berlin). Stack: Python 3.12 · LangGraph 1.x · LangSmith · pgvector ·
FastAPI · Streamlit · Postgres. Self-hosted on a Linux home server via
Cloudflare Tunnel. Publish target: real LinkedIn via [PostBoost](https://postboost.co).

---

## Canonical documents (in priority order)

| File | Purpose | When to read |
|---|---|---|
| [`docs/superpowers/specs/2026-04-26-linkedin-agent-2week-mvp-design.md`](docs/superpowers/specs/2026-04-26-linkedin-agent-2week-mvp-design.md) | **Authoritative design spec.** Architecture, 14-day plan, testing procedure, cuts, risks. | Before any code change. |
| [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) | Day-by-day plan with test gates per day. | When picking up the next task. |
| [`TASK.md`](TASK.md) | Checklist mirroring the implementation plan. | To find what's already done. |
| [`WALKTHROUGH.md`](WALKTHROUGH.md) | What's been built and tested so far. | To pick up where work left off. |
| [`README.md`](README.md) | Public-facing repo doc. | If editing public surface. |
| [`docs/adr/`](docs/adr/) | Architecture decision records. | When reconsidering a load-bearing decision. |
| [`docs/v2-roadmap.md`](docs/v2-roadmap.md) | Parked v2 features. | If asked to add something not in v1. |

If those documents conflict, the **design spec wins**. Open a PR to fix the
conflict before implementing the conflicting feature.

---

## Current status

- ✅ **Tutorial-stage scripts (Phase 1-4 of the old plan)**: `archive/01_base_agent.py`, `archive/02_agent_tools.py`. They work. They are NOT the production codebase. Refactored into `src/linkedin_agent/` on Day 1.
- 📐 **Planning complete (2026-04-26)**: design spec approved by author.
- 🚀 **Ready to start Day 0** (pre-flight: rotate keys, `git init`, package skeleton, `pyproject.toml`).

---

## What to build next

Whatever's marked `🔄 in_progress` in [`TASK.md`](TASK.md). If nothing is, start
with the next `⏳ pending` item in the order they appear. Do not skip ahead —
day order is dependency order (e.g., schemas come before graph; graph comes
before API).

---

## Architecture principles (DO NOT VIOLATE)

1. **Typed I/O everywhere.** Every tool, every node, every API endpoint takes and returns Pydantic models. No raw `str`/`dict` exchanges across module boundaries.
2. **Bounded loops.** The re-draft loop has both an iteration cap (≤2) and a cost cap ($0.05/run). Both are checked inside the LangGraph state on every iteration.
3. **Outline-first.** Never call `draft_post` without an approved outline. Token waste is real.
4. **Context-grounded.** Every LLM call retrieves from pgvector. No generic outputs. Static `my_context.md` loading is **dead** as of Day 4.
5. **LangSmith always on.** `LANGCHAIN_TRACING_V2=true`. Do not bypass tracing for "convenience."
6. **Cassettes for LLM tests.** Tests that hit an LLM use `pytest-recording` cassettes committed to the repo. CI must run free.
7. **Coverage gate.** ≥ 75% line coverage on `src/`, ≥ 85% on `schemas/` + `tools/`. CI enforces this.
8. **Bounded units talk through interfaces.** Dashboard talks to FastAPI only — never directly to the DB or LLM. This makes adding Telegram (v2) purely additive.

---

## Hard rules

- **No new feature ideas accepted after Day 5.** They go to [`docs/v2-roadmap.md`](docs/v2-roadmap.md). Period.
- **No auto-connection-request sub-agent.** It's a LinkedIn ToS violation. The repo will not contain that code.
- **Never commit `.env`** or any file containing a real API key. `.env.template` is placeholders only.
- **Never amend an existing git commit** without explicit author permission. Always make a new commit.
- **Never bypass `pre-commit`** (`--no-verify` is a senior anti-pattern; if a hook fails, fix the underlying issue).

---

## Environment

- Python: **3.12** (3.14 caused import hangs in early experiments — do not upgrade).
- Package manager: **uv** with `pyproject.toml` + `uv.lock`. Do not regenerate `requirements.txt`.
- Local infra: `docker compose up -d postgres-pgvector` brings up the dev DB.
- Activate venv: `source .venv/bin/activate` or use `uv run <command>`.

### Required `.env` keys

```
GOOGLE_API_KEY            # Drafter LLM (Gemini)
OPENROUTER_API_KEY        # Judge LLM (GPT-4o-mini via OpenRouter)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=linkedin-agent
LANGCHAIN_API_KEY         # LangSmith
POSTBOOST_API_KEY         # Real LinkedIn publish
JWT_SECRET                # FastAPI auth
ADMIN_USERNAME            # Single admin user (no signup in v1)
ADMIN_PASSWORD_HASH       # bcrypt hash
DATABASE_URL              # postgresql+asyncpg://...
B2_ACCESS_KEY_ID          # Backblaze B2 for nightly pg_dump
B2_SECRET_ACCESS_KEY
```

---

## Key files (post-Day 1 layout)

```
src/linkedin_agent/
├── schemas/__init__.py            # AgentState, OutlineOutput, DraftOutput,
│                                  # ReviewOutput, PostStatus enum
├── tools/                         # @tool functions; one per file
├── graph/                         # StateGraph + node functions
├── api/                           # FastAPI app + auth
├── db/                            # SQLAlchemy + Alembic + repository
└── dashboard/                     # Streamlit app

tests/
├── unit/ · integration/ · e2e/ · security/ · eval/
└── conftest.py                    # Centralized fixtures

scripts/
├── run_eval.py                    # Manual full eval
└── smoke_publish.py               # Manual real PostBoost publish

archive/                           # Tutorial-stage code (do not import from src)
```

---

## Common tasks for AI assistants

- **Adding a new tool:** Create Pydantic input/output schemas in `schemas/`, write the `@tool` function in `tools/`, register it in `graph/` if used by a node, add unit tests with a VCR cassette, update `tools/__init__.py`.
- **Adding a node:** Type its signature with `AgentState`, write a unit test, wire into `graph/builder.py`, add an integration test for the new edge.
- **Adding an endpoint:** Add request/response Pydantic models, add the route in `api/`, write 4 tests (200, 401, 422, 404), update the dashboard if it consumes the endpoint.
- **Re-recording cassettes:** `uv run pytest --record-mode=rewrite path/to/test`. Commit the new cassette in the same PR.
- **Running the eval:** `uv run python scripts/run_eval.py`. Updates README "Eval Results" table.
