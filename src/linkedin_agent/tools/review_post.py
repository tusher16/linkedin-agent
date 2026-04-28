from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from ..schemas import DraftOutput, ReviewOutput
from ._llm import get_drafter_llm

SYSTEM_PROMPT = """You are a strict LinkedIn content reviewer.
Score the draft on FOUR criteria, each 1-10:

1. hook_score        — does the first line stop the scroll?
2. technical_density — concrete tools, numbers, decisions vs vague claims
3. tone_match        — does it sound like a senior engineer, not a guru?
4. cliche_detected   — true if AI-cliches appear ("game-changer", "unleash", "in today's world", "🚀", over-emoji, "let's dive in")

Also produce:
- score: a holistic 1-10 (NOT the average — your overall judgement)
- feedback: 1-3 sentences, concrete and actionable

Be harsh. Most LinkedIn posts deserve 4-6. Reserve 8+ for genuinely strong work."""


def review_post(draft: DraftOutput, llm: BaseChatModel | None = None) -> ReviewOutput:
    chain_llm = llm or get_drafter_llm(temperature=0.2, max_output_tokens=600)
    structured = chain_llm.with_structured_output(ReviewOutput)

    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM_PROMPT), ("human", "Review this draft:\n\n{text}")]
    )
    chain = prompt | structured
    result = chain.invoke({"text": draft.text})
    if not isinstance(result, ReviewOutput):
        raise TypeError(f"Expected ReviewOutput, got {type(result).__name__}")
    return result
