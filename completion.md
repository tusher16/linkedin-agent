# Completion Log

Tracks what was built, why, and the gotchas hit each day. Agents picking up
work mid-stream should read this end-to-end before touching code.

**Project:** Autonomous LinkedIn content agent — LangGraph + RAG + pgvector.
**Source of truth:** `docs/superpowers/specs/2026-04-26-linkedin-agent-2week-mvp-design.md`
**Status as of 2026-04-29:** Days 0-2 complete; ready for Day 3 (PostgreSQL + pgvector).

---

## Day 0 — Pre-flight (2026-04-28)

### What was built

| Artefact | Purpose |
|---|---|
| `pyproject.toml` + `uv.lock` | Replaces `requirements.txt`. Managed by `uv`. Includes `dev` extra with pytest, ruff, mypy, pre-commit, vcrpy. |
| `src/linkedin_agent/{schemas,tools,graph,api,db,dashboard,guardrails}/` | Empty package skeleton — every layer has its own module. |
| `tests/{unit,integration,e2e,security,eval}/` + `conftest.py` | Five test categories matching CI quality gates. |
| `archive/01_base_agent.py`, `archive/02_agent_tools.py` | Tutorial code preserved as reference. **Never imported from `src/`.** |
| `docs/personal/my_context.md` | Author's brain dump used for RAG (Day 4). |
| `.pre-commit-config.yaml` | ruff, ruff-format, mypy hooks. mypy is scoped to `src/` only — see gotcha below. |
| `docker-compose.yml` | Single service: `postgres-pgvector` (`ankane/pgvector:latest`). |

### Key decisions

- **`uv` over `pip`/`poetry`.** Faster, lockfile is deterministic, native Python 3.12 support.
- **mypy strict only on `src/`.** Tests use `@pytest.fixture` (untyped decorator) and
  archive code is tutorial-quality — running strict mypy on either makes the hook unusable.
  Configured via `files: ^src/` in `.pre-commit-config.yaml`.
- **Coverage gate at 75%.** Set in `[tool.coverage.report]`. `dashboard/` excluded
  from coverage because Streamlit pages don't unit-test cleanly.
- **`pythonpath = ["src"]` in pytest config.** `uv pip install -e .` had issues
  with the spaces in the project path; this is the reliable way to make imports work.
- **Key rotation skipped.** `.env` was never committed — confirmed by checking
  `git log --all -- .env`. Saved ~30 minutes of manual provider work.

### Gotchas

- **Path with spaces.** The project lives at `/Users/tusher16/Documents/Linkedin Agent for Auto Post/`.
  Always quote paths in bash. Never use `$(cat graphify-out/.graphify_python)` for the venv —
  use `.venv/bin/python3` directly.
- **`graphify` was lost on first `git init` redo.** When the `.git` folder was
  deleted to recreate the repo cleanly, the `post-commit` hook went with it.
  Fix: `uv add graphifyy && .venv/bin/python3 -m graphify hook install`.
- **First commit attempt hit pre-commit failures on archive files.** Ruff and
  mypy ran on tutorial code that wasn't strict-typed. Fixed by adding
  `exclude = ["archive/", ".venv/"]` to both ruff and mypy config sections, and
  scoping the mypy hook to `^src/`.

### Test gate
`pytest --collect-only` runs clean. Pre-commit hooks pass on commit.

---

## Day 1 — Pydantic schemas + typed tool wrappers (2026-04-28)

### What was built

**`src/linkedin_agent/schemas/`** (5 files + `__init__.py`):

| File | Class | Notes |
|---|---|---|
| `post_status.py` | `PostStatus(str, Enum)` | 8 states: `queued`, `outline_pending`, `ready_to_publish`, `published`, `failed_quality`, `failed_cost`, `failed_publish`, `cancelled`. String-typed enum so it serialises cleanly to JSON. |
| `outline.py` | `OutlineOutput` | `hook` (10-300 chars), `bullets` (3-7), `closing_question` (10-300 chars). |
| `draft.py` | `DraftOutput` | `text` (50-3000 chars), `hashtags` (≤3), `estimated_tokens` (≥0). |
| `review.py` | `ReviewOutput` | All scores `Annotated[int, Field(ge=1, le=10)]`. Holistic `score` + 3 sub-scores + `cliche_detected: bool` + `feedback`. |
| `agent_state.py` | `AgentState` | The single state object carried through the graph. Owns the iteration cap (`max_iterations=2`) and cost cap (`max_cost_usd=0.05`) with helper methods `cost_exceeded()` and `iterations_exceeded()`. |

**`src/linkedin_agent/tools/`** (4 tools + `_llm.py` + `__init__.py`):

| File | Function | Returns |
|---|---|---|
| `_llm.py` | `get_drafter_llm(temperature, max_output_tokens)` | `ChatGoogleGenerativeAI` configured for `gemini-2.5-flash`. Single factory so the model can be swapped in one place. |
| `plan_outline.py` | `plan_outline(topic, context, llm=None)` | `OutlineOutput` |
| `draft_post.py` | `draft_post(topic, outline, context, tone, llm=None)` | `DraftOutput` |
| `review_post.py` | `review_post(draft, llm=None)` | `ReviewOutput` |
| `publish_via_postboost.py` | `publish_via_postboost(draft) → PublishResult(post_id, mock=True)` | Stub. Real impl Day 9. |

