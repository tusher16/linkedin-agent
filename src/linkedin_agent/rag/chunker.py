DEFAULT_MAX_CHARS = 1200
DEFAULT_OVERLAP = 200


def chunk_markdown(
    text: str,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap: int = DEFAULT_OVERLAP,
) -> list[str]:
    """Split markdown text into overlapping chunks.

    Algorithm: prefer paragraph boundaries (split on \\n\\n). Pack paragraphs
    into chunks until adding another would exceed `max_chars`. Each new chunk
    starts with the trailing `overlap` chars of the previous chunk so context
    isn't lost across the boundary.

    Deterministic: same input → same output.
    """
    if max_chars <= 0:
        raise ValueError(f"max_chars must be positive, got {max_chars}")
    if overlap < 0 or overlap >= max_chars:
        raise ValueError(f"overlap must be in [0, {max_chars}), got {overlap}")

    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if not current:
            current = paragraph
            continue
        candidate = f"{current}\n\n{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.append(current)
            tail = current[-overlap:] if overlap and len(current) > overlap else ""
            if tail and len(tail) + 2 + len(paragraph) <= max_chars:
                current = f"{tail}\n\n{paragraph}"
            else:
                current = paragraph

    if current:
        chunks.append(current)

    return chunks
