from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ContextChunk, Post, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, username: str, password_hash: str) -> User:
        user = User(username=username, password_hash=password_hash)
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.execute(select(User).where(User.username == username))
        user: User | None = result.scalar_one_or_none()
        return user

    async def get_by_id(self, user_id: UUID) -> User | None:
        user: User | None = await self.session.get(User, user_id)
        return user


class PostRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, topic: str, tone: str = "professional") -> Post:
        post = Post(topic=topic, tone=tone)
        self.session.add(post)
        await self.session.flush()
        return post

    async def get(self, post_id: UUID) -> Post | None:
        post: Post | None = await self.session.get(Post, post_id)
        return post

    async def update_status(
        self,
        post_id: UUID,
        *,
        status: str,
        error_message: str | None = None,
    ) -> Post | None:
        post = await self.get(post_id)
        if post is None:
            return None
        post.status = status
        if error_message is not None:
            post.error_message = error_message
        await self.session.flush()
        return post

    async def list(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Post]:
        stmt = select(Post).order_by(Post.created_at.desc()).limit(limit).offset(offset)
        if status is not None:
            stmt = stmt.where(Post.status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, post_id: UUID) -> bool:
        post = await self.get(post_id)
        if post is None:
            return False
        await self.session.delete(post)
        await self.session.flush()
        return True


class ContextRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self,
        *,
        source_file: str,
        chunk_index: int,
        text: str,
        embedding: list[float],
    ) -> ContextChunk:
        chunk = ContextChunk(
            source_file=source_file,
            chunk_index=chunk_index,
            text=text,
            embedding=embedding,
        )
        self.session.add(chunk)
        await self.session.flush()
        return chunk

    async def search_similar(
        self, query_embedding: list[float], top_k: int = 3
    ) -> list[ContextChunk]:
        # cosine distance — pgvector exposes <=> for cosine, <-> for L2
        stmt = (
            select(ContextChunk)
            .order_by(ContextChunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_source(self, source_file: str) -> int:
        result = await self.session.execute(
            select(ContextChunk).where(ContextChunk.source_file == source_file)
        )
        chunks = list(result.scalars().all())
        for chunk in chunks:
            await self.session.delete(chunk)
        await self.session.flush()
        return len(chunks)
