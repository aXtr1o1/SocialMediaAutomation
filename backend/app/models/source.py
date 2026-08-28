from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SourceCreate(BaseModel):
    url: HttpUrl
    domain_id: UUID
    source_type: str = Field(
        min_length=1, 
        max_length=100,
    )
    description: Optional[str] = None
    status_id: Optional[UUID] = None


class SourceUpdate(BaseModel):
    url: Optional[HttpUrl] = None
    source_type: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    description: Optional[str] = None
    status_id: Optional[UUID] = None


class SourceResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    url: str
    domain_id: UUID
    source_type: str
    description: Optional[str] = None
    last_crawled_at: Optional[datetime] = None
    next_crawl_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    status_id: Optional[UUID] = None