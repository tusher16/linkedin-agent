"""Unit tests for retrieve_context tool + retrieve_context_node."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from linkedin_agent.graph import nodes
from linkedin_agent.schemas import AgentState
from linkedin_agent.tools.retrieve_context import retrieve_context


def _stub_embedder(_: list[str]) -> list[list[float]]:
    return [[0.0] * 1536]


def _make_chunk(text: str) -> Any:
    """MagicMock kwargs do not reliably set arbitrary attributes; assign instead."""
    chunk = MagicMock()
    chunk.text = text
    return chunk


class TestRetrieveContext:
    @pytest.mark.asyncio
    async def test_returns_chunk_texts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        chunk_a = _make_chunk("chunk A")
        chunk_b = _make_chunk("chunk B")
        repo_mock = MagicMock()
        repo_mock.search_similar = AsyncMock(return_value=[chunk_a, chunk_b])

        # String-based path resolves to the actual submodule via sys.modules,
        # avoiding the function/submodule shadowing in tools/__init__.py.
        monkeypatch.setattr(
            "linkedin_agent.tools.retrieve_context.ContextRepository",
            lambda _session: repo_mock,
        )

        result = await retrieve_context(
            "RAG systems",
            session=MagicMock(),
            top_k=2,
            embedder=_stub_embedder,
        )

        assert result == ["chunk A", "chunk B"]
        repo_mock.search_similar.assert_called_once()

    @pytest.mark.asyncio
    async def test_blank_query_returns_empty(self) -> None:
        result = await retrieve_context(
            "   ",
            session=MagicMock(),
            embedder=_stub_embedder,
        )
        assert result == []


class TestRetrieveContextNode:
    def test_blank_topic_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # AgentState validates topic min_length=5, so we need to use a real-looking
        # topic and bypass with a manual state field set.
        state = AgentState(topic="A reasonable seed topic")
        monkeypatch.setattr(state, "topic", "   ", raising=False)
        result = nodes.retrieve_context_node(state)
        assert result == {"retrieved_context": []}

    def test_falls_back_to_empty_when_engine_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def boom(*_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("DB unreachable")

        monkeypatch.setattr(nodes, "make_engine", boom)

        state = AgentState(topic="A reasonable topic for the post")
        result = nodes.retrieve_context_node(state)
        assert result["retrieved_context"] == []
        assert result["cost_usd"] == pytest.approx(nodes.COST_PER_RETRIEVAL)

    def test_returns_chunks_on_happy_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(nodes.asyncio, "run", lambda _coro: ["chunk 1", "chunk 2"])

        state = AgentState(topic="A reasonable topic for the post")
        result = nodes.retrieve_context_node(state)
        assert result["retrieved_context"] == ["chunk 1", "chunk 2"]
        assert result["cost_usd"] == pytest.approx(nodes.COST_PER_RETRIEVAL)
