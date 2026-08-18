from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr

    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    name: str | None = None

    sso_provider: str | None = None
    sso_provider_user_id: str | None = None

    last_login: datetime | None = None

    is_active: bool
    is_deleted: bool

    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)