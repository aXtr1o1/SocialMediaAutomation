from datetime import datetime, timezone
from typing import Any
import asyncio
import logging

from app.core.supabase import get_supabase_client
from app.services.source_matching_service import SourceMatchingService
from app.services.crawler_service import CrawlerService
from app.services.kpi_service import KPIService
from app.services.processing_service import ProcessingService
from app.services.domain_reputation_service import DomainReputationService

log = logging.getLogger(__name__)

_RUNS: dict[str, dict[str, Any]] = {}
_TASKS: set[asyncio.Task] = set()


def _run_snapshot(run_id: str) -> dict[str, Any] | None:
    row = _RUNS.get(run_id)
    if not row:
        return None
    progress = row.get("progress") or {}
    return {
        "workflow_run_id": run_id,
        "job_status": row.get("job_status") or "RUNNING",
        "domain_name": row.get("domain_name") or "",
        "articles": row.get("articles") or [],
        "progress": {
            "stage": progress.get("stage") or "crawling",
            "message": progress.get("message") or "Starting...",
            "crawled": int(progress.get("crawled") or 0),
            "kpi_passed": int(progress.get("kpi_passed") or 0),
            "match_passed": int(progress.get("match_passed") or 0),
            "sources_done": int(progress.get("sources_done") or 0),
            "sources_total": int(progress.get("sources_total") or 0),
        },
    }


