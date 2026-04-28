# TASK.md — Master Checklist

Mirrors [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) — same content, checkbox format.
Update this as you go. **Definition of "done":** the test gate for that day passes.

**Status:** Day 0 complete (2026-04-28). Ready to start Day 1.

---

## Pre-existing (from old tutorial, archived)
- [x] Old Phase 1: Basic Gemini chain (`archive/01_base_agent.py`)
- [x] Old Phase 2: LangChain LCEL (`archive/01_base_agent.py`)
- [x] Old Phase 3: LangSmith tracing
- [x] Old Phase 4: `@tool` definitions + outline-first pipeline (`archive/02_agent_tools.py`)

---

## Day 0 — Pre-flight ✅
- [x] Rotate Google API key _(skipped — `.env` was never committed; keys not exposed)_
- [x] Rotate OpenRouter API key _(skipped — `.env` was never committed; keys not exposed)_
- [x] Rotate LangSmith API key _(skipped — `.env` was never committed; keys not exposed)_
- [x] Rotate PostBoost API key _(skipped — `.env` was never committed; keys not exposed)_
- [x] Verify each old key returns 401 on a test call _(skipped — no exposure risk)_
- [x] Rewrite `.env.template` with placeholder values only
- [x] `git init` + first commit
- [x] Create public GitHub repo `tusher16/linkedin-agent` and push
- [x] Replace `requirements.txt` with `pyproject.toml` + `uv.lock`
- [x] Create directory structure: `src/linkedin_agent/{schemas,tools,graph,api,db,dashboard,guardrails}/`
- [x] Create `tests/{unit,integration,e2e,security,eval}/` + `tests/conftest.py`
- [x] Create `docs/{adr,personal,eval}/`, `archive/`
- [x] Move `01_base_agent.py` and `02_agent_tools.py` to `archive/`
- [x] Copy `my_context.md` to `docs/personal/`
- [x] Install `pre-commit` with ruff + mypy hooks (mypy scoped to `src/`)
- [x] Add `docker-compose.yml` for dev pgvector DB
- [ ] PostBoost spike: validate key with one trivial API call _(pending — do before Day 9)_

**Test gate:** ✅ `pytest --collect-only` runs clean. Pre-commit hooks pass on commit.

---

## Day 1 — Pydantic schemas + tool refactor
- [ ] `schemas/post_status.py` — `PostStatus` enum (8 states)
- [ ] `schemas/__init__.py` — `OutlineOutput`, `DraftOutput`, `ReviewOutput` (with `score: conint(ge=1, le=10)`), `AgentState`
- [ ] `tools/plan_outline.py` — typed I/O wrapper around the plan tool
- [ ] `tools/draft_post.py` — typed wrapper for draft
- [ ] `tools/review_post.py` — typed wrapper for review
- [ ] `tools/publish_via_postboost.py` — STUB returning `MOCK` (real impl Day 9)
- [ ] `tests/unit/test_schemas.py` — roundtrip, score range, status transitions
- [ ] `tests/unit/test_tools.py` — each tool with VCR cassette
- [ ] Coverage on `schemas/` ≥ 85%, on `tools/` ≥ 85%

**Test gate:** Schema + tool tests green; coverage gate met.

---

## Day 2 — LangGraph StateGraph
- [ ] `graph/nodes.py` — `guardrails_node`, `plan_outline_node`, `human_approval_node` (interrupt), `draft_post_node`, `review_node`, `publish_node`
- [ ] Iteration cap (≤ 2 retries) inside `AgentState`
- [ ] Cost cap ($0.05/run default) inside `AgentState`
- [ ] `graph/builder.py` — `build_graph()`, conditional edge after review
- [ ] In-memory checkpoint store wired
- [ ] `tests/unit/test_graph_nodes.py` — one test per node
- [ ] `tests/integration/test_graph_flow.py` — happy path
- [ ] `tests/integration/test_graph_flow.py` — forced re-draft (score < 7 once, then ≥ 7)
- [ ] `tests/integration/test_graph_flow.py` — iteration cap (always < 7 → terminate `failed_quality`)
- [ ] `tests/integration/test_graph_flow.py` — cost cap (force tokens > cap → terminate `failed_cost`)
- [ ] `tests/integration/test_graph_flow.py` — human-approval interrupt pause/resume

