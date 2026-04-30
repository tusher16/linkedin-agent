import pytest
from linkedin_agent.rag import DEFAULT_MAX_CHARS, chunk_markdown


class TestChunkMarkdown:
    def test_empty_input_returns_empty(self) -> None:
        assert chunk_markdown("") == []
        assert chunk_markdown("   \n\n   \t  ") == []

    def test_short_text_returns_single_chunk(self) -> None:
        text = "Short content under the limit."
        chunks = chunk_markdown(text, max_chars=1000)
        assert chunks == [text]

    def test_long_text_splits_into_multiple_chunks(self) -> None:
        text = "\n\n".join(f"Paragraph number {i} with some filler content." for i in range(30))
        chunks = chunk_markdown(text, max_chars=300, overlap=50)
        assert len(chunks) > 1

    def test_chunks_respect_max_chars_with_overlap_tolerance(self) -> None:
        text = "\n\n".join(f"Para {i} " * 10 for i in range(50))
        chunks = chunk_markdown(text, max_chars=500, overlap=100)
        for chunk in chunks:
            assert len(chunk) <= 500 + 200, f"chunk too long: {len(chunk)}"

    def test_no_empty_chunks_in_output(self) -> None:
        # Use long input that forces multi-chunk output
        text = "\n\n".join(f"Filler paragraph {i} with words." for i in range(40))
        chunks = chunk_markdown(text, max_chars=200, overlap=50)
        assert len(chunks) >= 2
        assert all(chunk.strip() for chunk in chunks)

    def test_deterministic(self) -> None:
        text = "\n\n".join(f"p{i}" * 20 for i in range(40))
        a = chunk_markdown(text, max_chars=300, overlap=50)
        b = chunk_markdown(text, max_chars=300, overlap=50)
        assert a == b

    def test_overlap_creates_shared_content(self) -> None:
        # Adjacent chunks must share the literal overlap window: my chunker
        # builds each new chunk as `tail + "\n\n" + paragraph`, so prev's
        # last 50 chars must appear verbatim in the next chunk.
        paragraphs = [f"Section {i}: this paragraph has marker_{i} in it." for i in range(10)]
        text = "\n\n".join(paragraphs)
        chunks = chunk_markdown(text, max_chars=200, overlap=80)
        assert len(chunks) >= 2

        for prev, curr in zip(chunks, chunks[1:], strict=True):
            tail_50 = prev[-50:]
            assert tail_50 in curr, f"\nprev tail: {tail_50!r}\ncurr head: {curr[:200]!r}"

    def test_invalid_max_chars(self) -> None:
        with pytest.raises(ValueError):
            chunk_markdown("abc", max_chars=0)
        with pytest.raises(ValueError):
            chunk_markdown("abc", max_chars=-1)

    def test_invalid_overlap(self) -> None:
        with pytest.raises(ValueError):
            chunk_markdown("abc", max_chars=100, overlap=-1)
        with pytest.raises(ValueError):
            chunk_markdown("abc", max_chars=100, overlap=100)

    def test_default_settings_chunk_realistic_doc(self) -> None:
        text = "\n\n".join(f"## Section {i}\n\n" + ("content " * 30) for i in range(15))
        chunks = chunk_markdown(text)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= DEFAULT_MAX_CHARS + 200
