import pytest


@pytest.fixture()
def sample_topic() -> str:
    return "Building RAG systems vs fine-tuning LLMs: lessons from my thesis"
