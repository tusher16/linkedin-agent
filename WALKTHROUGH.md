# WALKTHROUGH.md — What's Actually Built and Tested

A factual log of progress. Updated as work lands. **Use this to figure out
where to pick up if you (or any AI assistant) come back to the project cold.**

---

## Current state — 2026-04-29

### Status
- ✅ Planning, Day 0, Day 1, Day 2, Day 3 (code) complete
- 🔜 Next: start Docker + run Day 3 DB tests, then Day 4 (RAG indexing)

### Repo
- GitHub: https://github.com/tusher16/linkedin-agent
- Latest commit on `main`: Day 3 — PostgreSQL + pgvector
- Knowledge graph: 338 nodes, 524 edges, 37 communities (graphify auto-rebuilds on every commit)

---

## Build log

### Day 0 — Pre-flight
*Status: completed 2026-04-28*

**What shipped:**
- `pyproject.toml` + `uv.lock` (replaces `requirements.txt`); managed by `uv`
- Full package skeleton: `src/linkedin_agent/{schemas,tools,graph,api,db,dashboard,guardrails}/`
- Test layout: `tests/{unit,integration,e2e,security,eval}/` + `conftest.py`
- Tutorial scripts moved to `archive/`; `my_context.md` copied to `docs/personal/`
- `.pre-commit-config.yaml` with ruff + mypy (mypy scoped to `src/`)
- `docker-compose.yml` for dev pgvector
- `.gitignore` excludes `.env`, `writing/`, `docs/superpowers/`, `graphify-out/`, `.claude/`
- GitHub repo created and first push

**Test gate:** ✅ `pytest --collect-only` clean. Pre-commit hooks pass on commit.

**Surprises:**
- Path with spaces (`Linkedin Agent for Auto Post/`) breaks `uv pip install -e .` editable install. Fix: `pythonpath = ["src"]` in pytest config.
- Key rotation skipped — `.env` was never committed (verified with `git log --all -- .env`), so old keys were not exposed.
- `.git` had to be reinitialized once to remove `docs/superpowers/` after we forgot to gitignore it. Lost the graphify hook in the process; reinstalled with `graphify hook install`.

---

### Day 1 — Pydantic schemas + typed tool wrappers
*Status: completed 2026-04-28*

**What shipped:**
- `schemas/post_status.py` — `PostStatus` enum (8 states)
- `schemas/{outline,draft,review,agent_state}.py` — Pydantic models with strict validation
- `schemas/__init__.py` — clean exports
- `tools/{plan_outline,draft_post,review_post,publish_via_postboost}.py` — typed wrappers using `with_structured_output(SchemaClass)`
- `tools/_llm.py` — single Gemini factory (`gemini-2.5-flash`)
- `tests/unit/test_schemas.py` — 30 tests covering validation, ranges, transitions, roundtrip
- `tests/unit/test_tools.py` — 13 tests with `_StubChatModel` (subclasses `Runnable`)

**Test gate:** ✅ 43/43 passing in 1.01s. Coverage: schemas/ 100%, tools/ 97%.

**Surprises:**
- First test attempt used `MagicMock` for `with_structured_output(...)`. Failed because `prompt | mock` calls the *real* `RunnableSerializable.__or__`, not the mock's. Fix: subclass `Runnable` properly so the chain ducktypes via `.invoke()`.
- Pydantic v2 uses `Annotated[int, Field(ge=1, le=10)]`, not v1's `conint`.

**Numbers:**
- 43 tests, 1.01s runtime, 96.77% coverage.

---

### Day 2 — LangGraph StateGraph
*Status: completed 2026-04-28*

**What shipped:**
- `graph/nodes.py` — 8 nodes: guardrails, plan_outline, human_approval, draft_post, review, publish, mark_failed_cost, mark_failed_quality. `should_redraft(state) -> str` for conditional routing.
- `graph/builder.py` — `build_graph()` with `MemorySaver` checkpoint and `interrupt_before=["human_approval"]`
- `tests/unit/test_graph_nodes.py` — 17 tests, one per node + 4 conditions on `should_redraft`
- `tests/integration/test_graph_flow.py` — 5 spec scenarios end-to-end through the compiled graph

