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


class WorkflowRunRequest(BaseModel):
    domain_id: UUID
    subdomain_ids: list[UUID] = Field(min_length=1)


class SourceArticleResponse(BaseModel):
    id: str
    article_id: str
    title: str
    author: str | None = None
    published_at: str | None = None
    subdomain_name: str | None = None
    content: str
    source_url: str | None = None


class WorkflowProgress(BaseModel):
    stage: str = "crawling"
    message: str = ""
    crawled: int = 0
    kpi_passed: int = 0
    match_passed: int = 0
    sources_done: int = 0
    sources_total: int = 0


class WorkflowRunResponse(BaseModel):
    workflow_run_id: str | None = None
    job_status: str
    domain_name: str
    articles: list[SourceArticleResponse] = Field(default_factory=list)
    progress: WorkflowProgress | None = None
