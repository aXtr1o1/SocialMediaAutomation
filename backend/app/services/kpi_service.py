from datetime import datetime, timezone
from typing import Any
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


class KPIService:
    def __init__(self) -> None:
        self.db = get_supabase_client()
        self.settings = get_settings()

    def validate(self, article: dict[str, Any], source: dict[str, Any], domain: dict[str, Any],
                 reputation: dict[str, Any], all_articles: list[dict[str, Any]]) -> dict[str, Any]:
        metadata = article.get("crawl_metadata") or {}
        scores, reasons = {}, {}
        moz_da = reputation.get("moz_domain_authority")
        scores["domain_reputation"] = float(moz_da) if moz_da is not None else (100.0 if reputation.get("https_available") else 40.0)
        reasons["domain_reputation"] = "MOZ Domain Authority" if moz_da is not None else "Configured fallback: HTTPS availability"

        dates = [article.get("last_updated_at"), article.get("published_at")]
        freshness = 50.0
        for value in dates:
            if value:
                try:
                    age = max(0, (datetime.now(timezone.utc) - datetime.fromisoformat(str(value).replace("Z", "+00:00"))).days)
                    freshness = max(0.0, 100.0 - min(100.0, age / 365 * 100))
                    break
                except ValueError:
                    pass
        scores["content_freshness"] = freshness
        reasons["content_freshness"] = "Date-based score" if any(dates) else "Configured missing-date fallback"

        author_meta = article.get("author_metadata") or {}
        scores["author_credibility"] = 90.0 if author_meta.get("author") or author_meta.get("publisher") else (55.0 if article.get("author") else 20.0)
        reasons["author_credibility"] = "Structured author/publisher metadata" if author_meta else "Plain author or missing-author fallback"

        citations = metadata.get("citation_urls", []) or metadata.get("external_links", [])
        scores["citation_quality"] = min(100.0, 35.0 + len(citations) * 10.0) if citations else 20.0
        scores["spam"] = max(0.0, 100.0 - float(reputation.get("moz_spam_score", 0) or 0))
        content = str(article.get("content") or "")
        similar = max((fuzz.ratio(content, str(other.get("content") or "")) for other in all_articles if other.get("id") != article.get("id")), default=0.0)
        scores["duplicate_content"] = max(0.0, 100.0 - similar)
        scores["website_quality"] = 100.0 if reputation.get("official_website") and reputation.get("https_available") else 60.0
        context = " ".join([str(domain.get("name") or "")] + [str(x) for x in source.get("subdomain_names", [])])
        scores["content_relevance"] = float(fuzz.token_set_ratio(content[:10000], context)) if content else 0.0
        for key in scores:
            scores[key] = round(max(0.0, min(100.0, scores[key])), 2)
        weights = {"domain_reputation": self.settings.kpi_domain_reputation_weight, "content_freshness": self.settings.kpi_content_freshness_weight,
                   "author_credibility": self.settings.kpi_author_credibility_weight, "citation_quality": self.settings.kpi_citation_quality_weight,
                   "spam": self.settings.kpi_spam_weight, "duplicate_content": self.settings.kpi_duplicate_content_weight,
                   "website_quality": self.settings.kpi_website_quality_weight, "content_relevance": self.settings.kpi_content_relevance_weight}
        overall = round(sum(scores[k] * weights[k] for k in weights), 2)
        passed = overall >= self.settings.kpi_pass_threshold
        result = {**article, "article_id": str(article["id"]), "source_id": str(source["id"]),
                  "domain_id": domain["id"], "subdomain_ids": source.get("subdomain_ids", []),
                  "kpi": {**scores, "overall_score": overall, "status": "PASSED" if passed else "REJECTED", "reasons": reasons},
                  "overall_kpi_score": overall, "validation_status": "PASSED" if passed else "REJECTED",
                  "rejection_stage": None if passed else "KPI_VALIDATION"}
        self.db.table("source_validations").upsert({"source_id": source["id"], "article_id": article["id"],
            "domain_reputation": scores["domain_reputation"], "content_freshness": scores["content_freshness"],
            "author_credibility": scores["author_credibility"], "citation_quality": scores["citation_quality"],
            "spam_score": scores["spam"], "duplicate_content": scores["duplicate_content"],
            "website_quality": scores["website_quality"], "content_relevance": scores["content_relevance"],
            "overall_trust_score": overall, "threshold_passed": passed, "validation_status": result["validation_status"],
            "rejection_stage": result["rejection_stage"], "kpi_details": {"reasons": reasons}}, on_conflict="article_id").execute()
        return result
