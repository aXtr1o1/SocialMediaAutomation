import json
import logging
from typing import Any

from google import genai
from app.core.config import get_settings
from app.prompts.relevance_classify import RELEVANCE_CLASSIFY_PROMPT

log = logging.getLogger(__name__)


def _fill(template: str, values: dict[str, Any]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"<<{key.upper()}>>", str(value if value is not None else ""))
    return rendered


class GeminiService:
    def __init__(self) -> None:
        settings = get_settings()
        self.model = settings.gemini_model
        self.client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
        self.settings = settings

    async def classify_article(self, *, domain: dict[str, Any], subdomains: list[dict[str, Any]],
                               article: dict[str, Any], keyword_score: float,
                               fuzzy_score: float, matched_terms: list[str] | None = None) -> dict[str, Any]:
        metadata = article.get("crawl_metadata") or {}
        headings = metadata.get("headings") or []
        prompt = _fill(RELEVANCE_CLASSIFY_PROMPT, {
            "domain_name": domain.get("name") or "",
            "subdomains": json.dumps(
                [{"name": item.get("name"), "description": item.get("description")} for item in subdomains],
                default=str,
            ),
            "title": article.get("title") or "",
            "description": article.get("description") or "",
            "headings": json.dumps(headings, default=str)[:4000],
            "content": str(article.get("content") or "")[:6000],
            "keyword_score": round(float(keyword_score), 2),
            "fuzzy_score": round(float(fuzzy_score), 2),
            "matched_terms": json.dumps(matched_terms or [], default=str),
        })
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model, contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            value = json.loads(response.text or "{}")
            score = max(0.0, min(100.0, float(value.get("score", 0))))
            relevant = value.get("relevant")
            if not isinstance(relevant, bool):
                relevant = score >= self.settings.source_relevance_threshold
            evidence = value.get("evidence") if isinstance(value.get("evidence"), list) else []
            return {
                "score": score,
                "relevant": relevant,
                "reason": str(value.get("reason", "")),
                "primary_subdomain": str(value.get("primary_subdomain") or ""),
                "evidence": [str(item) for item in evidence if str(item).strip()][:4],
            }
        except Exception as exc:
            log.warning("gemini_article_classification_failed error=%s", exc, exc_info=True)
            fallback = max(0.0, min(100.0, 0.5 * float(keyword_score) + 0.5 * float(fuzzy_score)))
            return {
                "score": round(fallback, 2),
                "relevant": fallback >= self.settings.source_relevance_threshold,
                "reason": "Gemini classification unavailable; used keyword/fuzzy fallback",
                "primary_subdomain": "",
                "evidence": [],
            }

    async def generate_json(self, prompt: str) -> dict[str, Any]:
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        value = json.loads(response.text or "{}")
        if not isinstance(value, dict):
            raise ValueError("Gemini returned invalid JSON")
        return value
