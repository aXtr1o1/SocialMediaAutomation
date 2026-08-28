import asyncio
import hashlib
import json
import logging
import time
from collections import deque
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from typing import Any

import httpx
import trafilatura
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.core.supabase import get_supabase_client

log = logging.getLogger(__name__)

SKIP_SUFFIXES = (
    ".css", ".js", ".mjs", ".json", ".map", ".xml",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".avif",
    ".pdf", ".zip", ".gz", ".rar", ".7z",
    ".mp4", ".mp3", ".wav", ".mov",
    ".woff", ".woff2", ".ttf", ".eot",
)

SKIP_PATH_PREFIXES = (
    "/policies", "/policy", "/privacy", "/terms", "/legal", "/cookie",
    "/cdn-cgi", "/business/partners", "/partners/", "/careers", "/jobs",
    "/jvm/", "/api_docs/java", "/javadoc",
)

FALLBACK_PATHS = ("/blog", "/news", "/research")

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

AFFILIATE_MARKERS = (
    "affiliate", "clickbank", "shareasale", "jdoqocy", "doubleclick",
    "amazon.com/gp", "amzn.to", "tag=", "utm_medium=affiliate",
)

QUALITY_CITATION_HOSTS = (
    "doi.org", "arxiv.org", "pubmed", "ncbi.nlm.nih.gov", "ieee.org",
    "acm.org", "nature.com", "sciencedirect.com", "springer.com",
    "scholar.google", "ssrn.com", "nist.gov",
)


