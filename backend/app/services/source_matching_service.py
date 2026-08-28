from collections import defaultdict
import re
from typing import Any

try:
    from rapidfuzz import fuzz
except ImportError:
    from difflib import SequenceMatcher

    class _Fuzz:
        @staticmethod
        def token_set_ratio(a: str, b: str) -> float:
            return SequenceMatcher(None, a.lower(), b.lower()).ratio() * 100

        partial_ratio = token_set_ratio
        WRatio = token_set_ratio

    fuzz = _Fuzz()

from app.core.config import get_settings
from app.core.supabase import get_supabase_client
from app.services.gemini_service import GeminiService

FIELD_WEIGHTS = {"title": 0.40, "headings": 0.25, "description": 0.20, "body": 0.15}
SUBDOMAIN_TERM_WEIGHT = 0.85
DOMAIN_TERM_WEIGHT = 0.15
STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "in", "on", "for", "to", "with", "by",
    "from", "vs", "via", "into", "over", "under", "about", "using",
}


class SourceMatchingService:
    """Post-KPI article relevance filtering; it never selects crawl targets."""
    def __init__(self) -> None:
        self.db = get_supabase_client()
        self.settings = get_settings()
        self.gemini = GeminiService()

    def get_fixed_context(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        allowed_domain_id = str(self.settings.workflow_domain_id)
        domain = (
            self.db.table("domains")
            .select("*")
            .eq("id", allowed_domain_id)
            .single()
            .execute()
            .data
        )
        subs = (
            self.db.table("subdomains")
            .select("*")
            .eq("domain_id", allowed_domain_id)
            .execute()
            .data
            or []
        )
        if not domain:
            raise RuntimeError("Configured workflow domain was not found")
        return domain, subs

    def get_context_for_selection(
        self,
        domain_id: str,
        subdomain_ids: list[str],
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        unique_ids = list(dict.fromkeys(subdomain_ids))
        if not unique_ids:
            raise ValueError("Select at least one subdomain")

        allowed_domain_id = str(self.settings.workflow_domain_id)
        if str(domain_id) != allowed_domain_id:
            raise ValueError("This domain is not available for the current workspace")

        domain_rows = (
            self.db.table("domains")
            .select("*")
            .eq("id", allowed_domain_id)
            .limit(1)
            .execute()
            .data
        )
        domain = domain_rows[0] if domain_rows else None
        if not domain:
            raise ValueError("Domain was not found")

        rows = (
            self.db.table("subdomains")
            .select("*")
            .eq("domain_id", allowed_domain_id)
            .in_("id", unique_ids)
            .execute()
            .data
            or []
        )
        if len(rows) != len(unique_ids):
            raise ValueError("One or more subdomains do not belong to the selected domain")

        selected = [
            {
                "id": row["id"],
                "name": row.get("name"),
                "description": row.get("description"),
                "relevance_score": 100.0,
                "relevance_reason": "User-selected subdomain",
            }
            for row in rows
        ]
        return domain, selected

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
        fields = self._article_fields(article)
        domain_terms = self._term_variants(str(domain.get("name") or ""), str(domain.get("description") or ""))
        subdomain_terms: list[str] = []
        for item in subdomains:
            subdomain_terms.extend(self._term_variants(str(item.get("name") or ""), str(item.get("description") or "")))
        subdomain_terms = list(dict.fromkeys(subdomain_terms))
        domain_terms = [term for term in dict.fromkeys(domain_terms) if term not in subdomain_terms]

        keyword_score, matched_terms, field_keyword = self._keyword_match(fields, subdomain_terms, domain_terms)
        fuzzy_score, best_subdomain_term, field_fuzzy = self._fuzzy_match(fields, subdomain_terms, domain_terms)
        llm = await self.gemini.classify_article(
            domain=domain,
            subdomains=subdomains,
            article=article,
            keyword_score=keyword_score,
            fuzzy_score=fuzzy_score,
            matched_terms=matched_terms,
        )
        llm = self._enforce_llm_accuracy(llm, subdomains)
        title_hit = any(self._token_coverage(fields["title"], term) >= 1.0 for term in subdomain_terms)
        # Deterministic floor only — LLM evidence cannot substitute for lexical signal.
        lexical_ok = keyword_score >= 28 or fuzzy_score >= 40 or title_hit
        final = (
            keyword_score * self.settings.source_keyword_weight
            + fuzzy_score * self.settings.source_fuzzy_weight
            + llm["score"] * self.settings.source_llm_weight
        )
        relevant = (
            bool(llm["relevant"])
            and lexical_ok
            and final >= self.settings.source_relevance_threshold
        )
        return {
            "article_id": str(article["id"]),
            "source_id": str(article["source_id"]),
            "keyword_score": round(keyword_score, 2),
            "matched_terms": matched_terms,
            "keyword_field_scores": field_keyword,
            "fuzzy_score": round(fuzzy_score, 2),
            "fuzzy_field_scores": field_fuzzy,
            "best_fuzzy_term": best_subdomain_term,
            "llm_score": llm["score"],
            "llm_relevant": llm["relevant"],
            "llm_reason": llm["reason"],
            "llm_primary_subdomain": llm.get("primary_subdomain") or "",
            "llm_evidence": llm.get("evidence") or [],
            "lexical_ok": lexical_ok,
            "final_relevance_score": round(final, 2),
            "final_relevance": relevant,
            "rejection_stage": None if relevant else "RELEVANCE_FILTER",
        }

    def _article_fields(self, article: dict[str, Any]) -> dict[str, str]:
        metadata = article.get("crawl_metadata") or {}
        headings = " ".join(str(item) for item in (metadata.get("headings") or []) if item)
        return {
            "title": str(article.get("title") or ""),
            "headings": headings,
            "description": str(article.get("description") or ""),
            "body": str(article.get("content") or "")[:8000],
        }

    def _term_variants(self, name: str, description: str = "") -> list[str]:
        variants: list[str] = []
        raw = (name or "").strip()
        if not raw:
            return []
        lowered = raw.lower()
        variants.append(lowered)
        variants.append(lowered.replace("-", " "))
        for acronym in re.findall(r"\(([^)]+)\)", raw):
            token = acronym.strip().lower()
            if token:
                variants.append(token)
        without_paren = re.sub(r"\([^)]*\)", " ", raw).strip().lower()
        if without_paren:
            variants.append(without_paren)
            variants.append(without_paren.replace("-", " "))
        for chunk in re.split(r"[.;|]", description or ""):
            phrase = " ".join(chunk.strip().lower().split()[:4])
            if len(phrase) >= 4:
                variants.append(phrase)
        cleaned: list[str] = []
        for item in variants:
            value = re.sub(r"\s+", " ", item).strip()
            if value and value not in cleaned:
                cleaned.append(value)
        return cleaned

    def _selected_name_ok(self, primary: str, subdomains: list[dict[str, Any]]) -> bool:
        names = [str(item.get("name") or "").strip() for item in subdomains if item.get("name")]
        if not primary.strip():
            return False
        lowered = primary.strip().lower()
        return any(lowered == name.lower() or lowered in name.lower() or name.lower() in lowered for name in names)

    def _enforce_llm_accuracy(self, llm: dict[str, Any], subdomains: list[dict[str, Any]]) -> dict[str, Any]:
        evidence = [str(item).strip() for item in (llm.get("evidence") or []) if str(item).strip()]
        primary = str(llm.get("primary_subdomain") or "").strip()
        if llm.get("relevant") and (not evidence or not self._selected_name_ok(primary, subdomains)):
            llm["relevant"] = False
            llm["score"] = min(float(llm.get("score") or 0), 45.0)
            llm["reason"] = f"{llm.get('reason') or ''} Rejected: relevance requires quoted evidence and a selected subdomain.".strip()
        llm["evidence"] = evidence[:4]
        llm["primary_subdomain"] = primary
        return llm

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]+", " ", (text or "").lower())).strip()

    def _token_coverage(self, field: str, term: str) -> float:
        haystack = self._normalize(field)
        needle = self._normalize(term)
        if not haystack or not needle:
            return 0.0
        if needle in haystack:
            return 1.0
        tokens = [token for token in needle.split() if token not in STOPWORDS]
        distinctive = [
            token for token in tokens
            if len(token) >= 3 or (len(token) == 2 and token.isalnum() and needle == token)
        ]
        if not distinctive:
            return 0.0
        haystack_tokens = set(haystack.split())
        hits = sum(1 for token in distinctive if token in haystack_tokens or token in haystack)
        return hits / len(distinctive)

    def _keyword_match(
        self,
        fields: dict[str, str],
        subdomain_terms: list[str],
        domain_terms: list[str],
    ) -> tuple[float, list[str], dict[str, float]]:
        matched: list[str] = []
        field_scores: dict[str, float] = {}
        for field, weight in FIELD_WEIGHTS.items():
            text = fields.get(field) or ""
            sub_score = max((self._token_coverage(text, term) for term in subdomain_terms), default=0.0)
            domain_score = max((self._token_coverage(text, term) for term in domain_terms), default=0.0)
            field_scores[field] = round(100.0 * (SUBDOMAIN_TERM_WEIGHT * sub_score + DOMAIN_TERM_WEIGHT * domain_score), 2)
        for term in subdomain_terms + domain_terms:
            if any(self._token_coverage(fields[field], term) >= 0.6 for field in FIELD_WEIGHTS):
                matched.append(term)
        score = sum(field_scores[field] * FIELD_WEIGHTS[field] for field in FIELD_WEIGHTS)
        return min(100.0, score), list(dict.fromkeys(matched)), field_scores

    def _chunks(self, text: str, size: int = 400) -> list[str]:
        value = text or ""
        if len(value) <= size:
            return [value] if value else []
        return [value[index:index + size] for index in range(0, min(len(value), 4000), size)]

    def _best_fuzzy(self, text: str, term: str) -> float:
        if not text or not term:
            return 0.0
        return max(
            float(fuzz.token_set_ratio(text, term)),
            float(fuzz.partial_ratio(text, term)),
            float(fuzz.WRatio(text, term)),
        )

    def _fuzzy_match(
        self,
        fields: dict[str, str],
        subdomain_terms: list[str],
        domain_terms: list[str],
    ) -> tuple[float, str, dict[str, float]]:
        field_scores: dict[str, float] = {}
        best_term = ""
        best_sub = 0.0
        for field in FIELD_WEIGHTS:
            text = fields.get(field) or ""
            if field == "body":
                sub = max(
                    (max((self._best_fuzzy(chunk, term) for chunk in self._chunks(text)), default=0.0) for term in subdomain_terms),
                    default=0.0,
                )
                dom = max(
                    (max((self._best_fuzzy(chunk, term) for chunk in self._chunks(text)), default=0.0) for term in domain_terms),
                    default=0.0,
                )
            else:
                sub = max((self._best_fuzzy(text, term) for term in subdomain_terms), default=0.0)
                dom = max((self._best_fuzzy(text, term) for term in domain_terms), default=0.0)
            field_scores[field] = round(SUBDOMAIN_TERM_WEIGHT * sub + DOMAIN_TERM_WEIGHT * dom, 2)
        for term in subdomain_terms:
            title_score = self._best_fuzzy(fields["title"], term)
            if title_score > best_sub:
                best_sub = title_score
                best_term = term
        score = sum(field_scores[field] * FIELD_WEIGHTS[field] for field in FIELD_WEIGHTS)
        return min(100.0, score), best_term, field_scores
