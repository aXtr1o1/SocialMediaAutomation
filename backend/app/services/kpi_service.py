from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

try:
    from rapidfuzz import fuzz
except ImportError:
    from difflib import SequenceMatcher

    class _Fuzz:
        @staticmethod
        def ratio(a: str, b: str) -> float:
            return SequenceMatcher(None, a.lower(), b.lower()).ratio() * 100

        token_set_ratio = ratio

    fuzz = _Fuzz()

from app.core.config import get_settings
from app.core.supabase import get_supabase_client

QUALITY_CITATION_HOSTS = (
    "doi.org", "arxiv.org", "pubmed", "ncbi.nlm.nih.gov", "ieee.org",
    "acm.org", "nature.com", "sciencedirect.com", "springer.com",
    "scholar.google", "ssrn.com", "nist.gov",
)


class KPIService:
    def __init__(self) -> None:
        self.db = get_supabase_client()
        self.settings = get_settings()

    def validate(self, article: dict[str, Any], source: dict[str, Any], domain: dict[str, Any],
                 reputation: dict[str, Any], all_articles: list[dict[str, Any]]) -> dict[str, Any]:
        metadata = article.get("crawl_metadata") or {}
        scores, reasons = {}, {}

        scores["domain_reputation"], reasons["domain_reputation"] = self._domain_reputation(reputation)
        scores["content_freshness"], reasons["content_freshness"] = self._content_freshness(article, metadata)
        scores["author_credibility"], reasons["author_credibility"] = self._author_credibility(article, metadata)
        scores["citation_quality"], reasons["citation_quality"] = self._citation_quality(metadata, domain, source)
        scores["spam"], reasons["spam"] = self._spam(reputation, metadata)
        scores["duplicate_content"], reasons["duplicate_content"], is_duplicate = self._duplicate_content(article, all_articles)
        scores["website_quality"], reasons["website_quality"] = self._website_quality(article, metadata, reputation)
        scores["content_relevance"], reasons["content_relevance"] = self._content_relevance(article, metadata, domain, source)

        for key in scores:
            scores[key] = round(max(0.0, min(100.0, scores[key])), 2)

        weights = {
            "domain_reputation": self.settings.kpi_domain_reputation_weight,
            "content_freshness": self.settings.kpi_content_freshness_weight,
            "author_credibility": self.settings.kpi_author_credibility_weight,
            "citation_quality": self.settings.kpi_citation_quality_weight,
            "spam": self.settings.kpi_spam_weight,
            "duplicate_content": self.settings.kpi_duplicate_content_weight,
            "website_quality": self.settings.kpi_website_quality_weight,
            "content_relevance": self.settings.kpi_content_relevance_weight,
        }
        overall = round(sum(scores[key] * weights[key] for key in weights), 2)
        passed = overall >= self.settings.kpi_pass_threshold and not is_duplicate
        result = {
            **article,
            "article_id": str(article["id"]),
            "source_id": str(source["id"]),
            "domain_id": domain["id"],
            "subdomain_ids": source.get("subdomain_ids", []),
            "kpi": {**scores, "overall_score": overall, "status": "PASSED" if passed else "REJECTED", "reasons": reasons},
            "overall_kpi_score": overall,
            "validation_status": "PASSED" if passed else "REJECTED",
            "rejection_stage": None if passed else ("DUPLICATE_CONTENT" if is_duplicate else "KPI_VALIDATION"),
        }
        self.db.table("source_validations").upsert({
            "source_id": source["id"],
            "article_id": article["id"],
            "domain_reputation": scores["domain_reputation"],
            "content_freshness": scores["content_freshness"],
            "author_credibility": scores["author_credibility"],
            "citation_quality": scores["citation_quality"],
            "spam_score": scores["spam"],
            "duplicate_content": scores["duplicate_content"],
            "website_quality": scores["website_quality"],
            "content_relevance": scores["content_relevance"],
            "overall_trust_score": overall,
            "threshold_passed": passed,
            "validation_status": result["validation_status"],
            "rejection_stage": result["rejection_stage"],
            "kpi_details": {"reasons": reasons, "scores": scores},
        }, on_conflict="article_id").execute()
        return result

    def _domain_reputation(self, reputation: dict[str, Any]) -> tuple[float, str]:
        moz_da = reputation.get("moz_domain_authority")
        https_score = 100.0 if reputation.get("https_available") else 40.0
        reachable = 100.0 if reputation.get("official_website") else 55.0
        status = reputation.get("http_status")
        if isinstance(status, int) and 200 <= status < 400:
            status_score = 100.0
        elif reputation.get("bot_blocked") or status in {401, 403, 429}:
            status_score = 75.0
        else:
            status_score = 45.0
        if moz_da is not None:
            score = float(moz_da) * 0.70 + https_score * 0.15 + reachable * 0.15
            return score, "MOZ Domain Authority plus HTTPS/reachability indicators"
        score = https_score * 0.40 + reachable * 0.40 + status_score * 0.20
        return score, "HTTPS, reachability, and HTTP status (403/401 treated as bot-blocked, not a fake site)"

    def _content_freshness(self, article: dict[str, Any], metadata: dict[str, Any]) -> tuple[float, str]:
        dates = [
            article.get("last_updated_at"),
            metadata.get("last_updated_date"),
            article.get("published_at"),
            metadata.get("publish_date"),
        ]
        for value in dates:
            if not value:
                continue
            try:
                age = max(0, (datetime.now(timezone.utc) - datetime.fromisoformat(str(value).replace("Z", "+00:00"))).days)
                score = max(0.0, 100.0 - min(100.0, age / 365 * 100))
                return score, "Date-based score from publish/update metadata"
            except ValueError:
                continue
        return 50.0, "Configured missing-date fallback; no date assumed"

    def _author_credibility(self, article: dict[str, Any], metadata: dict[str, Any]) -> tuple[float, str]:
        structured = metadata.get("author_metadata") or article.get("author_metadata") or {}
        if structured.get("has_person") or structured.get("has_organization") or structured.get("publisher") or structured.get("author"):
            return 90.0, "Structured Schema.org author/Person/Organization/publisher"
        if article.get("author"):
            return 55.0, "Plain-text author name only"
        if article.get("title") and article.get("content"):
            return 45.0, "No byline; article has title and body from the source site"
        return 25.0, "No author or publisher metadata"

    def _citation_quality(self, metadata: dict[str, Any], domain: dict[str, Any], source: dict[str, Any]) -> tuple[float, str]:
        citations = list(metadata.get("citation_urls") or [])
        references = list(metadata.get("references") or [])
        external = list(metadata.get("external_links") or [])
        if not citations and not references and not external:
            return 20.0, "No citations, references, or external links"
        presence = 25.0
        count = min(25.0, (len(set(citations + references)) or len(external)) * 5.0)
        quality_hits = sum(
            1 for url in citations + references + external
            if any(host in url.lower() or urlparse(url).netloc.endswith(".edu") or urlparse(url).netloc.endswith(".gov")
                   for host in QUALITY_CITATION_HOSTS)
        )
        quality = min(25.0, quality_hits * 8.0)
        https_share = 0.0
        pool = citations or references or external
        if pool:
            https_share = 15.0 * (sum(1 for url in pool if str(url).startswith("https://")) / max(1, len(pool)))
        context = " ".join([str(domain.get("name") or "")] + [str(item) for item in source.get("subdomain_names", [])])
        relevance = 0.0
        if pool and context.strip():
            relevance = min(10.0, fuzz.token_set_ratio(" ".join(pool)[:5000], context) / 10.0)
        return presence + count + quality + https_share + relevance, "Presence, count, source type, HTTPS accessibility, and context overlap"

    def _spam(self, reputation: dict[str, Any], metadata: dict[str, Any]) -> tuple[float, str]:
        raw_moz = float(reputation.get("moz_spam_score") or 0)
        moz_clean = max(0.0, 100.0 - raw_moz)
        affiliate = float(metadata.get("affiliate_link_count") or 0)
        redirects = float(metadata.get("redirect_count") or 0)
        popups = float(metadata.get("popup_signals") or 0)
        crawl_penalty = min(100.0, affiliate * 12.0 + max(0.0, redirects - 1) * 10.0 + popups * 8.0)
        crawl_clean = max(0.0, 100.0 - crawl_penalty)
        if reputation.get("moz_spam_score") is not None:
            score = moz_clean * 0.70 + crawl_clean * 0.30
            reason = "Inverted MOZ spam score plus crawl indicators (not raw spam)"
        else:
            score = crawl_clean
            reason = "Crawl-level spam indicators; MOZ spam unavailable"
        return score, reason

    def _duplicate_content(self, article: dict[str, Any], all_articles: list[dict[str, Any]]) -> tuple[float, str, bool]:
        article_id = str(article.get("id") or "")
        url = str(article.get("url") or article.get("final_url") or "").rstrip("/")
        content = str(article.get("content") or "")[:5000]
        content_hash = str(article.get("content_hash") or "")
        max_similarity = 0.0
        for other in all_articles:
            if str(other.get("id") or "") == article_id:
                break
            other_url = str(other.get("url") or other.get("final_url") or "").rstrip("/")
            other_hash = str(other.get("content_hash") or "")
            if url and other_url and url == other_url:
                return 0.0, "Duplicate URL; first copy is kept", True
            if content_hash and other_hash and content_hash == other_hash:
                return 0.0, "Duplicate content hash; first copy is kept", True
            other_content = str(other.get("content") or "")[:5000]
            if content and other_content and len(content) > 200 and len(other_content) > 200:
                content_score = float(fuzz.ratio(content, other_content))
                if content_score >= 85.0:
                    max_similarity = max(max_similarity, content_score)
        if max_similarity >= 85.0:
            return 0.0, "Near-duplicate body of an earlier article; first copy is kept", True
        return 100.0, "No earlier duplicate URL, hash, or body", False

    def _website_quality(self, article: dict[str, Any], metadata: dict[str, Any], reputation: dict[str, Any]) -> tuple[float, str]:
        status = metadata.get("http_status") or article.get("http_status")
        score = 0.0
        if isinstance(status, int) and 200 <= status < 300:
            score += 20.0
        elif isinstance(status, int) and 300 <= status < 400:
            score += 10.0
        url = str(article.get("final_url") or article.get("url") or "")
        if url.startswith("https://") or metadata.get("https") or reputation.get("https_available"):
            score += 15.0
        redirects = int(metadata.get("redirect_count") or 0)
        if redirects <= 1:
            score += 10.0
        elif redirects <= 3:
            score += 5.0
        if metadata.get("canonical_url"):
            score += 10.0
        if article.get("title"):
            score += 8.0
        if article.get("description") or (metadata.get("meta_tags") or {}).get("description"):
            score += 7.0
        if metadata.get("loading_success"):
            score += 10.0
        if reputation.get("official_website"):
            score += 5.0
        internal = metadata.get("internal_links") or article.get("internal_links") or []
        external = metadata.get("external_links") or article.get("external_links") or []
        if internal:
            score += 8.0
        if 1 <= len(external) <= 200:
            score += 7.0
        return score, "HTTP, HTTPS, redirects, canonical, metadata, crawl success, and link structure"

    def _content_relevance(self, article: dict[str, Any], metadata: dict[str, Any],
                           domain: dict[str, Any], source: dict[str, Any]) -> tuple[float, str]:
        context = " ".join([str(domain.get("name") or "")] + [str(item) for item in source.get("subdomain_names", [])])
        parts = [
            str(article.get("title") or ""),
            str(article.get("description") or ""),
            str(article.get("content") or "")[:10000],
            " ".join(str(item) for item in (metadata.get("headings") or [])),
            " ".join(f"{key} {value}" for key, value in (metadata.get("meta_tags") or {}).items()),
        ]
        text = " ".join(part for part in parts if part.strip())
        if not text or not context.strip():
            return 0.0, "Missing article text or selected domain/subdomain context"
        return float(fuzz.token_set_ratio(text, context)), "Title, description, content, and metadata vs selected domain/subdomain context"
