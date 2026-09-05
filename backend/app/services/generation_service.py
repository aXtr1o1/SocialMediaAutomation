import asyncio
import html
import logging
import re
from typing import Any

from app.core.supabase import get_supabase_client
from app.prompts.bluesky_post import BLUESKY_POST_PROMPT
from app.prompts.linkedin_post import LINKEDIN_POST_PROMPT
from app.prompts.regenerate_snippet import REGENERATE_SNIPPET_PROMPT
from app.services.gemini_service import GeminiService
from app.core.config import get_settings

from uuid import uuid4

from app.services.redis_state_service import (
    RedisStateService,
)

log = logging.getLogger(__name__)


_GENERATION_TASKS: dict[str, asyncio.Task] = {}


def _fill(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"<<{key.upper()}>>", value)
    return rendered


def _to_plain_social_text(value: str) -> str:
    """Convert HTML/markdown-ish LLM output into plain LinkedIn/Bluesky text."""
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</p\s*>", "\n\n", text)
    text = re.sub(r"(?is)</(div|h[1-6]|tr)\s*>", "\n", text)
    text = re.sub(r"(?is)<li[^>]*>", "• ", text)
    text = re.sub(r"(?is)</li\s*>", "\n", text)
    text = re.sub(r"(?is)</?(ul|ol)[^>]*>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", "", text)
    text = html.unescape(text)
    text = text.replace("```", "")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _canonicalize_copy_text(value: str) -> str:
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[\u00a0\u2000-\u200b\u202f\ufeff]", " ", text)


def _find_flexible_matches(post: str, target: str) -> list[tuple[int, int]]:
    """Match pasted text even when spaces/newlines differ from the stored post."""
    haystack = _canonicalize_copy_text(post)
    needle = _canonicalize_copy_text(target).strip()
    if not needle:
        return []
    parts = [part for part in re.split(r"\s+", needle) if part]
    if not parts:
        return []
    pattern = r"\s+".join(re.escape(part) for part in parts)
    return [(match.start(), match.end()) for match in re.finditer(pattern, haystack)]


def _version_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "version": int(row.get("version_number") or 1),
        "full_post": str(row.get("full_post") or ""),
        "label": str(row.get("label") or ""),
        "source": str(row.get("source") or "generate"),
        "created_at": str(row.get("created_at") or ""),
        "meta": {
            "target_text": row.get("target_text") or None,
            "instruction": row.get("instruction") or None,
            "replacement_text": row.get("replacement_text") or None,
        },
    }