**Test gate:** All 5 graph integration tests pass.

---

## Day 3 — PostgreSQL + pgvector
- [ ] `docker-compose.yml` (dev) — `postgres-pgvector` service with `ankane/pgvector:latest`
- [ ] `db/models.py` — `User`, `Post`, `ContextChunk` (with `Vector(1536)`)
- [ ] `db/alembic/` initialised
- [ ] First migration: enables `vector` extension, creates 3 tables
- [ ] `db/repository.py` — `UserRepository`, `PostRepository`, `ContextRepository` (CRUD + vector cosine search)
- [ ] `tests/integration/test_repository.py` — pytest-docker fixture spins up real DB
- [ ] CRUD tests: insert / fetch / update status / list / delete
- [ ] Vector search test: known query → expected chunk in top-1
- [ ] Migration roundtrip test: `upgrade head` → `downgrade base` → `upgrade head`

**Test gate:** Repository CRUD + vector search tests green. Migration roundtrip clean.

---

## Day 4 — RAG indexing + retrieval
- [ ] `scripts/index_context.py` — chunks `docs/personal/*.md`, embeds, upserts
- [ ] `tools/retrieve_context.py` — top-k cosine search returning typed list
- [ ] Wire `retrieve_context` into `plan_outline_node` and `draft_post_node`
- [ ] Remove static `load_my_context()` from all of `src/`
- [ ] `tests/unit/test_chunker.py` — chunking with overlap is deterministic
- [ ] `tests/integration/test_rag.py` — index 5 known chunks, query, top-1 match
- [ ] Quality test: 3 hand-picked tuples, recall@3 = 100%

**Test gate:** Recall@3 = 100%. No static context loading remains in `src/`.

---

## Day 5 — Eval pipeline ⭐ résumé centerpiece
- [ ] `scripts/eval/topics.json` — 15 hand-curated topics + reference criteria
- [ ] Push dataset to LangSmith (versioned)
- [ ] `scripts/eval/judge.py` — GPT-4o-mini judge (via OpenRouter), 4 criteria
- [ ] `scripts/run_eval.py` — orchestrator, writes `docs/eval/baseline-{date}.json`
- [ ] `tests/eval/test_eval_smoke.py` — 3-topic subset with VCR
- [ ] First baseline run captured
- [ ] Iterate prompts if baseline < 7 average; re-run
- [ ] Update README "Eval methodology" section with real numbers
- [ ] Capture one public LangSmith trace URL for README

**Test gate:** Eval baseline committed. CI smoke runs in < 30s using cassettes.

---

## Day 6 — FastAPI backend
- [ ] `api/main.py` — FastAPI app, CORS, health endpoint
- [ ] `api/auth.py` — JWT middleware, bcrypt password verify, single admin from env
- [ ] `api/routes/posts.py` — 6 endpoints (POST /posts, POST /posts/{id}/approve-outline, POST /posts/{id}/publish, DELETE /posts/{id}, GET /posts, GET /posts/{id})
- [ ] `api/deps.py` — async DB session DI
- [ ] Pydantic request/response models for each endpoint
- [ ] `tests/integration/test_api.py` — 4 cases (200, 401, 422, 404) per endpoint
- [ ] JWT middleware tests: valid / expired / missing
- [ ] `/health` returns 200

**Test gate:** Every endpoint has all 4 cases. JWT middleware tests green.

---

## Day 7 — Streamlit dashboard
- [ ] `dashboard/app.py` — entrypoint with login gate
- [ ] `dashboard/pages/0_Login.py`
- [ ] `dashboard/pages/1_New_Post.py`
- [ ] `dashboard/pages/2_Pending_Approvals.py`
- [ ] `dashboard/pages/3_History.py`
- [ ] `dashboard/api_client.py` — wraps FastAPI calls (single point of HTTP)
- [ ] `tests/e2e/test_dashboard.py` — login → submit → approve → history flow
- [ ] grep verifies no `langchain_*` imports in `dashboard/`

