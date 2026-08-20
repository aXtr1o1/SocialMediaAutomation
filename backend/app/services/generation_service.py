import asyncio
from typing import Any

from app.core.supabase import get_supabase_client
from app.prompts.bluesky_post import BLUESKY_POST_PROMPT
from app.prompts.linkedin_post import LINKEDIN_POST_PROMPT
from app.services.gemini_service import GeminiService

CONTENT_LIMIT = 24000
BLUESKY_CHAR_LIMIT = 300


def _fill(template: str, article: dict[str, str]) -> str:
    rendered = template
    for key, value in article.items():
        rendered = rendered.replace(f"<<{key.upper()}>>", value)
    return rendered


class GenerationService:
    def __init__(self) -> None:
        self.db = get_supabase_client()
        self.gemini = GeminiService()

    async def create(self, *, article_id: str, platforms: list[str]) -> dict[str, Any]:
        article = self._load_article(article_id)
        if not article:
            raise ValueError("Processed article was not found")

        jobs: list[tuple[str, Any]] = []
        if "linkedin" in platforms:
            jobs.append(("linkedin", self.gemini.generate_json(_fill(LINKEDIN_POST_PROMPT, article))))
        if "bluesky" in platforms:
            jobs.append(("bluesky", self.gemini.generate_json(_fill(BLUESKY_POST_PROMPT, article))))

        results = await asyncio.gather(*(job[1] for job in jobs))
        posts = []
        for (platform, _), payload in zip(jobs, results):
            if platform == "linkedin":
                posts.append(self._normalize_linkedin(payload))
            else:
                posts.append(self._normalize_bluesky(payload))

        return {"article_id": article_id, "posts": posts}

    def _load_article(self, article_id: str) -> dict[str, str] | None:
        rows = (
            self.db.table("processed_content")
            .select("*")
            .eq("article_id", article_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            rows = (
                self.db.table("processed_content")
                .select("*")
                .eq("id", article_id)
                .limit(1)
                .execute()
                .data
                or []
            )
        if not rows:
            return None

        row = rows[0]
        meta = row.get("metadata") or {}
        subdomain_name = ""
        subdomain_ids = [str(item) for item in (meta.get("subdomain_ids") or []) if item]
        if subdomain_ids:
            names = (
                self.db.table("subdomains")
                .select("name")
                .in_("id", subdomain_ids)
                .limit(1)
                .execute()
                .data
                or []
            )
            subdomain_name = str((names[0] or {}).get("name") or "") if names else ""

        return {
            "title": str(meta.get("title") or "Untitled"),
            "author": str(meta.get("author") or ""),
            "published_at": str(meta.get("publish_date") or ""),
            "subdomain_name": subdomain_name,
            "source_url": str(meta.get("source_url") or ""),
            "content": str(row.get("cleaned_text") or row.get("ai_ready_content") or "")[:CONTENT_LIMIT],
        }

    def _normalize_linkedin(self, payload: dict[str, Any]) -> dict[str, Any]:
        paragraphs = [str(item).strip() for item in payload.get("body_paragraphs") or [] if str(item).strip()]
        key_points = [str(item).strip() for item in payload.get("key_points") or [] if str(item).strip()]
        hashtags = [self._hashtag(item) for item in payload.get("hashtags") or []]
        hashtags = [item for item in hashtags if item][:5]
        insights = []
        for item in payload.get("related_insights") or []:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            if title:
                insights.append({"title": title, "url": str(item.get("url") or "") or None})
        hook = str(payload.get("hook") or "").strip()
        closing = str(payload.get("closing_cta") or "").strip()
        full_post = str(payload.get("full_post") or "").strip()
        if not full_post:
            parts = [hook, *paragraphs]
            if key_points:
                parts.append("\n".join(key_points))
            parts.append(closing)
            if hashtags:
                parts.append(" ".join(f"#{tag}" for tag in hashtags))
            full_post = "\n\n".join(part for part in parts if part)
        return {
            "platform": "linkedin",
            "hook": hook,
            "body_paragraphs": paragraphs,
            "key_points": key_points,
            "closing_cta": closing,
            "hashtags": hashtags,
            "article_summary": str(payload.get("article_summary") or "").strip(),
            "related_insights": insights[:2],
            "posts": [],
            "full_post": full_post,
        }

    def _normalize_bluesky(self, payload: dict[str, Any]) -> dict[str, Any]:
        raw_posts = payload.get("posts") or []
        posts = []
        for item in raw_posts[:3]:
            text = str(item.get("text") if isinstance(item, dict) else item or "").strip()
            text = text[:BLUESKY_CHAR_LIMIT]
            if text:
                posts.append({"text": text, "char_count": len(text)})
        if not posts:
            fallback = str(payload.get("full_post") or "").strip()[:BLUESKY_CHAR_LIMIT]
            if fallback:
                posts.append({"text": fallback, "char_count": len(fallback)})
        hashtags = [self._hashtag(item).lower() for item in payload.get("hashtags") or []]
        hashtags = [item for item in hashtags if item][:2]
        full_post = str(payload.get("full_post") or "").strip() or "\n\n".join(item["text"] for item in posts)
        return {
            "platform": "bluesky",
            "hook": "",
            "body_paragraphs": [],
            "key_points": [],
            "closing_cta": "",
            "hashtags": hashtags,
            "article_summary": "",
            "related_insights": [],
            "posts": posts,
            "full_post": full_post,
        }

    def _hashtag(self, value: Any) -> str:
        tag = str(value or "").strip().lstrip("#").replace(" ", "")
        return tag
