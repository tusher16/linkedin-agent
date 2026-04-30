from typing import Protocol

from openai import OpenAI

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536


class Embedder(Protocol):
    def __call__(self, texts: list[str]) -> list[list[float]]: ...


def embed_texts(texts: list[str], *, client: OpenAI | None = None) -> list[list[float]]:
    """Embed a list of texts with OpenAI text-embedding-3-small (1536-dim).

    Pass `client` to inject a stub or a pre-configured client. Default reads
    `OPENAI_API_KEY` from the environment.
    """
    if not texts:
        return []
    api = client or OpenAI()
    response = api.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]