**Tests (`tests/unit/`):**
- `test_schemas.py` — 30 tests across 5 classes
- `test_tools.py` — 13 tests with `_StubChatModel` Runnable

### Key decisions

- **`with_structured_output(SchemaClass)` instead of JSON parsing.** LangChain's
  structured output binds Pydantic schemas directly to the LLM, returning typed
  Pydantic objects. No JSON parsing, no string error handling.
- **All tools accept `llm: BaseChatModel | None = None`.** Production passes
  nothing (gets default Gemini); tests pass `_StubChatModel`. This is dependency
  injection without complexity.
- **`_StubChatModel` instead of `MagicMock` for tests.** The first attempt with
  `MagicMock.__or__` failed because `prompt | mock` triggers `prompt.__or__(mock)`
  which is the *real* LangChain `RunnableSerializable.__or__`. The fix was to
  subclass `Runnable` properly:
  ```python
  class _StubStructuredRunnable(Runnable):
      def __init__(self, return_value):
          self.return_value = return_value
          self.last_input = None
      def invoke(self, input, config=None, **kwargs):
          self.last_input = input
          return self.return_value
  ```
  This works because `RunnableSequence` ducktypes via `.invoke(input, config)`.
- **Tools verify the return type** with `isinstance` and raise `TypeError`. This
  catches the case where structured output silently degrades (e.g. provider
  returns a dict instead of the schema).

### Gotchas

- **Pydantic v2 uses `Annotated[int, Field(...)]`, not `conint`.** `conint` is
  v1-only. Used `Score = Annotated[int, Field(ge=1, le=10)]` in `review.py`.
- **Editable install (`uv pip install -e .`) didn't make `linkedin_agent` importable.**
  Two `.pth` files appeared in site-packages but Python didn't pick them up. Likely
  related to spaces in the path. Real fix: `pythonpath = ["src"]` in pytest config.
- **Stale `.coverage` file blocks pytest re-runs** with
  `sqlite3.OperationalError: table coverage_schema already exists`.
  Delete it: `rm -f .coverage` before each run.
- **Tests run in 1.01s.** If a test run takes minutes, an LLM call leaked through —
  check that you're passing the `llm=stub` kwarg to every tool call.

### Test gate
✅ 43/43 passing. Coverage: schemas/ 100%, tools/ 97% (only `_llm.py` factory uncovered).

---

## Day 2 — LangGraph StateGraph (2026-04-28)

### Architecture

```
START → guardrails → plan_outline → ⏸ INTERRUPT(human_approval)
                                          ↓ resume
                                     draft_post ←──────┐
                                          ↓            │ score<7 AND iter<max
                                       review          │
                                          ↓            │
                                  ┌──conditional──┐────┘
                                  ↓     ↓        ↓
                             publish  fail_cost fail_quality
                                  ↓     ↓        ↓
                                  END  END      END
```

### What was built

**`src/linkedin_agent/graph/nodes.py`** — 8 node functions:

| Node | Returns (state-update dict) |
|---|---|
| `guardrails_node` | `{"status": OUTLINE_PENDING}` (Day 8 wires real injection check here) |
| `plan_outline_node` | `{"outline": OutlineOutput, "cost_usd": +0.0002}` |
| `human_approval_node` | `{}` — marker; the actual pause is the graph-level interrupt |
| `draft_post_node` | `{"draft", "iteration": +1, "cost_usd": +0.0008}` |
| `review_node` | `{"review": ReviewOutput, "cost_usd": +0.0003}` |
| `publish_node` | `{"status": PUBLISHED, "post_id": "mock_..."}` |
| `mark_failed_cost` | `{"status": FAILED_COST, "error_message": "..."}` |
| `mark_failed_quality` | `{"status": FAILED_QUALITY, "error_message": "..."}` |

Plus `should_redraft(state) -> str` returning one of `"redraft" | "publish" | "fail_cost" | "fail_quality"`. Order of checks matters: cost cap first, then score, then iteration cap.

**`src/linkedin_agent/graph/builder.py`** — `build_graph(checkpointer=None)`:
- Wires all 8 nodes
- Conditional edge after `review` mapping the 4 strings to nodes
- `interrupt_before=["human_approval"]` so the graph pauses after `plan_outline`
- Defaults to `MemorySaver()` checkpoint store

**Tests:**
- `tests/unit/test_graph_nodes.py` — 17 tests, one per node + 4 conditions on `should_redraft`. Uses `monkeypatch.setattr(nodes, "tool_name", stub)` to swap tools.
- `tests/integration/test_graph_flow.py` — 5 spec scenarios end-to-end through the compiled graph.

### Key decisions

- **Cost is checked at the start of `plan_outline_node` and `draft_post_node`.**
  This guards against drift if external code mutates `state.cost_usd` between nodes.
  The conditional edge after `review` also checks (`should_redraft → "fail_cost"`).
