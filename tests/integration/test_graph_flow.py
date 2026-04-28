"""Integration tests for the LangGraph StateGraph.

Five scenarios from the spec:
1. Happy path: outline → draft (score 8) → publish
2. Forced re-draft: outline → draft (score 5) → review → draft (score 8) → publish
3. Iteration cap: always score 4, terminate FAILED_QUALITY at iter == max
4. Cost cap: cost forced over $0.05, terminate FAILED_COST
5. Human-approval interrupt: graph pauses after plan_outline, resumes successfully
"""

from typing import Any

import pytest
from linkedin_agent.graph import build_graph, nodes
from linkedin_agent.schemas import (
    AgentState,
    DraftOutput,
    OutlineOutput,
    PostStatus,
    ReviewOutput,
)


@pytest.fixture()
def stub_outline() -> OutlineOutput:
    return OutlineOutput(
        hook="Most LinkedIn AI posts read like AI wrote them.",
        bullets=["a" * 12, "b" * 12, "c" * 12],
        closing_question="How do you ground your AI writing?",
    )


@pytest.fixture()
def stub_draft() -> DraftOutput:
    return DraftOutput(text="x" * 200, hashtags=["#AI"], estimated_tokens=180)


def _stub_review(score: int) -> ReviewOutput:
    return ReviewOutput(
        score=score,
        hook_score=score,
        technical_density_score=score,
        tone_match_score=score,
        cliche_detected=score < 6,
        feedback=f"score={score}",
    )


def _patch_tools(
    monkeypatch: pytest.MonkeyPatch,
    *,
    outline: OutlineOutput,
    draft: DraftOutput,
    review_scores: list[int],
) -> dict[str, list[Any]]:
    """Patch the three tool functions used by graph nodes.

    `review_scores` is the sequence of scores to return on successive review
    calls. After the list is exhausted, the last score is reused.
    """
    calls: dict[str, list[Any]] = {"plan": [], "draft": [], "review": []}

    def _plan(topic: str, context: str = "") -> OutlineOutput:
        calls["plan"].append((topic, context))
        return outline

    def _draft(
        topic: str, outline: OutlineOutput, context: str = "", tone: str = "professional"
    ) -> DraftOutput:
        calls["draft"].append((topic, outline.hook, tone))
        return draft

    def _review(d: DraftOutput) -> ReviewOutput:
        idx = min(len(calls["review"]), len(review_scores) - 1)
        score = review_scores[idx]
        calls["review"].append(score)
        return _stub_review(score)

    monkeypatch.setattr(nodes, "plan_outline", _plan)
    monkeypatch.setattr(nodes, "draft_post", _draft)
    monkeypatch.setattr(nodes, "review_post", _review)
    return calls


def _run_to_completion(graph: Any, initial_state: AgentState, thread_id: str = "t1") -> AgentState:
    """Run the graph past the human_approval interrupt to completion."""
    config = {"configurable": {"thread_id": thread_id}}
    # First leg: runs guardrails + plan_outline, then pauses before human_approval
    graph.invoke(initial_state.model_dump(), config=config)
    # Resume: continues through draft → review → terminal
    final = graph.invoke(None, config=config)
    return AgentState.model_validate(final)


class TestHappyPath:
    def test_publishes_when_first_review_passes(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_outline: OutlineOutput,
        stub_draft: DraftOutput,
    ) -> None:
        calls = _patch_tools(monkeypatch, outline=stub_outline, draft=stub_draft, review_scores=[8])
        graph = build_graph()
        state = AgentState(topic="A reasonable topic for the post")
        final = _run_to_completion(graph, state)

        assert final.status == PostStatus.PUBLISHED
        assert final.post_id is not None and final.post_id.startswith("mock_")
        assert final.iteration == 1
        assert len(calls["draft"]) == 1
        assert len(calls["review"]) == 1


class TestForcedRedraft:
    def test_redrafts_then_publishes(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_outline: OutlineOutput,
        stub_draft: DraftOutput,
    ) -> None:
        calls = _patch_tools(
            monkeypatch, outline=stub_outline, draft=stub_draft, review_scores=[5, 8]
        )
        graph = build_graph()
        state = AgentState(topic="A reasonable topic for the post", max_iterations=3)
        final = _run_to_completion(graph, state)

        assert final.status == PostStatus.PUBLISHED
        assert final.iteration == 2
        assert len(calls["draft"]) == 2
        assert len(calls["review"]) == 2
        assert final.review is not None and final.review.score == 8


class TestIterationCap:
    def test_terminates_failed_quality_when_score_never_passes(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_outline: OutlineOutput,
        stub_draft: DraftOutput,
    ) -> None:
        calls = _patch_tools(
            monkeypatch, outline=stub_outline, draft=stub_draft, review_scores=[4, 4, 4]
        )
        graph = build_graph()
        state = AgentState(topic="A reasonable topic for the post", max_iterations=2)
        final = _run_to_completion(graph, state)

        assert final.status == PostStatus.FAILED_QUALITY
        assert final.post_id is None
        assert final.iteration == 2
        assert len(calls["draft"]) == 2


class TestCostCap:
    def test_terminates_failed_cost_when_cost_exceeded(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_outline: OutlineOutput,
        stub_draft: DraftOutput,
    ) -> None:
        _patch_tools(monkeypatch, outline=stub_outline, draft=stub_draft, review_scores=[5, 5])
        graph = build_graph()
        # Start near the cap so first draft+review will exceed it.
        state = AgentState(
            topic="A reasonable topic for the post",
            cost_usd=0.049,
            max_cost_usd=0.05,
            max_iterations=3,
        )
        final = _run_to_completion(graph, state)

        assert final.status == PostStatus.FAILED_COST
        assert final.post_id is None


class TestHumanApprovalInterrupt:
    def test_graph_pauses_then_resumes(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stub_outline: OutlineOutput,
        stub_draft: DraftOutput,
    ) -> None:
        _patch_tools(monkeypatch, outline=stub_outline, draft=stub_draft, review_scores=[8])
        graph = build_graph()
        config = {"configurable": {"thread_id": "interrupt-test"}}

        state = AgentState(topic="A reasonable topic for the post")
        # First leg pauses before human_approval
        intermediate = graph.invoke(state.model_dump(), config=config)
        intermediate_state = AgentState.model_validate(intermediate)
        assert intermediate_state.outline is not None
        assert intermediate_state.draft is None  # has not drafted yet
        assert intermediate_state.status == PostStatus.OUTLINE_PENDING

        # Resume — completes the rest
        final_data = graph.invoke(None, config=config)
        final = AgentState.model_validate(final_data)
        assert final.status == PostStatus.PUBLISHED
        assert final.draft is not None
