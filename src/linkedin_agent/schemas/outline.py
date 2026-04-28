from pydantic import BaseModel, Field


class OutlineOutput(BaseModel):
    hook: str = Field(..., min_length=10, max_length=300)
    bullets: list[str] = Field(..., min_length=3, max_length=7)
    closing_question: str = Field(..., min_length=10, max_length=300)
