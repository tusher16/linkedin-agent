from pydantic import BaseModel, Field

from .draft import DraftOutput
from .outline import OutlineOutput
from .post_status import PostStatus
from .review import ReviewOutput


class AgentState(BaseModel):
    topic: str = Field(..., min_length=5, max_length=500)
    tone: str = Field(default="professional", min_length=3, max_length=50)

    status: PostStatus = PostStatus.QUEUED

    outline: OutlineOutput | None = None
    draft: DraftOutput | None = None
    review: ReviewOutput | None = None

    iteration: int = Field(default=0, ge=0)
    max_iterations: int = Field(default=2, ge=1, le=5)

    cost_usd: float = Field(default=0.0, ge=0.0)
    max_cost_usd: float = Field(default=0.05, gt=0.0)

    post_id: str | None = None
    error_message: str | None = None

    retrieved_context: list[str] = Field(default_factory=list)

    def cost_exceeded(self) -> bool:
        return self.cost_usd > self.max_cost_usd

    def iterations_exceeded(self) -> bool:
        return self.iteration >= self.max_iterations