- **Status is updated by terminal nodes, not the conditional edge.**
  `mark_failed_cost` and `mark_failed_quality` exist as nodes (instead of routing
  straight to END from the conditional) so the final state carries the correct
  `status` and `error_message`. END only sees what the last node wrote.
- **Tools are imported into `graph/nodes.py` at module level.** This is what
  enables `monkeypatch.setattr(nodes, "plan_outline", stub)` to work in tests.
  Don't import them lazily inside the node body or the patch won't apply.
- **Cost estimates are constants in `nodes.py`** (`COST_PER_OUTLINE = 0.0002`, etc.).
  Day 5 will replace these with real values from LangSmith trace metadata. Don't
  build complex per-token math here.
- **`AgentState.model_dump()` is the entrypoint.** LangGraph wants a dict, not
  the Pydantic instance. The state IS still validated as `AgentState` internally
  because `StateGraph(AgentState)` was passed.

### Gotchas

- **`graph.invoke(state.model_dump(), config)` returns at the interrupt.** First
  invoke runs guardrails + plan_outline, then pauses. Resume with
  `graph.invoke(None, config)` — passing `None` is what tells LangGraph "continue
  from checkpoint, don't override state."
- **Same `thread_id` must be reused on resume.** `config = {"configurable": {"thread_id": "..."}}`
  is how the checkpointer matches the resume to the paused run.
- **Conditional edge return strings must exactly match the mapping keys.**
  Typos here cause silent routing bugs — the graph just goes nowhere.
- **`max_iterations=3` was needed for the forced-redraft test.** With default
  `max_iterations=2` the iteration cap kicks in before the second pass. Tests
  that exercise multi-iteration paths must set `max_iterations` explicitly.

### Test gate
✅ 22/22 graph tests pass (17 unit + 5 integration). All 5 spec scenarios green.
Total suite: 65 tests passing in 1.23s. Coverage: 97.51%.

---

## What the next agent should know

### Active conventions

1. **Every PR adds tests.** Coverage gate is 75% globally; effective floor is
   higher because schemas/ and tools/ are at 97-100%.
2. **No real LLM calls in CI.** All tool tests use `_StubChatModel`; all graph
   tests use `monkeypatch` to swap tool functions. Total suite runs in ~1.2s.
3. **Pre-commit must stay green.** ruff auto-fixes; ruff-format auto-fixes; mypy
   on `src/` only. If a hook fails, fix the underlying issue — never `--no-verify`.
4. **Graphify auto-runs on every commit.** `.git/hooks/post-commit` rebuilds
   `graphify-out/graph.json` (gitignored). Adds ~2-5s per commit.
5. **`docs/superpowers/` is private** — gitignored. Specs and plans stay local.
6. **`writing/` is private** — Medium drafts. Never push.

### File locations to remember

- Authoritative spec: `docs/superpowers/specs/2026-04-26-linkedin-agent-2week-mvp-design.md`
- Current task list: `TASK.md` (mirrors `IMPLEMENTATION_PLAN.md`)
- Coding rules: `docs/rules/coding.md`
- Security rules: `docs/rules/security.md`
- Personal context for RAG: `docs/personal/my_context.md`
- Past writing for `/humanizer`: `writing/context/*.md`

### Commands that work

| Need | Command |
|---|---|
| Run full test suite | `.venv/bin/pytest --no-header` |
| Run with coverage | `rm -f .coverage && .venv/bin/pytest --cov=src --cov-report=term-missing` |
| Run one test file | `.venv/bin/pytest tests/unit/test_schemas.py --no-cov -v` |
| Add a runtime dependency | `uv add <package>` |
| Add a dev-only dependency | `uv add --dev <package>` |
| Update graphify graph + RAG together | `./scripts/refresh.sh` |
| Verify graph compiles | `PYTHONPATH=src .venv/bin/python3 -c "from linkedin_agent.graph import build_graph; build_graph()"` |

### Things to avoid

- Importing tool functions inside node bodies (breaks monkeypatching).
- Adding `print()` to `src/` — use `structlog` (or skip logging entirely for now).
- Routing directly to `END` from a conditional edge when the final state needs
  a status update — go through a terminal node instead.
- `from langchain_core.runnables import Runnable` and trying to use `MagicMock`
  for the `with_structured_output` chain. Subclass `Runnable` properly.
- Re-running pytest without deleting `.coverage` — sqlite3 schema collision.

### Day 3 setup needed

PostgreSQL + pgvector. Will require:
- `docker compose up -d postgres-pgvector` (`ankane/pgvector:latest` already in `docker-compose.yml`)
- New deps: `sqlalchemy[asyncio]`, `alembic`, `asyncpg`, `pgvector` (already in `pyproject.toml`)
- Environment: `DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/linkedin_agent`

The `db/` package is empty. Day 3 fills it with `models.py`, `repository.py`,
and Alembic migrations. Test gate: `alembic upgrade head → downgrade base → upgrade head`
runs clean; CRUD tests pass against pytest-docker.
