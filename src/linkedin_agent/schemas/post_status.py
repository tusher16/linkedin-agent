from enum import StrEnum


class PostStatus(StrEnum):
    QUEUED = "queued"
    OUTLINE_PENDING = "outline_pending"
    READY_TO_PUBLISH = "ready_to_publish"
    PUBLISHED = "published"
    FAILED_QUALITY = "failed_quality"
    FAILED_COST = "failed_cost"
    FAILED_PUBLISH = "failed_publish"
    CANCELLED = "cancelled"
