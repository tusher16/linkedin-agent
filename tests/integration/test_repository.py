"""Integration tests for db.repository against a real PostgreSQL + pgvector.

Requires: `docker compose up -d postgres-pgvector` (see docker-compose.yml)
and `alembic upgrade head` against the test DB.

Each test runs inside a transaction that is rolled back at teardown — no
state leaks between tests. The test DB is the same as the dev DB; the
0001 migration must be applied before this test file is run.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from linkedin_agent.db import (
    EMBEDDING_DIM,
    ContextRepository,
    PostRepository,
    UserRepository,
    make_engine,
    make_session_factory,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _db_available() -> bool:
    """Skip tests if Postgres isn't reachable locally."""
    import socket

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
        # Wipe data between tests; faster than transactional rollback for our scale.
        await s.execute(text("TRUNCATE TABLE context_chunks, posts, users CASCADE"))
        await s.commit()
        yield s
    await engine.dispose()


def _zero_embedding(perturbation: float = 0.0, index: int = 0) -> list[float]:
    """Build a deterministic 1536-dim embedding."""
    vec = [0.0] * EMBEDDING_DIM
    vec[index] = 1.0 + perturbation
    return vec


class TestUserRepository:
    async def test_create_and_get_by_username(self, session: AsyncSession) -> None:
        repo = UserRepository(session)
        created = await repo.create(username="admin", password_hash="hashed")
        await session.commit()

        fetched = await repo.get_by_username("admin")
        assert fetched is not None
        assert fetched.id == created.id

    async def test_get_by_username_missing(self, session: AsyncSession) -> None:
        repo = UserRepository(session)
        assert await repo.get_by_username("nobody") is None


class TestPostRepository:
    async def test_create_get_update(self, session: AsyncSession) -> None:
        repo = PostRepository(session)
        post = await repo.create(topic="A reasonable topic for the post", tone="storytelling")
        await session.commit()
        assert post.id is not None
        assert post.status == "queued"

        fetched = await repo.get(post.id)
        assert fetched is not None and fetched.tone == "storytelling"

        updated = await repo.update_status(post.id, status="published")
        assert updated is not None and updated.status == "published"

    async def test_list_filter_and_delete(self, session: AsyncSession) -> None:
        repo = PostRepository(session)
        a = await repo.create(topic="topic A " * 5)
        b = await repo.create(topic="topic B " * 5)
        await session.commit()

        await repo.update_status(a.id, status="published")
        await session.commit()

        published = await repo.list(status="published")
        assert len(published) == 1 and published[0].id == a.id

        all_posts = await repo.list()
        assert len(all_posts) == 2

        assert await repo.delete(b.id) is True
        await session.commit()
        assert await repo.delete(b.id) is False  # already gone


class TestContextRepository:
    async def test_upsert_and_search_top1(self, session: AsyncSession) -> None:
        repo = ContextRepository(session)

        # Three chunks with embeddings biased toward different basis vectors.
        await repo.upsert(
            source_file="my_context.md",
            chunk_index=0,
            text="thesis on layoutlmv3",
            embedding=_zero_embedding(index=0),
        )
        await repo.upsert(
            source_file="my_context.md",
            chunk_index=1,
            text="aws redshift work",
            embedding=_zero_embedding(index=10),
        )
        await repo.upsert(
            source_file="my_context.md",
            chunk_index=2,
            text="rag systems with pgvector",
            embedding=_zero_embedding(index=100),
        )
        await session.commit()

        # Query close to the third embedding → expect it as top-1
        query = _zero_embedding(perturbation=0.01, index=100)
        hits = await repo.search_similar(query, top_k=1)
        assert len(hits) == 1
        assert hits[0].text == "rag systems with pgvector"

    async def test_search_returns_top_k(self, session: AsyncSession) -> None:
        repo = ContextRepository(session)
        for i in range(5):
            await repo.upsert(
                source_file="my_context.md",
                chunk_index=i,
                text=f"chunk-{i}",
                embedding=_zero_embedding(index=i),
            )
        await session.commit()

        hits = await repo.search_similar(_zero_embedding(index=0), top_k=3)
        assert len(hits) == 3

    async def test_delete_by_source(self, session: AsyncSession) -> None:
        repo = ContextRepository(session)
        for i in range(3):
            await repo.upsert(
                source_file="a.md",
                chunk_index=i,
                text=f"a-{i}",
                embedding=_zero_embedding(index=i),
            )
        await repo.upsert(
            source_file="b.md",
            chunk_index=0,
            text="b-0",
            embedding=_zero_embedding(index=200),
        )
        await session.commit()

        deleted = await repo.delete_by_source("a.md")
        await session.commit()
        assert deleted == 3

        remaining = await repo.search_similar(_zero_embedding(index=200), top_k=10)
        assert len(remaining) == 1
        assert remaining[0].source_file == "b.md"
