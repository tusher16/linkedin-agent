import asyncio
from typing import Any

from ..db import make_engine, make_session_factory
from ..schemas import AgentState, PostStatus
from ..tools import (
    draft_post,
    plan_outline,
    publish_via_postboost,
    retrieve_context,
    review_post,
)

# Rough Gemini 2.5 Flash cost estimates per call (USD).
# Real cost tracking comes in Day 5 from LangSmith trace metadata.
COST_PER_OUTLINE = 0.0002
COST_PER_DRAFT = 0.0008
COST_PER_REVIEW = 0.0003
COST_PER_RETRIEVAL = 0.00001  # text-embedding-3-small per query


def guardrails_node(state: AgentState) -> dict[str, Any]:
    # Day 8 wires real prompt-injection detection here.
    # For now: every topic passes; the node only advances status.
    return {"status": PostStatus.OUTLINE_PENDING}


def retrieve_context_node(state: AgentState) -> dict[str, Any]:
    """Fetch top-k context chunks from pgvector for the topic.

    Sync wrapper around the async retrieval. Falls back to empty list on any
    failure so the graph keeps running even if pgvector or OpenAI is down.
    """
    if not state.topic.strip():
        return {"retrieved_context": []}

    async def _retrieve() -> list[str]:
        engine = make_engine()
        try:
            factory = make_session_factory(engine)
            async with factory() as session:
                return await retrieve_context(state.topic, session, top_k=3)
        finally:
            await engine.dispose()

    try:
        chunks = asyncio.run(_retrieve())
    except Exception:
        # Graceful degradation: agent runs without RAG context if it fails.
        chunks = []

    return {
        "retrieved_context": chunks,
        "cost_usd": state.cost_usd + COST_PER_RETRIEVAL,
    }


def plan_outline_node(state: AgentState) -> dict[str, Any]:
    if state.cost_exceeded():
        return {"status": PostStatus.FAILED_COST}
    context = "\n".join(state.retrieved_context)
    outline = plan_outline(state.topic, context=context)
    return {
        "outline": outline,
        "cost_usd": state.cost_usd + COST_PER_OUTLINE,
    }


def human_approval_node(state: AgentState) -> dict[str, Any]:
    # Marker node — the actual pause happens via interrupt_before in builder.
    return {}


def draft_post_node(state: AgentState) -> dict[str, Any]:
    if state.cost_exceeded():
        return {"status": PostStatus.FAILED_COST}
    if state.outline is None:
        return {
            "status": PostStatus.FAILED_QUALITY,
            "error_message": "draft_post_node called without outline",
        }
    context = "\n".join(state.retrieved_context)
    draft = draft_post(state.topic, outline=state.outline, context=context, tone=state.tone)
    return {
        "draft": draft,
        "iteration": state.iteration + 1,
        "cost_usd": state.cost_usd + COST_PER_DRAFT,
    }


def review_node(state: AgentState) -> dict[str, Any]:
    if state.draft is None:
        return {
            "status": PostStatus.FAILED_QUALITY,
            "error_message": "review_node called without draft",
        }
    review = review_post(state.draft)
    return {
        "review": review,
        "cost_usd": state.cost_usd + COST_PER_REVIEW,
    }


def publish_node(state: AgentState) -> dict[str, Any]:
    if state.draft is None:
        return {
            "status": PostStatus.FAILED_PUBLISH,
            "error_message": "publish_node called without draft",
        }
    result = publish_via_postboost(state.draft)
    return {
        "status": PostStatus.PUBLISHED,
        "post_id": result.post_id,
    }


def mark_failed_cost(state: AgentState) -> dict[str, Any]:
    return {
        "status": PostStatus.FAILED_COST,
        "error_message": f"Cost cap exceeded: ${state.cost_usd:.4f} > ${state.max_cost_usd:.4f}",
    }


def mark_failed_quality(state: AgentState) -> dict[str, Any]:
    return {
        "status": PostStatus.FAILED_QUALITY,
        "error_message": (
            f"Quality gate failed after {state.iteration} iterations "
            f"(last score: {state.review.score if state.review else 'n/a'})"
        ),
    }


REDRAFT_THRESHOLD = 7


def should_redraft(state: AgentState) -> str:
    if state.cost_exceeded():
        return "fail_cost"
    if state.review is None:
        return "publish"
    if state.review.score >= REDRAFT_THRESHOLD:
        return "publish"
    if state.iterations_exceeded():
        return "fail_quality"
    return "redraft"
