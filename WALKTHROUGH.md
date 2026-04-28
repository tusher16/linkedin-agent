# WALKTHROUGH.md — What's Actually Built and Tested

A factual log of progress. Updated as work lands. **Use this to figure out
where to pick up if you (or any AI assistant) come back to the project cold.**

---

## Current state — 2026-04-26

### Status
- ✅ **Planning complete.** Design spec approved by author.
- 🔜 **Day 0 next.** No production code written yet. Tutorial-stage scripts archived.

### Documents in place
- ✅ Design spec: `docs/superpowers/specs/2026-04-26-linkedin-agent-2week-mvp-design.md`
- ✅ README, AGENTS, IMPLEMENTATION_PLAN, TASK, WALKTHROUGH — all consistent with the spec
- ✅ `docs/superpowers/specs/` and `docs/adr/` directories created

### Code in place (tutorial stage, will be archived on Day 0)
- ✅ `01_base_agent.py` — Gemini 2.5 Flash + LCEL chain. Single `run_basic_generation(topic)` function. Tested manually with one topic.
- ✅ `02_agent_tools.py` — 4 tools: `plan_post_outline`, `draft_linkedin_post`, `review_post_quality`, `publish_to_linkedin`. The publish tool is mocked.
- ✅ `my_context.md` — author's personal corpus (will be moved to `docs/personal/` on Day 0 and indexed into pgvector on Day 4).
- ✅ LangSmith tracing verified (`LANGCHAIN_TRACING_V2=true` in `.env`).

### Known issues to fix on Day 0
- 🚨 `.env.template` contains real API keys (Google, OpenRouter, LangSmith, PostBoost). All must be rotated and the template rewritten with placeholders before any push to GitHub.
- ⚠️ Project is not yet a git repository. Day 0 includes `git init` + first commit + push to public GitHub.
- ⚠️ `requirements.txt` is a flat pinned list including transitive dependencies. Day 0 replaces it with `pyproject.toml` + `uv.lock`.
- ⚠️ All code is at the project root. Day 0 restructures into `src/linkedin_agent/{schemas,tools,graph,api,db,dashboard}/` package layout.

---

## Build log (will fill in as days complete)

### Day 0 — Pre-flight
*Status: not started*

### Day 1 — Pydantic schemas + tool refactor
*Status: not started*

### Day 2 — LangGraph StateGraph
*Status: not started*

### Day 3 — PostgreSQL + pgvector
*Status: not started*

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
- These notes are gold for retrospectives and for ADRs that get written later.

**Numbers (if applicable):**
- e.g., baseline eval avg, p50 latency, coverage %.
```

This keeps WALKTHROUGH.md as a reliable record a future-you (or a recruiter who
asks "tell me about a hard bug") can read in 5 minutes and re-derive context.
