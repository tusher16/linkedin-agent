from pydantic import BaseModel, Field


class DraftOutput(BaseModel):
    text: str = Field(..., min_length=50, max_length=3000)
    hashtags: list[str] = Field(default_factory=list, max_length=3)
    estimated_tokens: int = Field(default=0, ge=0)
