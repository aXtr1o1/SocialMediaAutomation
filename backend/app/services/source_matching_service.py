from collections import defaultdict
from typing import Any

try:
    from rapidfuzz import fuzz
except ImportError:
    from difflib import SequenceMatcher
    class _Fuzz:
        @staticmethod
        def token_set_ratio(a: str, b: str) -> float:
            return SequenceMatcher(None, a.lower(), b.lower()).ratio() * 100
    fuzz = _Fuzz()

from app.core.config import get_settings
from app.core.supabase import get_supabase_client
from app.services.gemini_service import GeminiService


class SourceMatchingService:
    """Post-KPI article relevance filtering; it never selects crawl targets."""
    def __init__(self) -> None:
        self.db = get_supabase_client()
        self.settings = get_settings()
        self.gemini = GeminiService()

    def get_fixed_context(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        domain = self.db.table("domains").select("*").eq("id", self.settings.workflow_domain_id).single().execute().data
        subs = self.db.table("subdomains").select("*").eq("domain_id", self.settings.workflow_domain_id).execute().data or []
        if not domain:
            raise RuntimeError("Configured workflow domain was not found")
        return domain, subs

    def select_subdomains(self, domain: dict[str, Any], subdomains: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{"id": s["id"], "name": s.get("name"), "relevance_score": 100.0,
                 "relevance_reason": "Existing subdomain associated with fixed domain"} for s in subdomains]

    def mapped_sources(self, selected: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ids = [str(s["id"]) for s in selected]
        if not ids:
            return []
        mappings = self.db.table("source_subdomain_mapping").select("source_id,subdomain_id").in_("subdomain_id", ids).execute().data or []
        by_source: dict[str, list[str]] = defaultdict(list)
        for row in mappings:
            sid, sub_id = str(row["source_id"]), str(row["subdomain_id"])
            if sub_id not in by_source[sid]:
                by_source[sid].append(sub_id)
        sources = self.db.table("sources").select("*").in_("id", list(by_source)).execute().data or []
        for source in sources:
            source["subdomain_ids"] = by_source[str(source["id"])]
        return sources

    async def match_article(self, *, article: dict[str, Any], domain: dict[str, Any],
                            subdomains: list[dict[str, Any]]) -> dict[str, Any]:
        terms = [str(domain.get("name") or "")] + [str(s.get("name") or "") for s in subdomains]
        metadata = article.get("crawl_metadata") or {}
        text = " ".join(str(article.get(k) or "") for k in ("title", "description", "content"))
        text += " " + " ".join(str(x) for x in metadata.get("headings", []))
        matched = [term for term in terms if term and term.lower() in text.lower()]
        keyword_score = min(100.0, 100.0 * len(matched) / max(1, len([x for x in terms if x])))
        fuzzy_score = max((fuzz.token_set_ratio(text[:10000], term) for term in terms if term), default=0.0)
        llm = await self.gemini.classify_article(domain=domain, subdomains=subdomains, article=article,
                                                  keyword_score=keyword_score, fuzzy_score=fuzzy_score)
        final = keyword_score * self.settings.source_keyword_weight + fuzzy_score * self.settings.source_fuzzy_weight + llm["score"] * self.settings.source_llm_weight
        relevant = bool(llm["relevant"]) and final >= self.settings.source_relevance_threshold
        return {"article_id": str(article["id"]), "source_id": str(article["source_id"]),
                "keyword_score": round(keyword_score, 2), "matched_terms": matched,
                "fuzzy_score": round(fuzzy_score, 2), "llm_score": llm["score"],
                "llm_relevant": llm["relevant"], "llm_reason": llm["reason"],
                "final_relevance_score": round(final, 2), "final_relevance": relevant,
                "rejection_stage": None if relevant else "RELEVANCE_FILTER"}
