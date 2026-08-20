from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


PlatformName = Literal["linkedin", "bluesky"]


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


class GenerationResponse(BaseModel):
    article_id: str
    posts: list[GeneratedPost] = Field(default_factory=list)