class WorkflowService:
    """Enforces: master data -> crawl all -> KPI -> relevance -> processing."""
    def __init__(self) -> None:
        self.db = get_supabase_client()
        self.matching = SourceMatchingService()
        self.crawler = CrawlerService()
        self.kpi = KPIService()
        self.processing = ProcessingService()
        self.reputation = DomainReputationService()

    def begin(
        self,
        user_id: str | None = None,
        *,
        domain_id: str,
        subdomain_ids: list[str],
    ) -> dict[str, Any]:
        domain, selected = self.matching.get_context_for_selection(domain_id, subdomain_ids)
        sources = self.matching.mapped_sources(selected)
        subdomain_names = {str(s["id"]): s.get("name") for s in selected}
        for source in sources:
            source["subdomain_names"] = [subdomain_names.get(str(sid), "") for sid in source.get("subdomain_ids", [])]

        run_row = self.db.table("workflow_runs").insert({"domain_id": domain["id"], "created_by": user_id,
            "status_id": self._status("queued"), "total_sources": len(sources)}).execute().data or []
        workflow_run_id = str(run_row[0]["id"]) if run_row else None
        if not workflow_run_id:
            raise RuntimeError("Could not start the sources run")
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

        scope = ", ".join(str(item.get("name") or "") for item in selected if item.get("name"))
        _RUNS[workflow_run_id] = {
            "user_id": user_id,
            "domain": domain,
            "selected": selected,
            "sources": sources,
            "jobs": jobs,
            "job_status": "RUNNING",
            "domain_name": domain.get("name") or "",
            "articles": [],
            "progress": {
                "stage": "crawling",
                "message": f"Crawling sites for {scope or 'your selection'}...",
                "crawled": 0,
                "kpi_passed": 0,
                "match_passed": 0,
                "sources_done": 0,
                "sources_total": len(sources),
            },
        }
        return _run_snapshot(workflow_run_id) or {}

    def get_run(self, run_id: str, user_id: str | None) -> dict[str, Any] | None:
        row = _RUNS.get(run_id)
        if not row:
            return None
        if user_id and row.get("user_id") and str(row["user_id"]) != str(user_id):
            return None
        return _run_snapshot(run_id)

    def _set_progress(self, run_id: str, **values: Any) -> None:
        row = _RUNS.get(run_id)
        if not row:
            return
        progress = dict(row.get("progress") or {})
        progress.update(values)
        row["progress"] = progress

    async def execute(self, run_id: str) -> None:
        row = _RUNS.get(run_id)
        if not row:
            return
        domain = row["domain"]
        selected = row["selected"]
        sources = row["sources"]
        jobs = row["jobs"]
        try:
            self._set_progress(run_id, stage="crawling", message="Crawling mapped sites...")
            reputation_task = asyncio.create_task(self.reputation.check(sources))
            crawl_results = await self.crawler.crawl(sources)
            reputations = await reputation_task
            failed = [x for x in crawl_results if x.get("crawl_status", x.get("status")) == "FAILED" or x.get("status") == "FAILED"]
            all_articles = [article for crawl in crawl_results for article in crawl.get("articles", [])]
            self._set_progress(
                run_id,
                stage="kpi",
                message="Checking article quality...",
                crawled=len(all_articles),
                sources_done=len(crawl_results) - len(failed),
                sources_total=len(sources),
            )

            source_by_id = {str(s["id"]): s for s in sources}
            kpi_passed, kpi_rejected, relevance_passed, relevance_rejected, processed = [], [], [], [], []
            for crawl in crawl_results:
                source = source_by_id.get(str(crawl["source_id"]))
                if not source:
                    continue
                articles = crawl.get("articles", [])
                for article in articles:
                    kpi = self.kpi.validate(article, source, domain, reputations.get(str(source["id"]), {}), all_articles)
                    if kpi["validation_status"] != "PASSED":
                        kpi_rejected.append(kpi)
                        continue
                    kpi_passed.append(kpi)
                    self._set_progress(
                        run_id,
                        stage="matching",
                        message="Matching articles to your subdomains...",
                        crawled=len(all_articles),
                        kpi_passed=len(kpi_passed),
                    )
                    match = await self.matching.match_article(article=article, domain=domain, subdomains=selected)
                    self.db.table("source_validations").update({"matching_details": match}).eq("article_id", str(article["id"])).execute()
                    combined = {**kpi, "matching": match}
                    if not match["final_relevance"]:
                        relevance_rejected.append({**combined, "rejection_stage": "RELEVANCE_FILTER"})
                        continue
                    relevance_passed.append(combined)
                    processed.append(self.processing.process(combined))
                    self._set_progress(run_id, match_passed=len(relevance_passed), kpi_passed=len(kpi_passed))

            if kpi_rejected:
                avg = round(sum(float(item.get("overall_kpi_score") or 0) for item in kpi_rejected) / max(1, len(kpi_rejected)), 2)
                log.warning("kpi_rejected_avg_score=%s sample_reasons=%s", avg, (kpi_rejected[0].get("kpi") or {}).get("reasons"))
            log.warning(
                "workflow_filter crawled=%s kpi_passed=%s kpi_rejected=%s match_passed=%s match_rejected=%s shown=%s sources_failed=%s",
                len(all_articles),
                len(kpi_passed),
                len(kpi_rejected),
                len(relevance_passed),
                len(relevance_rejected),
                len(processed),
                len(failed),
            )
            status = "FAILED" if crawl_results and len(failed) == len(crawl_results) else ("PARTIAL" if failed else "COMPLETED")
            if not crawl_results:
                status = "COMPLETED"
            for crawl in crawl_results:
                job_id = jobs.get(str(crawl.get("source_id")))
                if job_id:
                    crawl_failed = crawl in failed
                    self.db.table("crawler_jobs").update({"status_id": self._status("failed" if crawl_failed else "completed"),
                        "completed_at": datetime.now(timezone.utc).isoformat(), "articles_found": len(crawl.get("articles", [])),
                        "error_message": crawl.get("error")}).eq("id", job_id).execute()
            self.db.table("workflow_runs").update({"status_id": self._status(status),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "successful_sources": len(crawl_results) - len(failed), "failed_sources": len(failed)}).eq("id", run_id).execute()
            articles = self._to_source_articles(processed, selected)
            row["articles"] = articles
            row["job_status"] = status
            self._set_progress(
                run_id,
                stage="completed",
                message="Done",
                crawled=len(all_articles),
                kpi_passed=len(kpi_passed),
                match_passed=len(relevance_passed),
            )
        except Exception as exc:
            log.warning("workflow_execute_failed run_id=%s error=%s", run_id, exc, exc_info=True)
            row["job_status"] = "FAILED"
            row["articles"] = []
            self._set_progress(run_id, stage="completed", message=str(exc)[:200])
            self.db.table("workflow_runs").update({"status_id": self._status("FAILED"),
                "completed_at": datetime.now(timezone.utc).isoformat()}).eq("id", run_id).execute()

    def _to_source_articles(
        self,
        processed: list[dict[str, Any]],
        selected: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        names = {str(item["id"]): item.get("name") or "" for item in selected}
        articles = []
        for row in processed:
            meta = row.get("metadata") or {}
            subdomain_name = next(
                (
                    names[str(sub_id)]
                    for sub_id in meta.get("subdomain_ids") or []
                    if names.get(str(sub_id))
                ),
                None,
            )
            published = meta.get("publish_date")
            if hasattr(published, "isoformat"):
                published = published.isoformat()
            elif published is not None:
                published = str(published)

            articles.append({
                "id": str(row.get("id") or row.get("article_id")),
                "article_id": str(row.get("article_id") or ""),
                "title": meta.get("title") or "Untitled",
                "author": meta.get("author") or None,
                "published_at": published,
                "subdomain_name": subdomain_name,
                "content": row.get("cleaned_text") or row.get("ai_ready_content") or "",
                "source_url": meta.get("source_url") or None,
            })
        return articles

    def _status(self, name: str) -> str | None:
        response = self.db.table("statuses").select("id").eq("status_name", name.lower()).limit(1).execute()
        rows = (response.data if response is not None else None) or []
        return rows[0]["id"] if rows else None


def spawn_workflow(run_id: str) -> None:
    task = asyncio.create_task(WorkflowService().execute(run_id))
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)
