from sqlalchemy.ext.asyncio import AsyncSession

from ..db import ContextRepository
from ..rag import Embedder, embed_texts


async def retrieve_context(
    query: str,
    session: AsyncSession,
    *,
    top_k: int = 3,
    embedder: Embedder | None = None,
) -> list[str]:
    """Retrieve top-k chunks similar to `query` from pgvector.

    Returns the chunk texts in similarity order (best first).
    Falls back to an empty list if `query` is blank.
    """
    if not query.strip():
        return []
    embed_fn = embedder or embed_texts
    vectors = embed_fn([query])
    if not vectors:
        return []
    repo = ContextRepository(session)
    chunks = await repo.search_similar(vectors[0], top_k=top_k)
    return [chunk.text for chunk in chunks]