**Test gate:** ✅ 22/22 graph tests pass. Total suite: 65 tests, 97.51% coverage.

**Scenarios verified:**
1. Happy path — outline → draft (score 8) → publish
2. Forced re-draft — score 5 then 8 → publish on second pass
3. Iteration cap — always score 4, terminates `FAILED_QUALITY` at iter == max
4. Cost cap — cost forced over $0.05, terminates `FAILED_COST`
5. Human-approval interrupt — `graph.invoke(state.model_dump(), config)` pauses, then `graph.invoke(None, config)` resumes

**Surprises:**
- `max_iterations=3` needed for the forced-redraft test; default 2 hits the iteration cap before the second pass completes.
- Cost is checked at the start of `plan_outline_node` and `draft_post_node` (defensive guard against external state mutation).

---

### Day 3 — PostgreSQL + pgvector
*Status: code completed 2026-04-29; tests pending Docker*

**What shipped:**
- `src/linkedin_agent/db/session.py` — async engine + session factory
- `src/linkedin_agent/db/models.py` — `User`, `Post`, `ContextChunk` with `Vector(1536)` (text-embedding-3-small)
- `src/linkedin_agent/db/repository.py` — `UserRepository`, `PostRepository`, `ContextRepository` with `cosine_distance` similarity search
- `alembic/` at repo root — async-friendly `env.py`, `versions/0001_init.py` enables `vector` extension and creates 3 tables + indexes
- `tests/integration/test_repository.py` — 8 tests (CRUD + top-1 / top-k vector search + delete-by-source)
- `tests/integration/test_migrations.py` — alembic upgrade/downgrade roundtrip

**Test gate:** ⏸️ Code complete; 65 unit/graph tests pass in 5.26s. The 8 DB tests auto-skip until Postgres is reachable.

**To finish:**
```bash
docker compose up -d postgres-pgvector
.venv/bin/alembic upgrade head
.venv/bin/pytest tests/integration/ -v
```

**Surprises:**
- `graphifyy` (added Day 2 for graph hook) pulled 27 tree-sitter language packages. Made `import pytest` take **91+ seconds**. Removed from project deps; reinstalled globally via `uv tool install graphifyy`. Graph hook still works.
- mypy strict trips on SQLAlchemy `DeclarativeBase` (typed as `Any`). Workaround: `class Base(DeclarativeBase):  # type: ignore[misc]`. Repository methods explicitly type `result.scalar_one_or_none()` returns to satisfy strict mode.
- Used `pgvector.sqlalchemy.Vector` for the embedding column; the `<=>` operator becomes `column.cosine_distance(query)` in SQLAlchemy.
- Alembic config lives at repo root (`alembic.ini` + `alembic/`) — convention over the spec's "in `db/`" suggestion. Easier to invoke (`.venv/bin/alembic upgrade head` from repo root).

---

### Day 4 — RAG indexing + retrieval
*Status: not started*

### Day 5 — Eval pipeline
*Status: not started*

### Day 6 — FastAPI backend
*Status: not started*

### Day 7 — Streamlit dashboard
*Status: not started*

### Day 8 — Guardrails + adversarial suite
*Status: not started*

### Day 9 — Real PostBoost publish
*Status: not started*

### Day 10 — Containerize + deploy
*Status: not started*

### Day 11 — GitHub Actions CI/CD
*Status: not started*

### Day 12-13 — Polish
*Status: not started*

### Day 14 — Recursive demo + launch
*Status: not started*

---

## Format for filling in each day (do this as work lands)

```markdown
### Day N — Title
*Status: completed YYYY-MM-DD*

**What shipped:**
- One-line bullet per concrete artifact (file, endpoint, test, etc.)

**Test gate:** ✅ <one line on how the gate was confirmed>

**What was tested manually:**
- One-line bullets for any non-automated checks

**Surprises / decisions made along the way:**
- Anything that diverged from the plan — what changed and why.

**Numbers (if applicable):**
- e.g., baseline eval avg, p50 latency, coverage %.
```
