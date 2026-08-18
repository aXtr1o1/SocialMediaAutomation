from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class CrawledArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_id: UUID
    url: str
    title: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    content: str | None = None
    summary: str | None = None
    content_hash: str | None = None
    is_processed: bool = False
    duplicate_content: bool = False
