import pytest
from linkedin_agent.schemas import (
    AgentState,
    DraftOutput,
    OutlineOutput,
    PostStatus,
    ReviewOutput,
)
from pydantic import ValidationError


class TestPostStatus:
    def test_has_eight_states(self) -> None:
        assert len(PostStatus) == 8

    def test_all_states_are_strings(self) -> None:
        for status in PostStatus:
            assert isinstance(status.value, str)

    def test_state_values(self) -> None:
        expected = {
            "queued",
            "outline_pending",
            "ready_to_publish",
            "published",
            "failed_quality",
            "failed_cost",
            "failed_publish",
            "cancelled",
        }
        assert {s.value for s in PostStatus} == expected


class TestOutlineOutput:
    def test_valid_outline(self) -> None:
        outline = OutlineOutput(
            hook="Most LinkedIn AI posts are written by AI — and it shows.",
            bullets=[
                "AI without context produces generic content",
                "RAG over personal docs fixes voice mismatch",
                "An eval gate catches the worst drafts before publish",
            ],
            closing_question="What's your take on AI-assisted content?",
        )
        assert len(outline.bullets) == 3

    def test_too_few_bullets(self) -> None:
        with pytest.raises(ValidationError):
            OutlineOutput(
                hook="A reasonable hook line for the post",
                bullets=["only one"],
                closing_question="A reasonable closing question?",
            )

    def test_too_many_bullets(self) -> None:
        with pytest.raises(ValidationError):
            OutlineOutput(
                hook="A reasonable hook line for the post",
                bullets=[f"bullet {i}" for i in range(8)],
                closing_question="A reasonable closing question?",
            )

    def test_short_hook_rejected(self) -> None:
        with pytest.raises(ValidationError):
            OutlineOutput(
                hook="short",
                bullets=["a", "b", "c"],
                closing_question="A reasonable closing question?",
            )

    def test_roundtrip(self) -> None:
        outline = OutlineOutput(
            hook="A reasonable hook line for the post",
            bullets=["bullet one here", "bullet two here", "bullet three here"],
            closing_question="A reasonable closing question?",
        )
        restored = OutlineOutput.model_validate(outline.model_dump())
        assert restored == outline


class TestDraftOutput:
    def test_valid_draft(self) -> None:
        draft = DraftOutput(
            text="x" * 100,
            hashtags=["#AI", "#MLOps"],
            estimated_tokens=250,
        )
        assert draft.estimated_tokens == 250

    def test_too_short_text(self) -> None:
        with pytest.raises(ValidationError):
            DraftOutput(text="too short")

    def test_too_many_hashtags(self) -> None:
        with pytest.raises(ValidationError):
            DraftOutput(text="x" * 100, hashtags=["#a", "#b", "#c", "#d"])

    def test_negative_tokens_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DraftOutput(text="x" * 100, estimated_tokens=-1)


class TestReviewOutput:
    def test_valid_review(self) -> None:
        review = ReviewOutput(
            score=8,
            hook_score=7,
            technical_density_score=9,
            tone_match_score=8,
            cliche_detected=False,
            feedback="Strong hook, dense technical detail, no cliches.",
        )
        assert review.score == 8

    @pytest.mark.parametrize("bad_score", [0, 11, -1, 100])
    def test_score_out_of_range(self, bad_score: int) -> None:
        with pytest.raises(ValidationError):
            ReviewOutput(
                score=bad_score,
                hook_score=5,
                technical_density_score=5,
                tone_match_score=5,
                feedback="ok",
            )

    @pytest.mark.parametrize("field", ["hook_score", "technical_density_score", "tone_match_score"])
    def test_subscore_out_of_range(self, field: str) -> None:
        kwargs = {
            "score": 5,
            "hook_score": 5,
            "technical_density_score": 5,
            "tone_match_score": 5,
            "feedback": "ok",
        }
        kwargs[field] = 11
        with pytest.raises(ValidationError):
            ReviewOutput(**kwargs)


class TestAgentState:
    def test_default_status_is_queued(self) -> None:
        state = AgentState(topic="A reasonable topic to write about")
        assert state.status == PostStatus.QUEUED

    def test_default_caps(self) -> None:
        state = AgentState(topic="A reasonable topic to write about")
        assert state.max_iterations == 2
        assert state.max_cost_usd == 0.05

    def test_iterations_exceeded(self) -> None:
        state = AgentState(topic="A reasonable topic", iteration=2, max_iterations=2)
        assert state.iterations_exceeded() is True

    def test_iterations_not_exceeded(self) -> None:
        state = AgentState(topic="A reasonable topic", iteration=1, max_iterations=2)
        assert state.iterations_exceeded() is False

    def test_cost_exceeded(self) -> None:
        state = AgentState(topic="A reasonable topic", cost_usd=0.06, max_cost_usd=0.05)
        assert state.cost_exceeded() is True

    def test_cost_not_exceeded(self) -> None:
        state = AgentState(topic="A reasonable topic", cost_usd=0.04, max_cost_usd=0.05)
        assert state.cost_exceeded() is False

    def test_negative_cost_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AgentState(topic="A reasonable topic", cost_usd=-1.0)

    def test_zero_max_cost_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AgentState(topic="A reasonable topic", max_cost_usd=0.0)

    def test_status_transition(self) -> None:
        state = AgentState(topic="A reasonable topic")
        state.status = PostStatus.OUTLINE_PENDING
        state.status = PostStatus.READY_TO_PUBLISH
        state.status = PostStatus.PUBLISHED
        assert state.status == PostStatus.PUBLISHED

    def test_roundtrip_with_artifacts(self) -> None:
        state = AgentState(
            topic="A reasonable topic to write about",
            outline=OutlineOutput(
                hook="A reasonable hook line for the post",
                bullets=["one bullet here", "two bullet here", "three bullet here"],
                closing_question="A reasonable closing question?",
            ),
        )
        restored = AgentState.model_validate(state.model_dump())
        assert restored.outline == state.outline
