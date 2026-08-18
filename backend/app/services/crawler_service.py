import asyncio
import hashlib
import logging
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from typing import Any

import httpx
import trafilatura
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.core.supabase import get_supabase_client

log = logging.getLogger(__name__)


class CrawlerService:
    def __init__(self) -> None:
        self.db = get_supabase_client()
        self.settings = get_settings()

    def _status(self, name: str) -> str | None:
        response = self.db.table("statuses").select("id").eq("status_name", name.lower()).limit(1).execute()
        rows = (response.data if response is not None else None) or []
        return rows[0]["id"] if rows else None

    async def _get(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        last: Exception | None = None
        for attempt in range(self.settings.crawler_max_retries + 1):
            try:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                return response
            except (httpx.HTTPError, OSError) as exc:
                last = exc
                if attempt < self.settings.crawler_max_retries:
                    delay = float(2 ** attempt)
                    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
                        retry_after = exc.response.headers.get("retry-after")
                        try:
                            delay = max(delay, min(60.0, float(retry_after))) if retry_after else max(delay, 10.0)
                        except ValueError:
                            delay = max(delay, 10.0)
                    await asyncio.sleep(delay)
        raise last or RuntimeError("request failed")

    async def _fetch_page(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        try:
            return await self._get(client, url)
        except httpx.HTTPStatusError as exc:
            # Bot-protection responses can still be accessible in a browser.
            if exc.response.status_code not in (403, 429):
                raise
            rendered = await self._playwright_html(url)
            if not rendered:
                raise
            request = httpx.Request("GET", url)
            return httpx.Response(200, content=rendered, request=request)

    async def _playwright_html(self, url: str) -> str | None:
        """Render only pages where the HTTP response contains no extractable content."""
        try:
            # Playwright's async API attempts to create a subprocess on the
            # current Windows selector loop, which raises NotImplementedError
            # under Uvicorn. Run the sync API in a worker thread instead.
            from playwright.sync_api import sync_playwright

            def render() -> str:
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto(url, wait_until="domcontentloaded", timeout=int(self.settings.crawler_read_timeout * 1000))
                    html = page.content()
                    browser.close()
                    return html

            return await asyncio.to_thread(render)
        except Exception as exc:
            log.info("playwright_fallback_failed", extra={"url": url, "error": str(exc)})
            return None

    def _article_urls(self, html: str, root: str) -> list[str]:
        host = urlparse(root).netloc
        found = [root]
        for link in BeautifulSoup(html, "html.parser").find_all("a", href=True):
            target = urljoin(root, link["href"]).split("#", 1)[0]
            parsed = urlparse(target)
            if parsed.scheme in {"http", "https"} and parsed.netloc == host and target not in found:
                found.append(target)
            if len(found) >= self.settings.crawler_max_articles_per_source:
                break
        return found

    async def crawl_source(self, source: dict[str, Any], client: httpx.AsyncClient) -> dict[str, Any]:
        started = time.perf_counter()
        root = str(source["url"])
        try:
            response = await self._fetch_page(client, root)
            results = []
            for url in self._article_urls(response.text, root):
                try:
                    page = response if url == root else await self._fetch_page(client, url)
                    html = page.text
                    content = trafilatura.extract(html, include_comments=False, include_tables=True) or ""
                    if not content.strip():
                        rendered = await self._playwright_html(url)
                        if rendered:
                            html = rendered
                            content = trafilatura.extract(html, include_comments=False, include_tables=True) or ""
                    if not content.strip():
                        continue
                    soup = BeautifulSoup(html, "html.parser")
                    title = (soup.title.string.strip() if soup.title and soup.title.string else None)
                    description = None
                    desc_tag = soup.find("meta", attrs={"name": "description"})
                    if desc_tag:
                        description = desc_tag.get("content")
                    links = [urljoin(url, a.get("href")).split("#", 1)[0] for a in soup.find_all("a", href=True)]
                    internal = [x for x in links if urlparse(x).netloc == urlparse(root).netloc]
                    external = [x for x in links if urlparse(x).netloc and urlparse(x).netloc != urlparse(root).netloc]
                    metadata = {
                        "headings": [h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "h3"])],
                        "meta_tags": {m.get("name") or m.get("property"): m.get("content") for m in soup.find_all("meta") if (m.get("name") or m.get("property")) and m.get("content")},
                        "canonical_url": (soup.find("link", rel="canonical") or {}).get("href") if soup.find("link", rel="canonical") else None,
                        "internal_links": internal, "external_links": external, "citation_urls": external,
                        "references": [], "http_status": page.status_code, "loading_success": True,
                    }
                    published = None
                    for key in ("article:published_time", "datePublished", "pubdate"):
                        tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
                        if tag and tag.get("content"):
                            published = tag["content"]
                            break
                    record = {"source_id": str(source["id"]), "domain_id": str(source["domain_id"]), "subdomain_ids": source.get("subdomain_ids", []), "url": url, "final_url": str(page.url), "title": title, "description": description, "content": content,
                              "author": None, "published_at": published, "content_hash": hashlib.sha256(content.encode()).hexdigest(),
                              "summary": content[:500], "internal_links": internal, "external_links": external, "citation_urls": external, "crawl_metadata": metadata,
                              "crawled_at": datetime.now(timezone.utc).isoformat(),
                              "status_id": self._status("completed")}
                    saved = self.db.table("crawled_articles").upsert(record, on_conflict="source_id,url").execute().data or []
                    results.append(saved[0] if saved else record)
                except Exception as exc:
                    log.warning("article_failed source_id=%s url=%s error=%s", source["id"], url, exc, exc_info=True)
            return {"source_id": str(source["id"]), "status": "SUCCESS", "articles": results,
                    "response_time": round(time.perf_counter() - started, 3), "final_url": str(response.url), "http_status": response.status_code}
        except Exception as exc:
            log.warning("source_failed source_id=%s url=%s error=%s", source["id"], root, exc, exc_info=True)
            return {"source_id": str(source["id"]), "status": "FAILED", "articles": [], "error": str(exc), "response_time": round(time.perf_counter() - started, 3)}

    async def crawl(self, sources: list[dict[str, Any]], user_id: str | None = None) -> list[dict[str, Any]]:
        limits = httpx.Limits(max_connections=self.settings.crawler_max_concurrency)
        timeout = httpx.Timeout(self.settings.crawler_read_timeout, connect=self.settings.crawler_connect_timeout)
        semaphore = asyncio.Semaphore(self.settings.crawler_max_concurrency)
        async with httpx.AsyncClient(timeout=timeout, limits=limits, headers={"User-Agent": "SocialMediaAutomationBot/1.0"}) as client:
            async def one(source: dict[str, Any]) -> dict[str, Any]:
                async with semaphore:
                    return await self.crawl_source(source, client)
            return await asyncio.gather(*(one(s) for s in sources))

    async def domain_reputation(self, sources: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Cheap pre-crawl checks, cached once per source/domain for this run."""
        unique = {str(s["domain_id"]): s for s in sources}
        timeout = httpx.Timeout(self.settings.crawler_read_timeout, connect=self.settings.crawler_connect_timeout)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            async def check(item: tuple[str, dict[str, Any]]) -> tuple[str, dict[str, Any]]:
                domain_id, source = item
                try:
                    response = await client.head(str(source["url"]))
                    result = {"https_available": str(source["url"]).startswith("https://"), "http_status": response.status_code,
                              "official_website": response.is_success, "domain_age": None, "moz_domain_authority": None, "moz_spam_score": None}
                    if self.settings.moz_api_key:
                        try:
                            moz = await client.get(self.settings.moz_api_url,
                                params={"targets": [urlparse(str(source["url"])).netloc]},
                                headers={"Authorization": f"Bearer {self.settings.moz_api_key.get_secret_value()}"})
                            if moz.is_success:
                                payload = moz.json()
                                values = payload[0] if isinstance(payload, list) else payload
                                result["moz_domain_authority"] = values.get("domain_authority")
                                result["moz_spam_score"] = values.get("spam_score")
                        except Exception as moz_exc:
                            result["moz_error"] = str(moz_exc)
                    return domain_id, result
                except Exception as exc:
                    return domain_id, {"https_available": str(source["url"]).startswith("https://"), "official_website": False,
                                       "domain_age": None, "moz_domain_authority": None, "error": str(exc)}
            values = await asyncio.gather(*(check(x) for x in unique.items()))
        return dict(values)
