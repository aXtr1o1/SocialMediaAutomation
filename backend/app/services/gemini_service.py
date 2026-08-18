import json
import logging
from typing import Any

from google import genai
from app.core.config import get_settings

log = logging.getLogger(__name__)


class GeminiService:
    def __init__(self) -> None:
        settings = get_settings()
        self.model = settings.gemini_model
        self.client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())

    async def classify_article(self, *, domain: dict[str, Any], subdomains: list[dict[str, Any]],
                               article: dict[str, Any], keyword_score: float,
                               fuzzy_score: float) -> dict[str, Any]:
        prompt = (
            "Classify article relevance using only the supplied metadata. Return strict JSON with "
            "score (0..100), relevant (boolean), and reason (string). Do not browse or use RAG.\n"
            f"DOMAIN={json.dumps(domain, default=str)}\nSUBDOMAINS={json.dumps(subdomains, default=str)}\n"
            f"ARTICLE={json.dumps({k: article.get(k) for k in ('title','description','content','crawl_metadata')}, default=str)[:30000]}\n"
            f"KEYWORD_SCORE={keyword_score}\nFUZZY_SCORE={fuzzy_score}"
        )
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model, contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            value = json.loads(response.text or "{}")
            score = max(0.0, min(100.0, float(value.get("score", 0))))
            relevant = value.get("relevant")
            if not isinstance(relevant, bool):
                relevant = score >= 50
            return {"score": score, "relevant": relevant, "reason": str(value.get("reason", ""))}
        except Exception as exc:
            log.warning("gemini_article_classification_failed error=%s", exc, exc_info=True)
            return {"score": 0.0, "relevant": False, "reason": "Gemini classification unavailable"}
