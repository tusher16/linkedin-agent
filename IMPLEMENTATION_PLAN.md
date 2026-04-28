# Implementation Plan — 14-Day MVP

**Source of truth for the build sequence.** All days, all deliverables, all
test gates. Mirrors the [design spec](docs/superpowers/specs/2026-04-26-linkedin-agent-2week-mvp-design.md);
in any conflict, the spec wins.

**Target ship:** 2026-05-10 (Day 14 from start).

**Status legend:** ✅ done · 🔄 in_progress · ⏳ pending · ⏸ blocked

---

## Day 0 — Pre-flight ⏳

Setup work before any feature code is written.

| Task | Why |
|---|---|
| Rotate Google, OpenRouter, LangSmith, PostBoost API keys | Old keys were committed in `.env.template` — already exposed |
| Confirm old keys are dead (try a request → expect 401) | Verification, not assumption |
| Rewrite `.env.template` to placeholder values only | Prevent future leaks |
| `git init` + first commit + push to public GitHub repo | Version control + recruiter-visible history |
| Replace `requirements.txt` with `pyproject.toml` (uv-managed) + `uv.lock` | Modern Python tooling |
| Create package layout: `src/linkedin_agent/{schemas,tools,graph,api,db,dashboard}/` + `tests/{unit,integration,e2e,security,eval}/` + `scripts/` + `docs/{adr,specs}/` | Clean structure for the rewrite |
| Move `01_base_agent.py` and `02_agent_tools.py` to `archive/` | Preserve history without polluting `src/` |
| Install `pre-commit` running `ruff check` + `ruff format` + `mypy src/` | Catch issues before commit |
| 15-min PostBoost spike: hit a trivial endpoint with the rotated key | De-risk Day 9 |

**Test gate:** `pytest --collect-only` runs without error. `git status` clean. Pre-commit hook installed and runs on `git commit`.

---

## Day 1 — Pydantic schemas + tool refactor ⏳

| Task | Output |
|---|---|
| Define `PostStatus` enum (`queued`, `outline_pending`, `ready_to_publish`, `published`, `failed_quality`, `failed_cost`, `failed_publish`, `cancelled`) | `schemas/post_status.py` |
| Define `OutlineOutput`, `DraftOutput`, `ReviewOutput` (with `score: conint(ge=1, le=10)`), `AgentState` (TypedDict + Pydantic) | `schemas/__init__.py` |
| Refactor `archive/02_agent_tools.py` content into typed `tools/plan_outline.py`, `tools/draft_post.py`, `tools/review_post.py`, `tools/publish_via_postboost.py` (stubbed for now — real impl Day 9) | `src/linkedin_agent/tools/` |
| Add `tests/unit/test_schemas.py`: roundtrip serialization, score range, status transitions | ~6 unit tests |
| Add `tests/unit/test_tools.py`: each tool with VCR cassette | ~5 unit tests |

**Test gate:**
- ≥ 85% line coverage on `src/linkedin_agent/schemas/` and `src/linkedin_agent/tools/`
- All schema validators reject out-of-range scores
- VCR cassettes committed for each tool test

---

## Day 2 — LangGraph StateGraph ⏳

| Task | Output |
|---|---|
| Build node functions: `guardrails_node`, `plan_outline_node`, `human_approval_node` (interrupt), `draft_post_node`, `review_node`, `publish_node` | `graph/nodes.py` |
| Conditional edge after `review_node`: `if score < 7 AND iter < 2 → draft_post_node else publish_node` | `graph/builder.py` |
| Cost-cap check + iteration-cap check inside state on every iteration | In `AgentState` validators |
| Wire into a buildable `StateGraph` with a tested checkpoint store (in-memory MVP) | `graph/builder.py` |
| `tests/unit/test_graph_nodes.py`: each node in isolation with mocked tools | One test per node |
| `tests/integration/test_graph_flow.py`: 5 scenarios — happy path, forced re-draft, iteration-cap termination, cost-cap termination, human-approval interrupt | 5 integration tests |

**Test gate:** All 5 graph integration tests pass. Iteration cap forces graph to terminate with `failed_quality` status when score perpetually < 7.

---

## Day 3 — PostgreSQL + pgvector ⏳

| Task | Output |
|---|---|
| `docker-compose.yml` with `ankane/pgvector:latest` for local dev | Service `postgres-pgvector` |
| SQLAlchemy 2.x async models: `User`, `Post`, `ContextChunk` (with `Vector(1536)` column) | `db/models.py` |
| Alembic init + first migration (creates `vector` extension, all 3 tables) | `db/alembic/versions/0001_init.py` |
| Repository module: `PostRepository`, `ContextRepository`, `UserRepository` (CRUD + vector cosine search) | `db/repository.py` |
| `tests/integration/test_repository.py` against pytest-docker pgvector instance | CRUD + vector tests |

**Test gate:**
- `alembic upgrade head` → `downgrade base` → `upgrade head` runs clean
- Repository CRUD tests pass
- Vector cosine search returns correct row for a known query

---

## Day 4 — RAG indexing + retrieval ⏳

