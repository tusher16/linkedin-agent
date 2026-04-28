from typing import Annotated

from pydantic import BaseModel, Field

Score = Annotated[int, Field(ge=1, le=10)]


class ReviewOutput(BaseModel):
    score: Score
    hook_score: Score
    technical_density_score: Score
    tone_match_score: Score
    cliche_detected: bool = False
    feedback: str = Field(..., min_length=1, max_length=2000)
