import pytest
from linkedin_agent.graph import nodes
from linkedin_agent.schemas import (
    AgentState,
    DraftOutput,
    OutlineOutput,
    PostStatus,
    ReviewOutput,
)


@pytest.fixture()
def outline() -> OutlineOutput:
    return OutlineOutput(
        hook="Most LinkedIn AI posts read like AI wrote them.",
        bullets=["a" * 12, "b" * 12, "c" * 12],
        closing_question="How do you ground your AI writing?",
    )


@pytest.fixture()
def draft() -> DraftOutput:
    return DraftOutput(text="x" * 200, hashtags=["#AI"], estimated_tokens=180)


@pytest.fixture()
def good_review() -> ReviewOutput:
    return ReviewOutput(
        score=8,
        hook_score=8,
        technical_density_score=8,
        tone_match_score=8,
        cliche_detected=False,
        feedback="solid",
    )


@pytest.fixture()
def bad_review() -> ReviewOutput:
    return ReviewOutput(
        score=4,
        hook_score=4,
        technical_density_score=4,
        tone_match_score=5,
        cliche_detected=True,
        feedback="cliched",
    )


class TestGuardrailsNode:
    def test_advances_status(self) -> None:
        state = AgentState(topic="A reasonable topic")
        result = nodes.guardrails_node(state)
        assert result["status"] == PostStatus.OUTLINE_PENDING


class TestPlanOutlineNode:
    def test_writes_outline_and_increments_cost(
        self, monkeypatch: pytest.MonkeyPatch, outline: OutlineOutput
    ) -> None:
        monkeypatch.setattr(nodes, "plan_outline", lambda topic, context="": outline)
        state = AgentState(topic="A reasonable topic", retrieved_context=["c1"])
        result = nodes.plan_outline_node(state)
        assert result["outline"] == outline
        assert result["cost_usd"] == pytest.approx(nodes.COST_PER_OUTLINE)

    def test_skips_if_cost_exceeded(self, outline: OutlineOutput) -> None:
        state = AgentState(topic="A reasonable topic", cost_usd=0.10, max_cost_usd=0.05)
        result = nodes.plan_outline_node(state)
        assert result["status"] == PostStatus.FAILED_COST


class TestHumanApprovalNode:
    def test_pass_through(self) -> None:
        state = AgentState(topic="A reasonable topic")
        assert nodes.human_approval_node(state) == {}


class TestDraftPostNode:
    def test_writes_draft_and_increments_iteration(
        self,
        monkeypatch: pytest.MonkeyPatch,
        outline: OutlineOutput,
        draft: DraftOutput,
    ) -> None:
        monkeypatch.setattr(
            nodes,
            "draft_post",
            lambda topic, outline, context="", tone="professional": draft,
        )
        state = AgentState(topic="topic", outline=outline, iteration=0)
        result = nodes.draft_post_node(state)
        assert result["draft"] == draft
        assert result["iteration"] == 1
        assert result["cost_usd"] == pytest.approx(nodes.COST_PER_DRAFT)

    def test_fails_if_no_outline(self) -> None:
        state = AgentState(topic="topic", outline=None)
        result = nodes.draft_post_node(state)
        assert result["status"] == PostStatus.FAILED_QUALITY

    def test_fails_if_cost_exceeded(self, outline: OutlineOutput) -> None:
        state = AgentState(topic="topic", outline=outline, cost_usd=0.10, max_cost_usd=0.05)
        result = nodes.draft_post_node(state)
        assert result["status"] == PostStatus.FAILED_COST


class TestReviewNode:
    def test_writes_review(
        self, monkeypatch: pytest.MonkeyPatch, draft: DraftOutput, good_review: ReviewOutput
    ) -> None:
        monkeypatch.setattr(nodes, "review_post", lambda d: good_review)
        state = AgentState(topic="topic", draft=draft)
        result = nodes.review_node(state)
        assert result["review"] == good_review

    def test_fails_if_no_draft(self) -> None:
        state = AgentState(topic="topic", draft=None)
        result = nodes.review_node(state)
        assert result["status"] == PostStatus.FAILED_QUALITY


class TestPublishNode:
    def test_publishes_with_post_id(self, draft: DraftOutput) -> None:
        state = AgentState(topic="topic", draft=draft)
        result = nodes.publish_node(state)
        assert result["status"] == PostStatus.PUBLISHED
        assert result["post_id"].startswith("mock_")

    def test_fails_if_no_draft(self) -> None:
        state = AgentState(topic="topic", draft=None)
        result = nodes.publish_node(state)
        assert result["status"] == PostStatus.FAILED_PUBLISH


class TestMarkFailedCost:
    def test_sets_failed_cost(self) -> None:
        state = AgentState(topic="topic", cost_usd=0.10, max_cost_usd=0.05)
        result = nodes.mark_failed_cost(state)
        assert result["status"] == PostStatus.FAILED_COST
        assert "0.10" in result["error_message"] or "0.1000" in result["error_message"]


class TestMarkFailedQuality:
    def test_sets_failed_quality(self, bad_review: ReviewOutput) -> None:
        state = AgentState(topic="topic", iteration=2, review=bad_review)
        result = nodes.mark_failed_quality(state)
        assert result["status"] == PostStatus.FAILED_QUALITY
        assert "2 iterations" in result["error_message"]


class TestShouldRedraft:
    def test_redraft_when_low_score_and_under_iter_cap(
        self, draft: DraftOutput, bad_review: ReviewOutput
    ) -> None:
        state = AgentState(
            topic="topic", draft=draft, review=bad_review, iteration=1, max_iterations=2
        )
        assert nodes.should_redraft(state) == "redraft"

    def test_publish_when_score_high(self, draft: DraftOutput, good_review: ReviewOutput) -> None:
        state = AgentState(topic="topic", draft=draft, review=good_review, iteration=1)
        assert nodes.should_redraft(state) == "publish"

    def test_fail_quality_when_iter_cap_reached(
        self, draft: DraftOutput, bad_review: ReviewOutput
    ) -> None:
        state = AgentState(
            topic="topic", draft=draft, review=bad_review, iteration=2, max_iterations=2
        )
        assert nodes.should_redraft(state) == "fail_quality"

    def test_fail_cost_when_cost_exceeded(
        self, draft: DraftOutput, good_review: ReviewOutput
    ) -> None:
        state = AgentState(
            topic="topic",
            draft=draft,
            review=good_review,
            cost_usd=0.10,
            max_cost_usd=0.05,
        )
        assert nodes.should_redraft(state) == "fail_cost"
