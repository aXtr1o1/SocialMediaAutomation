from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ProcessedContentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    article_id: UUID
    cleaned_text: str | None = None
    original_text: str | None = None
    ai_ready_content: str | None = None
    language: str | None = None
    word_count: int | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime | None = None
