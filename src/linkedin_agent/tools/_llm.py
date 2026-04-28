from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI


def get_drafter_llm(
    temperature: float = 0.7, max_output_tokens: int | None = None
) -> BaseChatModel:
    kwargs: dict[str, object] = {"model": "gemini-2.5-flash", "temperature": temperature}
    if max_output_tokens is not None:
        kwargs["max_output_tokens"] = max_output_tokens
    return ChatGoogleGenerativeAI(**kwargs)