class CrawlerService:
    def __init__(self) -> None:
        self.db = get_supabase_client()
        self.settings = get_settings()
        self._host_locks: dict[str, asyncio.Lock] = {}
        self._host_next: dict[str, float] = {}

    def _status(self, name: str) -> str | None:
        response = self.db.table("statuses").select("id").eq("status_name", name.lower()).limit(1).execute()
        rows = (response.data if response is not None else None) or []
        return rows[0]["id"] if rows else None

    def _max_pages(self) -> int | None:
        limit = int(self.settings.crawler_max_articles_per_source or 0)
        return None if limit <= 0 else limit

    def _normalize_url(self, url: str, base: str, root: str | None = None) -> str | None:
        target = urljoin(base, url).split("#", 1)[0].strip()
        parsed = urlparse(target)
        if parsed.scheme not in {"http", "https"}:
            return None
        root_host = urlparse(root or base).netloc.lower()
        if parsed.netloc.lower() != root_host:
            return None
        path = parsed.path or "/"
        lowered = path.lower()
        if any(lowered.endswith(suffix) for suffix in SKIP_SUFFIXES):
            return None
        if self._is_noise_path(lowered, urlparse(root or base).path.lower()):
            return None
        if path != "/" and path.endswith("/"):
            parsed = parsed._replace(path=path.rstrip("/"))
        normalized = parsed._replace(fragment="").geturl()
        if self._is_docs_explosion(normalized, root or base):
            return None
        return normalized

    def _is_docs_explosion(self, url: str, root: str) -> bool:
        host = urlparse(url).netloc.lower()
        root_host = urlparse(root).netloc.lower()
        if "huggingface.co" not in host or host != root_host:
            return False
        path = (urlparse(url).path or "/").lower()
        root_path = (urlparse(root).path or "/").lower()
        return path.startswith("/docs") and not root_path.startswith("/docs")

    def _is_noise_path(self, path: str, root_path: str) -> bool:
        if any(root_path.startswith(prefix) for prefix in SKIP_PATH_PREFIXES):
            return False
        return any(path.startswith(prefix) for prefix in SKIP_PATH_PREFIXES)

    def _seed_urls(self, root_url: str) -> list[str]:
        parsed = urlparse(root_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        seeds = [root_url]
        if (parsed.path or "/") in {"", "/"}:
            for path in FALLBACK_PATHS:
                candidate = self._normalize_url(path, origin, root_url)
                if candidate and candidate not in seeds:
                    seeds.append(candidate)
        return seeds

    def _host_lock(self, host: str) -> asyncio.Lock:
        lock = self._host_locks.get(host)
        if lock is None:
            lock = asyncio.Lock()
            self._host_locks[host] = lock
        return lock

    async def _pace_host(self, url: str) -> None:
        delay = float(self.settings.crawler_request_delay_seconds or 0)
        if delay <= 0:
            return
        host = urlparse(url).netloc.lower()
        async with self._host_lock(host):
            wait = self._host_next.get(host, 0.0) - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._host_next[host] = time.monotonic() + delay

    def _page_links(self, html: str, page_url: str, root: str) -> list[str]:
        links: list[str] = []
        seen: set[str] = set()
        for tag in BeautifulSoup(html, "html.parser").find_all("a", href=True):
            target = self._normalize_url(str(tag["href"]), page_url or root, root)
            if target and target not in seen:
                seen.add(target)
                links.append(target)
        return links

    async def _sitemap_urls(self, client: httpx.AsyncClient, root: str) -> list[str]:
        origin = f"{urlparse(root).scheme}://{urlparse(root).netloc}"
        pending = [f"{origin}/sitemap.xml", f"{origin}/sitemap_index.xml"]
        seen_maps: set[str] = set()
        pages: list[str] = []
        while pending and len(seen_maps) < 25:
            map_url = pending.pop(0)
            if map_url in seen_maps:
                continue
            seen_maps.add(map_url)
            try:
                response = await client.get(map_url, follow_redirects=True)
                if response.status_code >= 400:
                    continue
            except Exception:
                continue
            soup = BeautifulSoup(response.text, "xml")
            locs = [item.get_text(" ", strip=True) for item in soup.find_all("loc")]
            if soup.find("sitemapindex") or any(item.lower().endswith(".xml") for item in locs):
                nested = [item for item in locs if item.lower().endswith(".xml") or "sitemap" in item.lower()]
                if soup.find("sitemapindex") or nested:
                    pending.extend(nested or locs)
                    html_locs = [item for item in locs if item not in nested]
                    for item in html_locs:
                        target = self._normalize_url(item, root)
                        if target:
                            pages.append(target)
                    continue
            for item in locs:
                target = self._normalize_url(item, root)
                if target:
                    pages.append(target)
        return pages

    async def _get(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        last: Exception | None = None
        for attempt in range(self.settings.crawler_max_retries + 1):
            try:
                await self._pace_host(url)
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                return response
            except (httpx.HTTPError, OSError) as exc:
                last = exc
                status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
                if status in {403, 401, 404}:
                    raise
                timed_out = isinstance(exc, (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError, OSError))
                if timed_out and attempt >= 1:
                    raise
                if attempt < self.settings.crawler_max_retries:
                    delay = float(2 ** attempt)
                    if status == 429:
                        retry_after = exc.response.headers.get("retry-after")
                        try:
                            delay = max(delay, min(120.0, float(retry_after))) if retry_after else max(delay, 20.0)
                        except ValueError:
                            delay = max(delay, 20.0)
                        delay = min(120.0, max(delay, 20.0 * (attempt + 1)))
                    elif timed_out:
                        delay = 2.0
                    await asyncio.sleep(delay)
        raise last or RuntimeError("request failed")

    async def _fetch_page(self, client: httpx.AsyncClient, url: str, *, use_playwright: bool = False) -> httpx.Response:
        try:
            return await self._get(client, url)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 403 or not use_playwright:
                raise
            rendered = await self._playwright_html(url)
            if not rendered:
                raise
            request = httpx.Request("GET", url)
            return httpx.Response(200, content=rendered, request=request)

    async def _playwright_html(self, url: str) -> str | None:
        try:
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

    def _ld_nodes(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            text = script.string or script.get_text() or ""
            try:
                payload = json.loads(text)
            except (TypeError, ValueError):
                continue
            pending = payload if isinstance(payload, list) else [payload]
            while pending:
                item = pending.pop(0)
                if not isinstance(item, dict):
                    continue
                nodes.append(item)
                graph = item.get("@graph")
                if isinstance(graph, list):
                    pending.extend(node for node in graph if isinstance(node, dict))
        return nodes

    def _ld_types(self, node: dict[str, Any]) -> set[str]:
        value = node.get("@type")
        if isinstance(value, list):
            return {str(item).lower() for item in value}
        if value:
            return {str(value).lower()}
        return set()

    def _ld_name(self, value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, dict):
            return str(value.get("name") or value.get("legalName") or "").strip()
        if isinstance(value, list):
            for item in value:
                name = self._ld_name(item)
                if name:
                    return name
        return ""

    def _structured_metadata(self, soup: BeautifulSoup) -> dict[str, Any]:
        author = ""
        publisher = ""
        organization = ""
        person = ""
        published = ""
        modified = ""
        has_person = False
        has_organization = False
        for node in self._ld_nodes(soup):
            types = self._ld_types(node)
            if "person" in types:
                has_person = True
                person = person or self._ld_name(node)
            if "organization" in types:
                has_organization = True
                organization = organization or self._ld_name(node)
            publisher = publisher or self._ld_name(node.get("publisher"))
            author = author or self._ld_name(node.get("author"))
            published = published or str(node.get("datePublished") or "")
            modified = modified or str(node.get("dateModified") or "")
        return {
            "author": author,
            "publisher": publisher,
            "person": person,
            "organization": organization,
            "has_person": has_person,
            "has_organization": has_organization,
            "date_published": published,
            "date_modified": modified,
        }

    def _meta_content(self, soup: BeautifulSoup, *keys: str) -> str:
        for key in keys:
            tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
            if tag and tag.get("content"):
                return str(tag["content"]).strip()
        return ""

    def _citation_urls(self, soup: BeautifulSoup, external: list[str]) -> tuple[list[str], list[str]]:
        citations: list[str] = []
        references: list[str] = []
        for tag in soup.find_all("a", href=True):
            href = str(tag["href"])
            parent_names = " ".join(str(parent.name or "") for parent in tag.parents)
            classes = " ".join(tag.get("class") or [])
            text = f"{href} {classes} {parent_names} {tag.get_text(' ', strip=True)}".lower()
            if any(marker in text for marker in ("cite", "reference", "bibliograph", "doi", "arxiv", "pubmed", "citation")):
                references.append(href)
            host = urlparse(urljoin("https://example.com", href)).netloc.lower()
            if any(marker in host or marker in href.lower() for marker in QUALITY_CITATION_HOSTS):
                citations.append(href)
        citations.extend(item for item in external if any(marker in item.lower() for marker in QUALITY_CITATION_HOSTS))
        unique_citations = list(dict.fromkeys(citations))
        unique_references = list(dict.fromkeys(references))
        return unique_citations, unique_references

    def _affiliate_count(self, links: list[str]) -> int:
        return sum(1 for link in links if any(marker in link.lower() for marker in AFFILIATE_MARKERS))

    def _popup_signals(self, html: str) -> int:
        lowered = html.lower()
        markers = ("cookie-consent", "cookieconsent", "newsletter-modal", "popup-overlay", "modal-open", "optinmonster")
        return sum(1 for marker in markers if marker in lowered)

    def _page_payload(
        self,
        *,
        soup: BeautifulSoup,
        html: str,
        page: httpx.Response,
        url: str,
        final_url: str,
        root_url: str,
        content: str,
        source: dict[str, Any],
        user_id: str,
    ) -> dict[str, Any]:
        title = (soup.title.string.strip() if soup.title and soup.title.string else None)
        description = None
        desc_tag = soup.find("meta", attrs={"name": "description"})
        if desc_tag:
            description = desc_tag.get("content")
        links = [urljoin(final_url, a.get("href")).split("#", 1)[0] for a in soup.find_all("a", href=True)]
        internal = [item for item in links if urlparse(item).netloc == urlparse(root_url).netloc]
        external = [item for item in links if urlparse(item).netloc and urlparse(item).netloc != urlparse(root_url).netloc]
        structured = self._structured_metadata(soup)
        citations, references = self._citation_urls(soup, external)
        published = structured.get("date_published") or self._meta_content(
            soup, "article:published_time", "datePublished", "pubdate", "og:published_time",
        )
        modified = structured.get("date_modified") or self._meta_content(
            soup, "article:modified_time", "dateModified", "og:updated_time", "last-modified",
        )
        author = structured.get("author") or structured.get("person") or self._meta_content(soup, "author", "citation_author")
        canonical = (soup.find("link", rel="canonical") or {})
        canonical_url = canonical.get("href") if canonical else None
        history = getattr(page, "history", None) or []
        metadata = {
            "headings": [h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "h3"])],
            "meta_tags": {m.get("name") or m.get("property"): m.get("content") for m in soup.find_all("meta") if (m.get("name") or m.get("property")) and m.get("content")},
            "canonical_url": canonical_url,
            "internal_links": internal,
            "external_links": external,
            "citation_urls": citations or external,
            "references": references,
            "http_status": page.status_code,
            "loading_success": True,
            "https": str(final_url).startswith("https://"),
            "redirect_count": len(history),
            "affiliate_link_count": self._affiliate_count(links),
            "popup_signals": self._popup_signals(html),
            "author_metadata": structured,
            "last_updated_date": modified or None,
            "publish_date": published or None,
        }
        return {
            "created_by": str(user_id),
            "source_id": str(source["id"]),
            "domain_id": str(source["domain_id"]),
            "subdomain_ids": source.get("subdomain_ids", []),
            "url": url,
            "final_url": final_url,
            "title": title,
            "description": description,
            "content": content,
            "author": author or None,
            "published_at": published or None,
            "content_hash": hashlib.sha256(content.encode()).hexdigest(),
            "summary": content[:500],
            "internal_links": internal,
            "external_links": external,
            "citation_urls": citations or external,
            "crawl_metadata": metadata,
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "status_id": self._status("completed"),
        }

    async def crawl_source(
        self,
        source: dict[str, Any],
        client: httpx.AsyncClient,
        *,
        user_id: str,
        on_article_found=None,
        on_page_seen=None,
        should_cancel=None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        root = str(source["url"])
        root_url = self._normalize_url(root, root) or root
        try:
            seeds = [root_url]
            pending: deque[str] = deque(seeds)
            playwright_seeds = {root_url}
            fallbacks_added = False
            for sitemap_url in await self._sitemap_urls(client, root_url):
                if sitemap_url not in pending:
                    pending.append(sitemap_url)

            seen: set[str] = set()
            results: list[dict[str, Any]] = []
            root_page: httpx.Response | None = None
            max_pages = self._max_pages()
            playwright_used = False

            while pending:
                if should_cancel is not None and should_cancel():
                    raise asyncio.CancelledError()
                if max_pages is not None and len(seen) >= max_pages:
                    break
                url = pending.popleft()
                if url in seen:
                    continue
                seen.add(url)
                if on_page_seen is not None and (len(seen) == 1 or len(seen) % 5 == 0):
                    await on_page_seen(source, len(seen), len(results))
                try:
                    use_playwright = not playwright_used and url in playwright_seeds
                    page = await self._fetch_page(client, url, use_playwright=use_playwright)
                    if use_playwright:
                        playwright_used = True
                    if root_page is None:
                        root_page = page
                    html = page.text
                    final_url = str(page.url) if page.url else url
                    for link in self._page_links(html, final_url, root_url):
                        if link not in seen:
                            pending.append(link)

                    content = trafilatura.extract(html, include_comments=False, include_tables=True) or ""
                    if not content.strip() and use_playwright:
                        rendered = await self._playwright_html(url)
                        if rendered:
                            html = rendered
                            content = trafilatura.extract(html, include_comments=False, include_tables=True) or ""
                    if not content.strip():
                        continue

                    soup = BeautifulSoup(html, "html.parser")
                    record = self._page_payload(
                        soup=soup,
                        html=html,
                        page=page,
                        url=url,
                        final_url=final_url,
                        root_url=root_url,
                        content=content,
                        source=source,
                        user_id=user_id,
                    )
                    saved = (
                        self.db.table("crawled_articles")
                        .upsert(record, on_conflict="created_by,source_id,url")
                        .execute()
                        .data
                        or []
                    )
                    row = saved[0] if saved else record
                    if not row.get("crawl_metadata"):
                        row["crawl_metadata"] = record["crawl_metadata"]
                    results.append(row)
                    if on_article_found is not None:
                        await on_article_found(source, row)
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    if status == 429:
                        log.warning("article_rate_limited source_id=%s url=%s", source["id"], url)
                    elif status == 403:
                        log.warning("article_blocked source_id=%s url=%s", source["id"], url)
                        if not fallbacks_added and urlparse(url).path in {"", "/"}:
                            for extra in self._seed_urls(root_url)[1:]:
                                if extra not in seen:
                                    pending.append(extra)
                            fallbacks_added = True
                    elif status == 404:
                        log.warning("article_not_found source_id=%s url=%s", source["id"], url)
                    else:
                        log.warning("article_failed source_id=%s url=%s status=%s", source["id"], url, status)
                    continue
                except Exception as exc:
                    log.warning("article_failed source_id=%s url=%s error=%s", source["id"], url, exc)
                    continue

            if not results and root_page is None:
                log.warning("source_blocked source_id=%s url=%s", source["id"], root)
                return {
                    "source_id": str(source["id"]),
                    "status": "FAILED",
                    "articles": [],
                    "error": "Source blocked crawling (403). Try a blog/news URL or another source.",
                    "response_time": round(time.perf_counter() - started, 3),
                }
            log.warning("source_crawled source_id=%s articles=%s", source["id"], len(results))
            return {"source_id": str(source["id"]), "status": "SUCCESS", "articles": results,
                    "response_time": round(time.perf_counter() - started, 3),
                    "final_url": str(root_page.url) if root_page and root_page.url else root_url,
                    "http_status": root_page.status_code if root_page else 0}
        except Exception as exc:
            log.warning("source_failed source_id=%s url=%s error=%s", source["id"], root, exc, exc_info=True)
            return {"source_id": str(source["id"]), "status": "FAILED", "articles": [], "error": str(exc), "response_time": round(time.perf_counter() - started, 3)}

    async def crawl(
        self,
        sources: list[dict[str, Any]],
        user_id: str | None = None,
        on_source_start=None,
        on_source_done=None,
        on_article_found=None,
        on_page_seen=None,
        should_cancel=None,
    ) -> list[dict[str, Any]]:
        if not user_id:
            raise ValueError("user_id is required to crawl articles")

        limits = httpx.Limits(max_connections=self.settings.crawler_max_concurrency)
        timeout = httpx.Timeout(self.settings.crawler_read_timeout, connect=self.settings.crawler_connect_timeout)
        semaphore = asyncio.Semaphore(self.settings.crawler_max_concurrency)
        results: list[dict[str, Any]] = []
        done_count = 0
        total = len(sources)
        done_lock = asyncio.Lock()

        async with httpx.AsyncClient(timeout=timeout, limits=limits, headers=BROWSER_HEADERS) as client:
            async def one(source: dict[str, Any]) -> dict[str, Any]:
                nonlocal done_count
                if should_cancel is not None and should_cancel():
                    raise asyncio.CancelledError()
                async with semaphore:
                    if should_cancel is not None and should_cancel():
                        raise asyncio.CancelledError()
                    if on_source_start is not None:
                        await on_source_start(source)
                    result = await self.crawl_source(
                        source,
                        client,
                        user_id=str(user_id),
                        on_article_found=on_article_found,
                        on_page_seen=on_page_seen,
                        should_cancel=should_cancel,
                    )
                async with done_lock:
                    done_count += 1
                    current_done = done_count
                if on_source_done is not None:
                    await on_source_done(result, current_done, total, source)
                return result

            gathered = await asyncio.gather(*(one(s) for s in sources), return_exceptions=True)

        for item in gathered:
            if isinstance(item, asyncio.CancelledError):
                raise item
            if isinstance(item, BaseException):
                log.warning("source_gather_failed error=%s", item, exc_info=item)
                continue
            results.append(item)
        if should_cancel is not None and should_cancel():
            raise asyncio.CancelledError()
        return results

    async def domain_reputation(
        self, 
        sources: list[dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
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