class GenerationService:
    def __init__(self) -> None:
        self.db = get_supabase_client()
        self.gemini = GeminiService()
        self.redis = RedisStateService()
        self.settings = get_settings()

    async def create(self, *, user_id: str, article_id: str, platforms: list[str]) -> dict[str, Any]:
        article = self._load_article(article_id, user_id=user_id)
        if not article:
            raise ValueError("Processed article was not found")

        jobs: list[tuple[str, Any]] = []
        if "linkedin" in platforms:
            jobs.append(("linkedin", self.gemini.generate_json(_fill(LINKEDIN_POST_PROMPT, article))))
        if "bluesky" in platforms:
            jobs.append(("bluesky", self.gemini.generate_json(_fill(BLUESKY_POST_PROMPT, article))))

        results = await asyncio.gather(*(job[1] for job in jobs))
        posts: list[dict[str, Any]] = []
        drafts: list[dict[str, Any]] = []
        for (platform, _), payload in zip(jobs, results):
            post = self._normalize_linkedin(payload) if platform == "linkedin" else self._normalize_bluesky(payload)
            posts.append(post)
            draft = self._create_draft_with_original(
                user_id=user_id,
                article_id=article_id,
                platform=platform,
                full_post=str(post.get("full_post") or ""),
            )
            drafts.append(draft)

        return {"article_id": article_id, "posts": posts, "drafts": drafts}

    async def regenerate_snippet(
        self,
        *,
        user_id: str,
        platform: str,
        full_post: str,
        target_text: str,
        instruction: str,
        article_id: str | None = None,
        draft_id: str | None = None,
        label: str | None = None,
    ) -> dict[str, Any]:

        post = _canonicalize_copy_text(full_post)
        target = target_text

        if not post.strip():
            raise ValueError("Post content is empty")

        if not target.strip():
            raise ValueError("Paste the exact text you want to change")

        if not instruction.strip():
            raise ValueError("Add a short comment describing what to change")

        matches = _find_flexible_matches(post, target)

        if not matches:
            raise ValueError(
                "That text was not found in the post. Copy and paste it exactly."
            )

        if len(matches) > 1:
            raise ValueError(
                "That text appears more than once. Paste a longer unique section."
            )

        start, end = matches[0]

        matched = post[start:end]
        before = post[max(0, start - self.settings.generation_context_window):start]
        after = post[end:end + self.settings.generation_context_window]

        prompt = _fill(
            REGENERATE_SNIPPET_PROMPT,
            {
                "platform": platform,
                "instruction": instruction.strip(),
                "target_text": matched,
                "before_context": before,
                "after_context": after,
            },
        )


        payload = await self.gemini.generate_json(prompt)

        replacement = _to_plain_social_text(
            str(payload.get("replacement_text") or "")
        )

        if not replacement:
            raise ValueError(
                "Could not regenerate that section. Try a clearer comment."
            )

        merged = post[:start] + replacement + post[end:]

        result: dict[str, Any] = {
            "platform": platform,
            "original_full_post": post,
            "target_text": matched,
            "replacement_text": replacement,
            "full_post": merged,
            "occurrences": 1,
            "draft_id": draft_id,
            "version": None,
            "draft": None,
        }

        if not draft_id and article_id:
            seeded = self._create_draft_with_original(
                user_id=user_id,
                article_id=article_id,
                platform=platform,
                full_post=post,
            )

            draft_id = str(seeded["id"])



        if draft_id:
            version = self.add_version(
                user_id=user_id,
                draft_id=draft_id,
                full_post=merged,
                label=(label or instruction).strip() or "Section update",
                source="regenerate",
                target_text=matched,
                instruction=instruction.strip(),
                replacement_text=replacement,
            )

            draft = self.get_draft(
                user_id=user_id,
                draft_id=draft_id,
            )

            result["version"] = version
            result["draft_id"] = draft_id
            result["draft"] = draft

        return result
    def get_draft(self, *, user_id: str, draft_id: str) -> dict[str, Any]:
        draft = self._get_owned_draft(user_id=user_id, draft_id=draft_id)
        versions = self._list_versions(draft_id)
        current_id = str(draft.get("current_version_id") or "") or (versions[-1]["id"] if versions else "")
        return {
            "id": str(draft["id"]),
            "article_id": str(draft.get("article_id") or ""),
            "platform": str(draft.get("platform") or ""),
            "current_version_id": current_id,
            "versions": versions,
        }

    def add_version(
        self,
        *,
        user_id: str,
        draft_id: str,
        full_post: str,
        label: str,
        source: str,
        target_text: str | None = None,
        instruction: str | None = None,
        replacement_text: str | None = None,
    ) -> dict[str, Any]:
        self._get_owned_draft(user_id=user_id, draft_id=draft_id)
        existing = (
            self.db.table("generation_versions")
            .select("version_number")
            .eq("draft_id", draft_id)
            .order("version_number", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        next_number = int((existing[0].get("version_number") if existing else 0) or 0) + 1
        inserted = (
            self.db.table("generation_versions")
            .insert(
                {
                    "draft_id": draft_id,
                    "version_number": next_number,
                    "full_post": full_post,
                    "label": label[:200],
                    "source": source,
                    "target_text": target_text,
                    "instruction": instruction,
                    "replacement_text": replacement_text,
                }
            )
            .execute()
            .data
            or []
        )
        if not inserted:
            raise RuntimeError("Could not save generation version")
        row = inserted[0]
        from datetime import datetime, timezone

        self.db.table("generation_drafts").update(
            {
                "current_version_id": row["id"],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", draft_id).execute()
        return _version_payload(row)

    def set_current_version(self, *, user_id: str, draft_id: str, version_id: str) -> dict[str, Any]:
        self._get_owned_draft(user_id=user_id, draft_id=draft_id)
        rows = (
            self.db.table("generation_versions")
            .select("*")
            .eq("id", version_id)
            .eq("draft_id", draft_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            raise ValueError("Version was not found")
        from datetime import datetime, timezone

        self.db.table("generation_drafts").update(
            {
                "current_version_id": version_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", draft_id).execute()
        return self.get_draft(user_id=user_id, draft_id=draft_id)

    def delete_version(self, *, user_id: str, draft_id: str, version_id: str) -> dict[str, Any]:
        draft = self._get_owned_draft(user_id=user_id, draft_id=draft_id)
        versions = (
            self.db.table("generation_versions")
            .select("*")
            .eq("draft_id", draft_id)
            .order("version_number")
            .execute()
            .data
            or []
        )
        if len(versions) <= 1:
            raise ValueError("At least one version must be kept")
        index = next((i for i, row in enumerate(versions) if str(row["id"]) == str(version_id)), -1)
        if index < 0:
            raise ValueError("Version was not found")

        self.db.table("generation_versions").delete().eq("id", version_id).eq("draft_id", draft_id).execute()
        remaining = [row for row in versions if str(row["id"]) != str(version_id)]
        current_id = str(draft.get("current_version_id") or "")
        if current_id == str(version_id):
            fallback = remaining[min(index, len(remaining) - 1)]
            from datetime import datetime, timezone

            self.db.table("generation_drafts").update(
                {
                    "current_version_id": fallback["id"],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", draft_id).execute()

        return self.get_draft(user_id=user_id, draft_id=draft_id)

    def _create_draft_with_original(
        self,
        *,
        user_id: str,
        article_id: str,
        platform: str,
        full_post: str,
    ) -> dict[str, Any]:
        draft_rows = (
            self.db.table("generation_drafts")
            .insert(
                {
                    "user_id": user_id,
                    "article_id": article_id,
                    "platform": platform,
                }
            )
            .execute()
            .data
            or []
        )
        if not draft_rows:
            raise RuntimeError("Could not create generation draft. Run the generation_versions SQL migration.")
        draft_id = str(draft_rows[0]["id"])
        version = self.add_version(
            user_id=user_id,
            draft_id=draft_id,
            full_post=full_post,
            label="Original",
            source="generate",
        )
        return {
            "id": draft_id,
            "article_id": article_id,
            "platform": platform,
            "current_version_id": version["id"],
            "versions": [version],
        }

    def _get_owned_draft(self, *, user_id: str, draft_id: str) -> dict[str, Any]:
        rows = (
            self.db.table("generation_drafts")
            .select("*")
            .eq("id", draft_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            raise ValueError("Generation draft was not found")
        return rows[0]

    def _list_versions(self, draft_id: str) -> list[dict[str, Any]]:
        rows = (
            self.db.table("generation_versions")
            .select("*")
            .eq("draft_id", draft_id)
            .order("version_number")
            .execute()
            .data
            or []
        )
        return [_version_payload(row) for row in rows]

    def _load_article(self, article_id: str, *, user_id: str) -> dict[str, str] | None:
        rows = (
            self.db.table("processed_content")
            .select("*")
            .eq("article_id", article_id)
            .eq("created_by", str(user_id))
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
                .eq("created_by", str(user_id))
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
            "content": str(row.get("cleaned_text") or row.get("ai_ready_content") or "")[:self.settings.content_limit],
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
            text = text[:self.settings.bluesky_char_limit]
            if text:
                posts.append({"text": text, "char_count": len(text)})
        if not posts:
            fallback = str(payload.get("full_post") or "").strip()[:self.settings.bluesky_char_limit]
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

    def create_job(
        self,
        *,
        user_id: str,
        article_id: str,
        platforms: list[str],
    ) -> dict[str, Any]:
        generation_id = str(uuid4())

        job = {
            "generation_id": generation_id,
            "user_id": user_id,
            "article_id": article_id,
            "platforms": platforms,
            "status": "QUEUED",
            "posts": [],
            "drafts": [],
            "error": None,
        }

        self.redis.save_generation_job(
            generation_id,
            job,
        )

        return job
    
    async def run_job(
        self,
        generation_id: str,
    ) -> None:
        job = self.redis.get_generation_job(
            generation_id
        )

        if not job:
            return

        self.redis.update_generation_job(
            generation_id,
            status="RUNNING",
        )

        try:
            result = await self.create(
                user_id=str(job["user_id"]),
                article_id=str(job["article_id"]),
                platforms=list(job["platforms"]),
            )

            current = self.redis.get_generation_job(
                generation_id
            )

            if not current:
                return

            if current.get("status") == "CANCELLED":
                return

            self.redis.update_generation_job(
                generation_id,
                status="COMPLETED",
                posts=result.get("posts") or [],
                drafts=result.get("drafts") or [],
            )

            self.redis.update_session(
                str(job["user_id"]),
                current_workflow="content_generation",
                current_step="review",
                selected_source_posts=(
                    self.redis.get_session(
                        str(job["user_id"])
                    ).get("selected_source_posts")
                    or []
                ),
                generated_content=result.get("posts") or [],
                generation_drafts=result.get("drafts") or [],
                target_platforms=list(
                    job["platforms"]
                ),
                generation_status="COMPLETED",
            )

        except asyncio.CancelledError:
            self.redis.update_generation_job(
                generation_id,
                status="CANCELLED",
            )

            self.redis.update_session(
                str(job["user_id"]),
                generation_status="CANCELLED",
            )

        except Exception as exc:
            log.exception(
                "generation_job_failed generation_id=%s",
                generation_id,
            )

            self.redis.update_generation_job(
                generation_id,
                status="FAILED",
                error=str(exc)[:1000],
            )

            self.redis.update_session(
                str(job["user_id"]),
                generation_status="FAILED",
            )

    def cancel_job(
        self,
        generation_id: str,
        user_id: str,
    ) -> dict[str, Any] | None:
        job = self.redis.get_generation_job(
            generation_id
        )

        if not job:
            return None

        if str(job.get("user_id")) != str(user_id):
            return None

        if job.get("status") in {
            "COMPLETED",
            "FAILED",
            "CANCELLED",
        }:
            return job

        self.redis.update_generation_job(
            generation_id,
            status="CANCELLED",
        )

        task = _GENERATION_TASKS.get(
            generation_id
        )

        if task and not task.done():
            task.cancel()

        return self.redis.get_generation_job(
            generation_id
        )