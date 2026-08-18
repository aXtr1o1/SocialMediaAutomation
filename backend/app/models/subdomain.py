from uuid import UUID
from pydantic import BaseModel


class SubdomainResponse(BaseModel):
    id: UUID
    domain_id: UUID
    name: str
    description: str | None = None
    relevance_score: float | None = None
    reason: str | None = None
