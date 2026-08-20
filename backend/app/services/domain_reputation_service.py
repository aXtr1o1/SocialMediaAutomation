import asyncio
from typing import Any
from urllib.parse import urlparse
import httpx

from app.core.config import get_settings

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class DomainReputationService:
    """Per-source reachability checks for a workflow run."""
    def __init__(self) -> None:
        self.settings = get_settings()

    async def check(self, sources: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        unique = {str(s["id"]): s for s in sources}
        timeout = httpx.Timeout(self.settings.crawler_read_timeout, connect=self.settings.crawler_connect_timeout)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=BROWSER_HEADERS) as client:
            async def one(item):
                source_id, source = item
                url = str(source["url"])
                result = {
                    "https_available": url.startswith("https://"),
                    "domain_age": None,
                    "moz_domain_authority": None,
                    "moz_spam_score": None,
                }
                try:
                    response = await client.get(url)
                    blocked = response.status_code in {401, 403, 429}
                    result.update({
                        "http_status": response.status_code,
                        "official_website": response.is_success or blocked,
                        "bot_blocked": blocked,
                    })
                except Exception as exc:
                    result.update({"official_website": url.startswith("https://"), "error": str(exc)})
                if self.settings.moz_api_key:
                    try:
                        response = await client.get(
                            self.settings.moz_api_url,
                            params={"targets": [urlparse(url).netloc]},
                            headers={"Authorization": f"Bearer {self.settings.moz_api_key.get_secret_value()}"},
                        )
                        if response.is_success:
                            payload = response.json()
                            payload = payload[0] if isinstance(payload, list) else payload
                            result["moz_domain_authority"] = payload.get("domain_authority")
                            result["moz_spam_score"] = payload.get("spam_score")
                    except Exception as exc:
                        result["moz_error"] = str(exc)
                return source_id, result
            return dict(await asyncio.gather(*(one(item) for item in unique.items())))
