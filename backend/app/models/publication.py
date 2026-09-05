from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field


class PublicationCreate(BaseModel):
    draft_id: UUID
    connected_account_id: UUID

class PublicationResponse(BaseModel):
    id: UUID
    draft_id: UUID
    version_id: UUID
    status_id: UUID
    status_name: str
    user_id: UUID
    platform_id: UUID
    platform_name: str
    connected_account_id: UUID
    platform_post_id: str | None=None
    platform_response: str | None=None
    error_message: str | None=None
    retry_count: int=0
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None=None
    full_message: str | None=None


class PublicationEventResponse(BaseModel):
    id: UUID
    publication_id: UUID
    event_type: str | None=None
    event_status: str |None=None
    created_at: datetime
    updated_at: datetime
    message: str | None=None

class PublicationDetailResponse(PublicationResponse):
    events: list[PublicationEventResponse] = Field(default_factory=list)

class PublicationListResponse(BaseModel):
    publications: list[PublicationResponse] = Field(default_factory=list)