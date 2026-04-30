"""Integration tests for the RAG pipeline against real Postgres + pgvector.

Uses a deterministic stub embedder (no OpenAI calls in CI). Quality test
verifies recall@3 = 100% on three hand-picked (query, expected_chunk_id) tuples.

Requires Postgres + pgvector running. Run with:
    docker compose up -d postgres-pgvector
    .venv/bin/alembic upgrade head
"""

from __future__ import annotations

import os
import socket
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from linkedin_agent.db import (
    EMBEDDING_DIM,
    ContextRepository,
    make_engine,
    make_session_factory,
)
from linkedin_agent.tools.retrieve_context import retrieve_context
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _db_available() -> bool:
    host = os.environ.get("DB_HOST", "localhost")
    port = int(os.environ.get("DB_PORT", "5432"))
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(
    not _db_available(),
    reason="Postgres not running. Start with: docker compose up -d postgres-pgvector",
)


@pytest_asyncio.fixture()
async def session() -> AsyncIterator[AsyncSession]:
    engine = make_engine()
    factory = make_session_factory(engine)
    async with factory() as s:
        await s.execute(text("TRUNCATE TABLE context_chunks, posts, users CASCADE"))
        await s.commit()
        yield s
    await engine.dispose()


# Deterministic "embeddings": each chunk gets a one-hot vector at a unique index.
# A query embedder maps known queries to those same indices, so cosine search
# is exact and reproducible without hitting OpenAI.
QUERY_TO_INDEX = {
    "what is my thesis about layoutlmv3 segmentation": 0,
    "tell me about aws redshift work at home24": 10,
    "lessons from building rag systems with pgvector": 100,
}


def _vec_at(index: int) -> list[float]:
    v = [0.0] * EMBEDDING_DIM
    v[index] = 1.0
    return v


def _stub_query_embedder(texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    for t in texts:
        idx = QUERY_TO_INDEX.get(t.strip().lower(), 999)
        out.append(_vec_at(idx))
    return out


CORPUS = [
    ("my_context.md", 0, "thesis layoutlmv3 segmentation 18 classes class imbalance focal loss", 0),
    ("my_context.md", 1, "django portfolio mysql virtualenv beginner tutorial", 5),
    ("my_context.md", 2, "aws redshift home24 conversion uplift airflow etl", 10),
    ("my_context.md", 3, "tableau dashboards data viz reddit api praw", 20),
    ("my_context.md", 4, "rag pgvector chunking text embedding 3 small", 100),
]


async def _seed_corpus(session: AsyncSession) -> None:
    repo = ContextRepository(session)
    for source, chunk_idx, text_, vec_idx in CORPUS:
        await repo.upsert(
            source_file=source,
            chunk_index=chunk_idx,
            text=text_,
            embedding=_vec_at(vec_idx),
        )
    await session.commit()


class TestRetrieveContextIntegration:
    async def test_top1_match_for_known_query(self, session: AsyncSession) -> None:
        await _seed_corpus(session)
        results = await retrieve_context(
            "lessons from building rag systems with pgvector",
            session=session,
            top_k=1,
            embedder=_stub_query_embedder,
        )
        assert len(results) == 1
        assert "rag pgvector" in results[0]

    async def test_recall_at_3_is_100pct(self, session: AsyncSession) -> None:
        """Three hand-picked tuples — every expected chunk in top-3 of its query."""
        await _seed_corpus(session)

        expectations = [
            (
                "what is my thesis about layoutlmv3 segmentation",
                "thesis layoutlmv3 segmentation",
            ),
            (
                "tell me about aws redshift work at home24",
                "aws redshift home24",
            ),
            (
                "lessons from building rag systems with pgvector",
                "rag pgvector",
            ),
        ]

        hits = 0
        for query, expected_substring in expectations:
            results = await retrieve_context(
                query,
                session=session,
                top_k=3,
                embedder=_stub_query_embedder,
            )
            if any(expected_substring in r for r in results):
                hits += 1

        assert hits == len(
            expectations
        ), f"recall@3 = {hits}/{len(expectations)} (expected {len(expectations)})"

    async def test_blank_query_returns_empty(self, session: AsyncSession) -> None:
        await _seed_corpus(session)
        results = await retrieve_context("", session=session, embedder=_stub_query_embedder)
        assert results == []
