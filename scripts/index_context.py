"""Index personal context markdown files into pgvector.

Reads every .md file under `docs/personal/`, chunks each, embeds the chunks
with OpenAI text-embedding-3-small, and upserts them into the
`context_chunks` table. Re-running replaces existing chunks for the same
source_file.

Usage:
    docker compose up -d postgres-pgvector
    .venv/bin/alembic upgrade head
    OPENAI_API_KEY=... .venv/bin/python scripts/index_context.py
    # or pass an explicit directory:
    .venv/bin/python scripts/index_context.py docs/personal
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from linkedin_agent.db import (
    ContextRepository,
    make_engine,
    make_session_factory,
)
from linkedin_agent.rag import chunk_markdown, embed_texts


async def index_directory(directory: Path) -> int:
    """Index every .md file in `directory`. Returns total chunks indexed."""
    md_files = sorted(directory.rglob("*.md"))
    if not md_files:
        print(f"No .md files found under {directory}")
        return 0

    engine = make_engine()
    factory = make_session_factory(engine)
    total_chunks = 0

    try:
        async with factory() as session:
            repo = ContextRepository(session)

            for md_path in md_files:
                rel = str(md_path.relative_to(directory.parent))
                text = md_path.read_text()
                chunks = chunk_markdown(text)
                if not chunks:
                    print(f"  {rel}: no content")
                    continue

                await repo.delete_by_source(rel)
                vectors = embed_texts(chunks)

                for i, (chunk_text, vector) in enumerate(zip(chunks, vectors, strict=True)):
                    await repo.upsert(
                        source_file=rel,
                        chunk_index=i,
                        text=chunk_text,
                        embedding=vector,
                    )

                await session.commit()
                total_chunks += len(chunks)
                print(f"  {rel}: {len(chunks)} chunks indexed")

    finally:
        await engine.dispose()

    return total_chunks


def main() -> int:
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/personal")

    if not directory.is_dir():
        print(f"Not a directory: {directory}", file=sys.stderr)
        return 1

    print(f"Indexing markdown under {directory}/")
    total = asyncio.run(index_directory(directory))
    print(f"\nDone. Indexed {total} chunks total.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
