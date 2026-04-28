from dataclasses import dataclass
from uuid import uuid4

from ..schemas import DraftOutput


@dataclass(frozen=True)
class PublishResult:
    post_id: str
    mock: bool


def publish_via_postboost(draft: DraftOutput) -> PublishResult:
    if not draft.text.strip():
        raise ValueError("Cannot publish an empty draft")
    return PublishResult(post_id=f"mock_{uuid4().hex[:12]}", mock=True)
