from uuid import UUID
from pydantic import BaseModel


class DomainResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
