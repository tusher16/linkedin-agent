# LinkedIn AI Agent

**Author:** [Mohammad Obaidullah Tusher](https://linkedin.com/in/tusher16) · AI Engineer · Berlin, Germany

> Autonomous AI agent that drafts, evaluates, and publishes LinkedIn posts grounded
> in personal context. **LangGraph + pgvector RAG + cross-model eval.** Self-hosted
> on a Linux home server via Cloudflare Tunnel.

🚧 **Status:** In active development — target ship **2026-05-10** (14-day MVP).
Live demo, eval results, and demo video link below will populate as the build progresses.

- 🚀 **Live demo:** `https://linkedin-agent.tusher16.com` *(deploys Day 10)*
- 🎥 **60s walkthrough:** *(records Day 13)*
- 📊 **Public LangSmith trace:** *(captured Day 5)*
- 📑 **Design spec:** [`docs/superpowers/specs/2026-04-26-linkedin-agent-2week-mvp-design.md`](docs/superpowers/specs/2026-04-26-linkedin-agent-2week-mvp-design.md)

---

## Why this exists

Most "AI LinkedIn post" tools generate generic motivational filler that sounds
identical across users. They don't know your thesis, your stack, or your
opinions. They also waste tokens — you reject 3 generic drafts before getting
one usable post.

This agent is engineered around four explicit decisions:

| Problem | Decision |
|---|---|
| **Generic voice** — every AI post sounds the same | RAG retrieval over a personal context corpus (pgvector). Every LLM call grounds in author-specific chunks. |
| **Token waste** — full draft costs ~1000 tokens; rejected drafts compound | Outline-first generation: ~200-token outline → human approves → only then is the full draft generated. ~80% cost reduction on rejected ideas. |
| **Self-judge bias** — same model judging itself rewards its own style | Cross-model eval: GPT-4o-mini scores Gemini outputs on a 15-topic dataset. 4 criteria: tone match, technical density, hook strength, AI-cliché detection. |
| **No quality gate** — bad posts ship without a fight | LangGraph re-draft loop: scores < 7 trigger up to 2 automated re-drafts before the post is even shown to me. |

---

## Architecture

```
                     ┌─────────────────────────────────────┐
                     │       Streamlit Dashboard           │
                     │  (auth · new post · approve · view) │
                     └────────────────┬────────────────────┘
                                      │ HTTPS via Cloudflare Tunnel
                                      ▼
                     ┌─────────────────────────────────────┐
                     │         FastAPI backend              │
                     │   /draft  /approve  /publish  /list  │
                     └────────────────┬────────────────────┘
                                      │
                                      ▼
                     ┌─────────────────────────────────────┐
                     │  LangGraph StateGraph (typed state) │
                     │                                      │
                     │  guardrails → plan → human-approval │
                     │     → draft → review → (loop ≤ 2)   │
                     │     → publish                        │
                     └────┬───────────────┬────────────────┘
                          │               │
                  ┌───────▼────┐    ┌─────▼──────────┐
                  │  pgvector  │    │   PostBoost     │
                  │   (RAG     │    │   API (real)    │
                  │  context)  │    │                 │
                  └────────────┘    └─────────────────┘
                          │
                  ┌───────▼────────────┐
                  │   PostgreSQL       │
                  │  users · posts ·   │
                  │  context_chunks    │
                  └────────────────────┘

           Cross-cutting:  LangSmith traces · Pydantic schemas everywhere
                           Cost cap + iteration cap enforced in state
                           Prompt-injection guardrails before LLM calls
```

Six bounded units, each independently testable. See the
[design spec](docs/superpowers/specs/2026-04-26-linkedin-agent-2week-mvp-design.md#22-six-bounded-units)
for the full breakdown.

---

## Eval methodology *(populated after Day 5)*

| Metric | Value |
|---|---|
| Dataset size | 15 hand-curated topics |
| Judge model | GPT-4o-mini (different family from the drafter to eliminate self-judge bias) |
| Drafter model | Gemini 2.5 Flash |
| Criteria | Tone match · Technical density · Hook strength · AI-cliché detection (4 axes) |
| Baseline avg score | _TBD after Day 5 run_ |
| Re-draft trigger rate | _TBD_ |
| p50 / p95 latency | _TBD_ |
| Cost per published post | _TBD_ |

Cassette-based smoke eval runs in CI for regression detection on every push;
full quality eval runs manually before each release via `scripts/run_eval.py`.

---

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| Agent framework | LangChain 1.x + LangGraph 1.x | Stateful loops, conditional edges, human-in-the-loop interrupt |
| Observability | LangSmith | Traces every token, latency, cost; eval datasets |
| Drafter LLM | Gemini 2.5 Flash | Fast, cost-efficient |
| Judge LLM | OpenAI GPT-4o-mini (via OpenRouter) | Cross-model judging |
| Embeddings | `text-embedding-3-small` | RAG corpus indexing |
| Vector store | **pgvector** (in same Postgres) | Single-DB simplicity vs Qdrant — see [ADR-001](docs/adr/001-pgvector-over-qdrant.md) |
| Schemas | Pydantic 2.x | Typed I/O at every boundary |
| Backend | FastAPI | REST endpoints, JWT auth |
| Dashboard | Streamlit | Auth · new post · pending approvals · history |
| Database | PostgreSQL + pgvector | Drafts, history, vector search |
| Publish | [PostBoost](https://postboost.co) | Real LinkedIn publishing via OAuth |
| Reverse proxy | Caddy | Auto-HTTPS within home network |
| Public access | Cloudflare Tunnel | HTTPS without port-forwarding or exposing home IP |
| Monitoring | Uptime Kuma | Self-hosted status page + alerts |
| Backups | `pg_dump` → Backblaze B2 (encrypted, nightly) | Off-site disaster recovery |
| CI/CD | GitHub Actions | ruff · mypy · pytest · docker build · GHCR · SSH deploy |
| Test recording | `pytest-recording` (VCR) | LLM tests in CI cost $0 |

---

## Project structure

```
linkedin-agent/
├── src/linkedin_agent/
│   ├── schemas/        # Pydantic models — single source of truth for I/O
│   ├── tools/          # @tool functions (plan, draft, review, retrieve, publish)
│   ├── graph/          # LangGraph StateGraph + node functions
│   ├── api/            # FastAPI app + auth middleware
│   ├── db/             # SQLAlchemy 2.x models + Alembic + repository
│   └── dashboard/      # Streamlit app
├── tests/
│   ├── unit/           # Schema, tool, chunker tests (VCR cassettes)
│   ├── integration/    # Graph flow, API, repository, RAG (pytest-docker pgvector)
│   ├── e2e/            # Streamlit AppTest dashboard flows
│   ├── security/       # Adversarial input suite (10 attacks)
│   └── eval/           # LangSmith eval smoke tests
├── scripts/
│   ├── run_eval.py             # Manual full 15-topic eval runner
│   └── smoke_publish.py        # Manual real PostBoost publish smoke test
├── docs/
│   ├── superpowers/specs/      # Design specs
│   ├── adr/                    # Architecture decision records
│   └── v2-roadmap.md           # Parked features (Telegram, image gen, etc.)
├── archive/
│   ├── 01_base_agent.py        # Tutorial-stage code, kept for history
│   └── 02_agent_tools.py       # Tutorial-stage code, kept for history
├── docker-compose.yml          # api · dashboard · postgres-pgvector · cloudflared · uptime-kuma · caddy
├── Dockerfile                  # Multi-stage build
├── pyproject.toml              # uv-managed deps
├── .env.template               # Placeholders only — never real keys
└── README.md
```

---

## Roadmap

### v1 — 14-Day MVP (current)

See [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) for the day-by-day plan and
[`TASK.md`](TASK.md) for the checklist. High-level shape:

- **Days 1-5:** Schemas, LangGraph, Postgres + pgvector, RAG, eval pipeline.
- **Days 6-11:** FastAPI, Streamlit, guardrails + adversarial suite, real PostBoost publish, deploy, CI.
- **Days 12-14:** Polish, ADRs, demo video, recursive demo (the agent writes its own announcement post).

### v2 — Parked features (post-MVP, see [`docs/v2-roadmap.md`](docs/v2-roadmap.md))

- Telegram bot interface
- Parallel image generation (Gemini Imagen ‖ GPT-image-1) for post hero images
- Playwright/MCP browser-side publish verification
- Multi-provider LLM factory once a second provider is genuinely needed

### Hard cuts (not on any roadmap)

- Auto-connection-request sub-agent — violates LinkedIn ToS, hard cut.

---

## Quickstart

<details>
<summary>Local development</summary>

```bash
# Clone
git clone https://github.com/tusher16/linkedin-agent
cd linkedin-agent

# Install with uv
uv venv --python 3.12
uv sync

# Configure secrets (NEVER commit real keys)
cp .env.template .env  # edit with your own keys

# Bring up local Postgres + pgvector
docker compose up -d postgres-pgvector

# Run migrations
uv run alembic upgrade head

# Index personal context into pgvector
uv run python scripts/index_context.py

# Run the FastAPI backend
uv run uvicorn linkedin_agent.api.main:app --reload

# Run the Streamlit dashboard (separate terminal)
uv run streamlit run src/linkedin_agent/dashboard/app.py
```

</details>

<details>
<summary>Run the test suite</summary>

```bash
# Unit + integration tests
uv run pytest

# With coverage gate
uv run pytest --cov=src --cov-fail-under=75

# Re-record VCR cassettes (only when prompts change)
uv run pytest --record-mode=rewrite

# Full quality eval (manual, hits real LLMs)
uv run python scripts/run_eval.py
```

</details>

---

## Architecture decisions

Three short ADRs explain the load-bearing decisions:

- [ADR-001 — pgvector over Qdrant](docs/adr/001-pgvector-over-qdrant.md)
- [ADR-002 — Cross-model judge for eval](docs/adr/002-cross-model-judge.md)
- [ADR-003 — Outline-first generation with human-in-the-loop](docs/adr/003-outline-first-generation.md)

---

## Security

- `.env` is in `.gitignore`. The committed `.env.template` contains placeholders only.
- Cloudflare Tunnel exposes the service to the public internet without
  port-forwarding or revealing the home IP.
- Prompt-injection guardrails run before any LLM call.
- An adversarial test suite of 10 attacks runs in CI and blocks merge on any
  failure.

---

## Author

Mohammad Obaidullah Tusher — AI Engineer based in Berlin. M.Sc. thesis: semantic
segmentation of historical legal documents using LayoutLMv3.

[LinkedIn](https://linkedin.com/in/tusher16) · [GitHub](https://github.com/tusher16)

## License

MIT.
