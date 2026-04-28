from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from ..schemas import DraftOutput, OutlineOutput
from ._llm import get_drafter_llm

SYSTEM_PROMPT = """You are a LinkedIn ghostwriter for the author below.
Write in THEIR voice using their context. Make it feel personal, not generic.

--- AUTHOR CONTEXT ---
{context}
--- END CONTEXT ---

Follow the approved outline strictly:
HOOK: {hook}
BULLETS: {bullets}
CLOSING QUESTION: {closing_question}

Rules:
- Short paragraphs (1-2 lines)
- Generous line breaks
- 0-3 hashtags maximum
- No motivational quotes, no "🚀" emojis, no buzzwords
- Tone: {tone}
- Length: 100-700 words"""


def draft_post(
    topic: str,
    outline: OutlineOutput,
    context: str = "",
    tone: str = "professional",
    llm: BaseChatModel | None = None,
) -> DraftOutput:
    chain_llm = llm or get_drafter_llm(temperature=0.7)
    structured = chain_llm.with_structured_output(DraftOutput)

    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM_PROMPT), ("human", "Write the full post about: {topic}")]
    )
    chain = prompt | structured
    result = chain.invoke(
        {
            "topic": topic,
            "context": context or "(no context provided)",
            "hook": outline.hook,
            "bullets": "\n".join(f"- {b}" for b in outline.bullets),
            "closing_question": outline.closing_question,
            "tone": tone,
        }
    )
    if not isinstance(result, DraftOutput):
        raise TypeError(f"Expected DraftOutput, got {type(result).__name__}")
    return result