| Task | Output |
|---|---|
| `scripts/index_context.py`: chunk `archive/my_context.md` (and any other `.md` files in `docs/personal/`), embed with `text-embedding-3-small`, upsert into `context_chunks` | Re-runnable indexer |
| New `retrieve_context` tool: top-k cosine search, returns typed `ContextChunk` list | `tools/retrieve_context.py` |
| Wire `retrieve_context` into `plan_outline_node` and `draft_post_node` (replaces static `load_my_context()` from archive) | Updated `graph/nodes.py` |
| `tests/unit/test_chunker.py`: deterministic chunking with overlap | Unit tests |
| `tests/integration/test_rag.py`: index 5 known chunks, query, assert top-1 match. Quality test: 3 hand-picked (query, expected_chunk_id) tuples → recall@3 = 100% | Integration tests |

**Test gate:** Recall@3 = 100% on the 3 quality-test tuples. Static `load_my_context()` removed entirely from `tools/` and `graph/`.

---

## Day 5 — Eval pipeline (résumé centerpiece) ⏳

| Task | Output |
|---|---|
| Hand-curate 15 topics with reference criteria | `scripts/eval/topics.json` |
| Push to LangSmith as a versioned dataset | LangSmith dataset URL committed in README |
| Cross-model judge implementation: GPT-4o-mini (via OpenRouter) scores Gemini outputs on 4 criteria — tone match, technical density, hook strength, AI-cliché detection | `scripts/eval/judge.py` |
| `scripts/run_eval.py`: orchestrator that runs all 15 topics through the agent and writes `docs/eval/baseline-{date}.json` | Manual eval runner |
| `tests/eval/test_eval_smoke.py`: runs a 3-topic subset on every CI run via VCR cassettes | Catches code/shape regressions |
| Inspect failures, iterate prompts, re-run until baseline is acceptable | Iterative loop |
| Capture baseline numbers and write into README "Eval methodology" section | README update |

**Test gate:** Eval baseline committed. Smoke test runs in CI in < 30s and uses no real LLM credits. (Quality regressions caught only by manual `run_eval.py` before each release — explicitly noted in README.)

**Note:** Day 5 is the highest-value day for résumé impact. Budget all 8 hours. If baseline avg < 7, add a transparency section to README acknowledging the weakness — own it explicitly rather than hide.

---

## Day 6 — FastAPI backend ⏳

| Endpoint | Purpose |
|---|---|
| `POST /posts` | Submit topic → start a graph run → return post_id + status |
| `POST /posts/{id}/approve-outline` | Resume the graph from the human-approval interrupt |
| `POST /posts/{id}/publish` | Trigger publish_via_postboost on a `ready_to_publish` post |
| `DELETE /posts/{id}` | Cancel a run / reject an outline |
| `GET /posts` | List with pagination + status filter |
| `GET /posts/{id}` | Detail view with full state |
| `GET /health` | Liveness probe (used by Uptime Kuma + post-deploy smoke) |

| Task | Output |
|---|---|
| FastAPI app + Pydantic request/response models | `api/main.py`, `api/routes/posts.py` |
| JWT auth middleware: `passlib[bcrypt]` + `python-jose[cryptography]`. Single hardcoded admin from env | `api/auth.py` |
| Dependency injection for async DB session | `api/deps.py` |
| `tests/integration/test_api.py`: each endpoint with 200 / 401 / 422 / 404 cases | ≥ 28 endpoint tests |

**Test gate:** Every endpoint has all 4 cases covered. JWT middleware: valid passes, expired/missing rejected. `/health` returns 200.

---

## Day 7 — Streamlit dashboard ⏳

| Task | Output |
|---|---|
| Login page (calls FastAPI `/auth/login`, stores JWT in `st.session_state`) | `dashboard/pages/0_Login.py` |
| New Post form (topic + tone) → `POST /posts` | `dashboard/pages/1_New_Post.py` |
| Pending Approvals list → click → see outline → Approve / Reject buttons | `dashboard/pages/2_Pending_Approvals.py` |
| History table with quality scores + LangSmith trace links | `dashboard/pages/3_History.py` |
| `tests/e2e/test_dashboard.py` using `streamlit.testing.v1.AppTest` (mocks FastAPI at HTTP level) | E2E coverage |

**Test gate:** Login → submit topic → approve outline → history page renders, all without real LLM or DB. Dashboard only talks to FastAPI (verify by grep — no `langchain_*` imports in `dashboard/`).

---

## Day 8 — Guardrails + adversarial suite ⏳

| Task | Output |
|---|---|
| `prompt_injection_guardrail` function: regex + heuristics + Lakera-sample patterns | `src/linkedin_agent/guardrails/injection.py` |
| Wire into `guardrails_node` (already exists from Day 2 as a stub) | Updated `graph/nodes.py` |
| `tests/security/adversarial_inputs.json`: 10 attacks (5 hand-written + 5 from Lakera open dataset) | Test fixture |
| `tests/security/test_guardrails.py`: each attack → assert blocked. False-positive test: 10 legit topics → none blocked | Security tests |
| Document patterns covered + roadmap for additional defences in `docs/security.md` | Defensive doc |

