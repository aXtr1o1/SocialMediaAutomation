from datetime import datetime, timezone
from typing import Any
import asyncio

from app.core.supabase import get_supabase_client
from app.services.source_matching_service import SourceMatchingService
from app.services.crawler_service import CrawlerService
from app.services.kpi_service import KPIService
from app.services.processing_service import ProcessingService
from app.services.domain_reputation_service import DomainReputationService


class WorkflowService:
    """Enforces: master data -> crawl all -> KPI -> relevance -> processing."""
    def __init__(self) -> None:
        self.db = get_supabase_client()
        self.matching = SourceMatchingService()
        self.crawler = CrawlerService()
        self.kpi = KPIService()
        self.processing = ProcessingService()
        self.reputation = DomainReputationService()

    async def run(self, user_id: str | None = None) -> dict[str, Any]:
        domain, all_subdomains = self.matching.get_fixed_context()
        selected = self.matching.select_subdomains(domain, all_subdomains)
        sources = self.matching.mapped_sources(selected)
        subdomain_names = {str(s["id"]): s.get("name") for s in selected}
        for source in sources:
            source["subdomain_names"] = [subdomain_names.get(str(sid), "") for sid in source.get("subdomain_ids", [])]

        run_row = self.db.table("workflow_runs").insert({"domain_id": domain["id"], "created_by": user_id,
            "status_id": self._status("queued"), "total_sources": len(sources)}).execute().data or []
        workflow_run_id = run_row[0]["id"] if run_row else None
        if workflow_run_id:
            self.db.table("workflow_runs").update({"status_id": self._status("running"),
                "started_at": datetime.now(timezone.utc).isoformat()}).eq("id", workflow_run_id).execute()
        jobs: dict[str, str] = {}
        for source in sources:
            row = self.db.table("crawler_jobs").insert({"source_id": source["id"], "created_by": user_id,
                "workflow_run_id": workflow_run_id, "status_id": self._status("queued")}).execute().data or []
            if row:
                jobs[str(source["id"])] = row[0]["id"]
        for job_id in jobs.values():
            self.db.table("crawler_jobs").update({"status_id": self._status("running"),
                "started_at": datetime.now(timezone.utc).isoformat()}).eq("id", job_id).execute()

        # Critical ordering rule: every mapped source is crawled before any matching.
        reputation_task = asyncio.create_task(self.reputation.check(sources))
        crawl_results = await self.crawler.crawl(sources, user_id)
        reputations = await reputation_task

        source_by_id = {str(s["id"]): s for s in sources}
        kpi_passed, kpi_rejected, relevance_passed, relevance_rejected, processed = [], [], [], [], []
        for crawl in crawl_results:
            source = source_by_id.get(str(crawl["source_id"]))
            if not source:
                continue
            articles = crawl.get("articles", [])
            for article in articles:
                kpi = self.kpi.validate(article, source, domain, reputations.get(str(source["domain_id"]), {}), articles)
                if kpi["validation_status"] != "PASSED":
                    kpi_rejected.append(kpi)
                    continue
                kpi_passed.append(kpi)
                match = await self.matching.match_article(article=article, domain=domain, subdomains=selected)
                self.db.table("source_validations").update({"matching_details": match}).eq("article_id", str(article["id"])).execute()
                combined = {**kpi, "matching": match}
                if not match["final_relevance"]:
                    relevance_rejected.append({**combined, "rejection_stage": "RELEVANCE_FILTER"})
                    continue
                relevance_passed.append(combined)
                processed.append(self.processing.process(combined))

        failed = [x for x in crawl_results if x.get("crawl_status", x.get("status")) == "FAILED" or x.get("status") == "FAILED"]
        status = "FAILED" if crawl_results and len(failed) == len(crawl_results) else ("PARTIAL" if failed else "COMPLETED")
        for crawl in crawl_results:
            job_id = jobs.get(str(crawl.get("source_id")))
            if job_id:
                crawl_failed = crawl in failed
                self.db.table("crawler_jobs").update({"status_id": self._status("failed" if crawl_failed else "completed"),
                    "completed_at": datetime.now(timezone.utc).isoformat(), "articles_found": len(crawl.get("articles", [])),
                    "error_message": crawl.get("error")}).eq("id", job_id).execute()
        if workflow_run_id:
            self.db.table("workflow_runs").update({"status_id": self._status(status),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "successful_sources": len(crawl_results) - len(failed), "failed_sources": len(failed)}).eq("id", workflow_run_id).execute()
        return {"domain": domain, "selected_relevant_subdomains": selected,
                "sources": sources, "crawl_results": crawl_results,
                "domain_reputation": reputations, "kpi_passed": kpi_passed,
                "kpi_rejected": kpi_rejected, "relevance_passed": relevance_passed,
                "relevance_rejected": relevance_rejected, "processed_content": processed,
                "workflow_run_id": workflow_run_id, "job_status": status}

    def _status(self, name: str) -> str | None:
        response = self.db.table("statuses").select("id").eq("status_name", name.lower()).limit(1).execute()
        rows = (response.data if response is not None else None) or []
        return rows[0]["id"] if rows else None
