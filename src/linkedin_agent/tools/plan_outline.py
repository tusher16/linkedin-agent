from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from ..schemas import OutlineOutput
from ._llm import get_drafter_llm

SYSTEM_PROMPT = """You are a LinkedIn content strategist for a senior AI engineer.
Use the AUTHOR CONTEXT below to make the outline personal and authentic.

--- AUTHOR CONTEXT ---
{context}
--- END CONTEXT ---

Produce a structured outline with:
- a hook line (10-300 chars) that opens the post
- 3-7 bullet points covering the main argument
- a closing question that invites engagement (10-300 chars)

Be concrete. No buzzwords. No fluff. Match the author's voice."""


def plan_outline(topic: str, context: str = "", llm: BaseChatModel | None = None) -> OutlineOutput:
    chain_llm = llm or get_drafter_llm(temperature=0.5, max_output_tokens=600)
    structured = chain_llm.with_structured_output(OutlineOutput)

    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM_PROMPT), ("human", "Outline a LinkedIn post about: {topic}")]
    )
    chain = prompt | structured
    result = chain.invoke({"topic": topic, "context": context or "(no context provided)"})
    if not isinstance(result, OutlineOutput):
        raise TypeError(f"Expected OutlineOutput, got {type(result).__name__}")
    return result