**Test gate:** 10/10 adversarial attacks blocked. 0/10 legit topics blocked (no false positives). CI fails on any test failure.

---

## Day 9 — Real PostBoost publish ⏳

| Task | Output |
|---|---|
| Read PostBoost docs end to end (auth, posts, errors, rate limits) | Notes in `docs/postboost-integration.md` |
| One-time LinkedIn account connection in PostBoost's own dashboard (their built-in OAuth — our app never sees LinkedIn creds) | Manual setup, document the steps |
| Implement real `publish_via_postboost` tool: POST request, retry on 5xx, return PostBoost post_id, idempotency check (don't re-publish a `published` post) | `tools/publish_via_postboost.py` |
| `tests/integration/test_postboost_client.py`: mocked HTTPX. Idempotency: same `post_id` published twice → second is no-op | Mocked tests |
| `scripts/smoke_publish.py`: manual one-off real publish to a sandbox/dev LinkedIn account | Manual smoke test |

**Test gate:** Mocked tests pass. Smoke script publishes one real post successfully (manual confirmation).

---

## Day 10 — Containerize + deploy live ⏳

| Task | Output |
|---|---|
| Multi-stage `Dockerfile` (build deps in stage 1, runtime slim in stage 2) | `Dockerfile` |
| `docker-compose.yml` services: `api`, `dashboard`, `postgres-pgvector`, `cloudflared`, `caddy`, `uptime-kuma` | Production compose file |
| Caddy config: route `linkedin-agent.tusher16.com` → `dashboard:8501`, `api.linkedin-agent.tusher16.com` → `api:8000` (or single host with path-based routing) | `caddy/Caddyfile` |
| Cloudflare Tunnel: create tunnel, run `cloudflared tunnel route dns` to auto-provision DNS, run `cloudflared` as a service in compose | Tunnel running |
| Uptime Kuma: configure HTTP check on the live URL + Telegram alert | Uptime Kuma running |
| Nightly `pg_dump` cron → encrypted upload to Backblaze B2 (`rclone` or `restic`) | Scheduled backup job |
| Deploy to Ubuntu home server via Portainer stack import | Live |
| Post-deploy smoke: `curl https://linkedin-agent.tusher16.com/health` from phone hotspot returns 200 | External reachability confirmed |

**Test gate:** Live URL reachable from outside the home network. Login page loads. Streamlit assets load over Cloudflare. Uptime Kuma green. One nightly backup successfully run and verified restorable.

---

## Day 11 — GitHub Actions CI ⏳

| Task | Output |
|---|---|
| `.github/workflows/ci.yml`: `ruff check` → `ruff format --check` → `mypy src/` → `pytest --cov=src --cov-fail-under=75` → docker build → push to GHCR | CI pipeline |
| `.github/workflows/deploy.yml`: on tag push to `v*`, SSH into home server (via `appleboy/ssh-action` with restricted deploy key), `docker compose pull && docker compose up -d` | Deploy pipeline |
| Coverage badge + CI badge added to README | Public visibility |

**Test gate:** Push to `main` → all CI checks green. Tag `v0.1.0` → deploy workflow runs and home server pulls the new image.

---

## Day 12-13 — README, ADRs, demo video ⏳

| Task | Output |
|---|---|
| Polish architecture diagram (Excalidraw export) | `docs/architecture.png` |
| Fill in README "Eval Results" section with real numbers from Day 5 | Updated README |
| Write 3 ADRs (~200 words each): pgvector vs Qdrant, cross-model judge, outline-first | `docs/adr/001-003-*.md` |
| Record 60-second Loom demo (shot list in spec §6.4) | Loom URL in README |
| Capture one public LangSmith trace, link in README | Public trace URL |
| Audit every URL in the README — every link clicks to a working target | Link audit |
| Write `docs/v2-roadmap.md` covering all parked features with rationale | Parked items doc |
| Draft CV bullets (calibrated with eval numbers) | CV-ready text |

**Test gate:** All 7 "definition of done" boxes from spec §1.2 are checkable.

---

## Day 14 — Buffer + recursive demo ⏳

| Task | Output |
|---|---|
| Use the agent to write the LinkedIn announcement post | First real published post |
| Tweet/post the live URL + repo link | Public launch |
| Update LinkedIn profile + CV | Distribution |
| If anything from Day 0-13 is unfinished, finish it here | Buffer |

**Test gate:** Announcement post is live on LinkedIn AND links to the repo + live demo. CV bullets calibrated. Project officially shipped.

---

## Kill-switch order (if Day 12 arrives behind)

Drop in this order — each saves about half a day:

1. ADR markdown files → fold into a "Design Notes" section in README.
2. Full GitHub Actions pipeline → just `ruff` + `pytest` in CI; manual `docker build` + `scp`.
3. Adversarial suite from 10 → 3 representative attacks with a roadmap note.

**Never cut:** the Day 5 eval pipeline. It is the entire AI Engineering story.
