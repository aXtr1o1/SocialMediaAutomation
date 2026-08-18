import asyncio
from typing import Any
from urllib.parse import urlparse
import httpx

from app.core.config import get_settings


class DomainReputationService:
    """Domain-only checks, cached once per domain for a workflow run."""
    def __init__(self) -> None:
        self.settings = get_settings()

    async def check(self, sources: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        unique = {str(s["domain_id"]): s for s in sources}
        timeout = httpx.Timeout(self.settings.crawler_read_timeout, connect=self.settings.crawler_connect_timeout)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            async def one(item):
                domain_id, source = item
                result = {"https_available": str(source["url"]).startswith("https://"),
                          "domain_age": None, "moz_domain_authority": None, "moz_spam_score": None}
                try:
                    response = await client.head(str(source["url"]))
                    result.update({"http_status": response.status_code, "official_website": response.is_success})
                except Exception as exc:
                    result.update({"official_website": False, "error": str(exc)})
                if self.settings.moz_api_key:
                    try:
                        response = await client.get(self.settings.moz_api_url,
                            params={"targets": [urlparse(str(source["url"])).netloc]},
                            headers={"Authorization": f"Bearer {self.settings.moz_api_key.get_secret_value()}"})
                        if response.is_success:
                            payload = response.json()
                            payload = payload[0] if isinstance(payload, list) else payload
                            result["moz_domain_authority"] = payload.get("domain_authority")
                            result["moz_spam_score"] = payload.get("spam_score")
                    except Exception as exc:
                        result["moz_error"] = str(exc)
                return domain_id, result
            return dict(await asyncio.gather(*(one(item) for item in unique.items())))
