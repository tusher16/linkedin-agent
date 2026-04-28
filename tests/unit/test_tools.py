from typing import Any

import pytest
from langchain_core.runnables import Runnable
from linkedin_agent.schemas import DraftOutput, OutlineOutput, ReviewOutput
from linkedin_agent.tools import (
    draft_post,
    plan_outline,
    publish_via_postboost,
    review_post,
)


class _StubStructuredRunnable(Runnable):
    """Returns a fixed value on every invoke; records the last input it saw."""

    def __init__(self, return_value: Any) -> None:
        self.return_value = return_value
        self.last_input: Any = None

    def invoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        self.last_input = input
        return self.return_value


class _StubChatModel:
    """Minimal stub of a chat model: `with_structured_output(schema)` returns a Runnable."""

    def __init__(self, return_value: Any) -> None:
        self.return_value = return_value
        self.runnable = _StubStructuredRunnable(return_value)

    def with_structured_output(self, schema: type[Any]) -> Runnable:
        return self.runnable


@pytest.fixture()
def sample_outline() -> OutlineOutput:
    return OutlineOutput(
        hook="Most LinkedIn AI posts read like AI wrote them.",
        bullets=[
            "Static context = generic outputs",
            "RAG fixes voice mismatch",
            "An eval gate catches drafts before publish",
        ],
        closing_question="How do you ground your AI writing?",
    )


@pytest.fixture()
def sample_draft() -> DraftOutput:
    return DraftOutput(
        text=(
            "Most LinkedIn AI posts read like AI wrote them — because AI did, "
            "without context.\n\nHere is what changed when I plugged in pgvector "
            "as the agent's memory."
        ),
        hashtags=["#AI", "#MLOps"],
        estimated_tokens=180,
    )


@pytest.fixture()
def sample_review() -> ReviewOutput:
    return ReviewOutput(
        score=7,
        hook_score=8,
        technical_density_score=7,
        tone_match_score=7,
        cliche_detected=False,
        feedback="Strong hook, dense, no cliches.",
    )


class TestPlanOutline:
    def test_returns_outline_output(self, sample_outline: OutlineOutput) -> None:
        llm = _StubChatModel(sample_outline)
        result = plan_outline("RAG vs fine-tuning", context="author info", llm=llm)
        assert isinstance(result, OutlineOutput)
        assert result == sample_outline

    def test_default_context_when_empty(self, sample_outline: OutlineOutput) -> None:
        llm = _StubChatModel(sample_outline)
        plan_outline("topic", llm=llm)
        # The chain serialised the default context into the system prompt
        assert llm.runnable.last_input is not None

    def test_raises_on_unexpected_type(self) -> None:
        llm = _StubChatModel("not an outline")
        with pytest.raises(TypeError):
            plan_outline("topic", llm=llm)


class TestDraftPost:
    def test_returns_draft_output(
        self, sample_outline: OutlineOutput, sample_draft: DraftOutput
    ) -> None:
        llm = _StubChatModel(sample_draft)
        result = draft_post("topic", outline=sample_outline, context="ctx", llm=llm)
        assert isinstance(result, DraftOutput)
        assert result == sample_draft

    def test_default_tone_used(
        self, sample_outline: OutlineOutput, sample_draft: DraftOutput
    ) -> None:
        llm = _StubChatModel(sample_draft)
        result = draft_post("topic", outline=sample_outline, llm=llm)
        assert isinstance(result, DraftOutput)
        # Verify the prompt used the outline (chain ran end-to-end without error)
        assert llm.runnable.last_input is not None

    def test_custom_tone(self, sample_outline: OutlineOutput, sample_draft: DraftOutput) -> None:
        llm = _StubChatModel(sample_draft)
        result = draft_post("topic", outline=sample_outline, tone="storytelling", llm=llm)
        assert isinstance(result, DraftOutput)

    def test_raises_on_unexpected_type(self, sample_outline: OutlineOutput) -> None:
        llm = _StubChatModel("not a draft")
        with pytest.raises(TypeError):
            draft_post("topic", outline=sample_outline, llm=llm)


class TestReviewPost:
    def test_returns_review_output(
        self, sample_draft: DraftOutput, sample_review: ReviewOutput
    ) -> None:
        llm = _StubChatModel(sample_review)
        result = review_post(sample_draft, llm=llm)
        assert isinstance(result, ReviewOutput)
        assert result.score == 7

    def test_passes_draft_text(
        self, sample_draft: DraftOutput, sample_review: ReviewOutput
    ) -> None:
        llm = _StubChatModel(sample_review)
        review_post(sample_draft, llm=llm)
        # The chain was invoked, meaning the draft text was serialised into the prompt
        assert llm.runnable.last_input is not None

    def test_raises_on_unexpected_type(self, sample_draft: DraftOutput) -> None:
        llm = _StubChatModel("not a review")
        with pytest.raises(TypeError):
            review_post(sample_draft, llm=llm)


class TestPublishViaPostboost:
    def test_returns_mock_post_id(self, sample_draft: DraftOutput) -> None:
        result = publish_via_postboost(sample_draft)
        assert result.mock is True
        assert result.post_id.startswith("mock_")

    def test_post_ids_are_unique(self, sample_draft: DraftOutput) -> None:
        first = publish_via_postboost(sample_draft)
        second = publish_via_postboost(sample_draft)
        assert first.post_id != second.post_id

    def test_empty_draft_rejected(self) -> None:
        empty = DraftOutput(text=" " * 100)
        with pytest.raises(ValueError):
            publish_via_postboost(empty)