**Test gate:** E2E flow passes. Dashboard talks ONLY to FastAPI.

---

## Day 8 — Guardrails + adversarial suite
- [ ] `guardrails/injection.py` — `prompt_injection_guardrail(text) -> bool`
- [ ] Wire into `guardrails_node`
- [ ] `tests/security/adversarial_inputs.json` — 10 attacks (5 hand-written + 5 from Lakera)
- [ ] `tests/security/test_guardrails.py` — each attack blocked
- [ ] False-positive test: 10 legit topics not blocked
- [ ] `docs/security.md` — covered patterns + roadmap

**Test gate:** 10/10 attacks blocked, 0/10 legit blocked.

---

## Day 9 — Real PostBoost publish
- [ ] Read PostBoost docs end-to-end; `docs/postboost-integration.md` written
- [ ] LinkedIn account connected via PostBoost's OAuth flow (one-time, manual)
- [ ] `tools/publish_via_postboost.py` — real implementation with retry + idempotency
- [ ] `tests/integration/test_postboost_client.py` — mocked HTTPX, idempotency check
- [ ] `scripts/smoke_publish.py` — manual real publish smoke
- [ ] Smoke test executed once, real post visible on LinkedIn

**Test gate:** Mocked tests pass. Smoke script publishes one real post successfully.

---

## Day 10 — Containerize + deploy
- [ ] Multi-stage `Dockerfile`
- [ ] `docker-compose.yml` (prod) — `api`, `dashboard`, `postgres-pgvector`, `cloudflared`, `caddy`, `uptime-kuma`
- [ ] Caddy config for hostname routing
- [ ] Cloudflare Tunnel: tunnel created, DNS provisioned via `cloudflared tunnel route dns`
- [ ] Uptime Kuma configured with HTTP check on live URL + Telegram alert channel
- [ ] Nightly `pg_dump` → encrypted upload to Backblaze B2 (cron + `rclone` or `restic`)
- [ ] Stack imported into Portainer on home server
- [ ] Post-deploy smoke: `curl https://linkedin-agent.tusher16.com/health` from phone hotspot returns 200
- [ ] Login page loads from external network
- [ ] Verify one backup is restorable

**Test gate:** Live URL externally reachable. One verified-restorable backup.

---

## Day 11 — GitHub Actions CI/CD
- [ ] `.github/workflows/ci.yml` — ruff + ruff format check + mypy + pytest --cov-fail-under=75 + docker build + GHCR push
- [ ] `.github/workflows/deploy.yml` — on `v*` tag, SSH-deploy to home server
- [ ] SSH deploy key created with restricted command
- [ ] CI badge in README
- [ ] Coverage badge in README
- [ ] Push to `main` → all green
- [ ] Tag `v0.1.0` → deploy workflow runs successfully

**Test gate:** Both workflows green. Tag triggers a real deploy.

---

## Day 12-13 — Polish
- [ ] Architecture diagram polished (Excalidraw export)
- [ ] README "Eval methodology" filled with Day 5 numbers
- [ ] `docs/adr/001-pgvector-over-qdrant.md`
- [ ] `docs/adr/002-cross-model-judge.md`
- [ ] `docs/adr/003-outline-first-generation.md`
- [ ] 60-second Loom demo recorded and linked in README
- [ ] Public LangSmith trace URL linked in README
- [ ] Every URL in README clicks to a working target (link audit)
- [ ] `docs/v2-roadmap.md` written
- [ ] CV bullets drafted (calibrated to eval numbers)

**Test gate:** All 7 "definition of done" boxes from spec §1.2 checkable.

---

## Day 14 — Recursive demo + launch
- [ ] Agent generates the LinkedIn announcement post
- [ ] Announcement published to LinkedIn (via the agent itself)
- [ ] Tweet/post links the live URL + repo
- [ ] CV updated with bullets
- [ ] LinkedIn profile updated

**Test gate:** Announcement post live, links repo + live demo, generated by the agent.
