from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


PlatformName = Literal["linkedin", "bluesky"]
VersionSource = Literal["generate", "regenerate", "restore"]


class GenerationCreate(BaseModel):
    article_id: UUID
    platforms: list[PlatformName] = Field(min_length=1, max_length=2)

    @field_validator("platforms")
    @classmethod
    def unique_platforms(cls, value: list[PlatformName]) -> list[PlatformName]:
        unique = list(dict.fromkeys(value))
        if not unique:
            raise ValueError("Select a platform")
        return unique


class RelatedInsight(BaseModel):
    title: str
    url: str | None = None


class BlueskySkeet(BaseModel):
    text: str
    char_count: int


class GeneratedPost(BaseModel):
    platform: PlatformName
    hook: str = ""
    body_paragraphs: list[str] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    closing_cta: str = ""
    hashtags: list[str] = Field(default_factory=list)
    article_summary: str = ""
    related_insights: list[RelatedInsight] = Field(default_factory=list)
    posts: list[BlueskySkeet] = Field(default_factory=list)
    full_post: str


class GenerationVersionMeta(BaseModel):
    target_text: str | None = None
    instruction: str | None = None
    replacement_text: str | None = None


class GenerationVersion(BaseModel):
    id: str
    version: int
    full_post: str
    label: str
    source: VersionSource
    created_at: str = ""
    meta: GenerationVersionMeta = Field(default_factory=GenerationVersionMeta)


class GenerationDraft(BaseModel):
    id: str
    article_id: str
    platform: PlatformName
    current_version_id: str = ""
    versions: list[GenerationVersion] = Field(default_factory=list)


class GenerationResponse(BaseModel):
    article_id: str
    posts: list[GeneratedPost] = Field(default_factory=list)
    drafts: list[GenerationDraft] = Field(default_factory=list)


class RegenerateSnippetRequest(BaseModel):
    platform: PlatformName
    full_post: str = Field(min_length=1, max_length=20000)
    target_text: str = Field(min_length=1, max_length=8000)
    instruction: str = Field(min_length=3, max_length=2000)
    article_id: UUID | None = None
    draft_id: UUID | None = None
    label: str | None = None


class RegenerateSnippetResponse(BaseModel):
    platform: PlatformName
    original_full_post: str
    target_text: str
    replacement_text: str
    full_post: str
    occurrences: int = 1
    draft_id: str | None = None
    version: GenerationVersion | None = None
    draft: GenerationDraft | None = None


class AddVersionRequest(BaseModel):
    full_post: str = Field(min_length=1, max_length=20000)
    label: str = Field(min_length=1, max_length=200)
    source: VersionSource = "regenerate"
    target_text: str | None = None
    instruction: str | None = None
    replacement_text: str | None = None


class SetCurrentVersionRequest(BaseModel):
    version_id: UUID

class GenerationJobResponse(BaseModel):
    generation_id: str
    article_id: str
    status: Literal[
        "QUEUED",
        "RUNNING",
        "COMPLETED",
        "FAILED",
        "CANCELLED",
    ]
    posts: list[GeneratedPost] = Field(
        default_factory=list
    )
    drafts: list[GenerationDraft] = Field(
        default_factory=list
    )
    error: str | None = None