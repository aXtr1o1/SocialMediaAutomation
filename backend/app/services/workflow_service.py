from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse
import asyncio
import logging

from app.core.supabase import get_supabase_client
from app.services.source_matching_service import SourceMatchingService
from app.services.crawler_service import CrawlerService
from app.services.kpi_service import KPIService
from app.services.processing_service import ProcessingService
from app.services.domain_reputation_service import DomainReputationService
from app.services.redis_state_service import RedisStateService

log = logging.getLogger(__name__)

_RUNS: dict[str, dict[str, Any]] = {}
_TASKS: set[asyncio.Task] = set()
_RUN_TASKS: dict[str, asyncio.Task] = {}
_ACTIVITY_LIMIT = 8


def _site_label(source: dict[str, Any] | None) -> str:
    if not source:
        return "a mapped site"
    name = str(source.get("name") or "").strip()
    if name:
        return name
    host = urlparse(str(source.get("url") or "")).netloc.lower().removeprefix("www.")
    return host or "a mapped site"


def _title_preview(article: dict[str, Any] | None, limit: int = 52) -> str:
    title = str((article or {}).get("title") or "").strip()
    if not title:
        return "an article"
    if len(title) <= limit:
        return title
    return f"{title[: limit - 1].rstrip()}…"


def _run_snapshot(run_id: str) -> dict[str, Any] | None:
    row = _RUNS.get(run_id)
    if not row:
        return None
    progress = row.get("progress") or {}
    activity_log = progress.get("activity_log") or []
    if not isinstance(activity_log, list):
        activity_log = []
    return {
        "workflow_run_id": run_id,
        "job_status": row.get("job_status") or "RUNNING",
        "domain_name": row.get("domain_name") or "",
        "articles": row.get("articles") or [],
        "progress": {
            "stage": progress.get("stage") or "crawling",
            "message": progress.get("message") or "Starting...",
            "activity": progress.get("activity") or progress.get("message") or "Starting...",
            "current_site": progress.get("current_site") or "",
            "activity_log": [str(item) for item in activity_log[:_ACTIVITY_LIMIT]],
            "crawled": int(progress.get("crawled") or 0),
            "kpi_passed": int(progress.get("kpi_passed") or 0),
            "match_passed": int(progress.get("match_passed") or 0),
            "sources_done": int(progress.get("sources_done") or 0),
            "sources_total": int(progress.get("sources_total") or 0),
            "checked": int(progress.get("checked") or 0),
            "pages_seen": int(progress.get("pages_seen") or 0),
        },
    }


class WorkflowService:
    """Enforces: master data -> crawl all -> KPI -> relevance -> processing."""
    def __init__(self) -> None:
        self.db = get_supabase_client()
        self.redis = RedisStateService()
        self.matching = SourceMatchingService()
        self.crawler = CrawlerService()
        self.kpi = KPIService()
        self.processing = ProcessingService()
        self.reputation = DomainReputationService()
        self._status_cache: dict[str, str | None] = {}

    def begin(
        self,
        user_id: str | None = None,
        *,
        domain_id: str,
        subdomain_ids: list[str],
    ) -> dict[str, Any]:
        
        if user_id:
            existing_id = self.redis.get_active_workflow(
                str(user_id)
            )

            if existing_id:
                existing = self.get_run(
                    existing_id,
                    user_id,
                )

                if existing:
                    existing_status = str(
                        existing.get("job_status") or ""
                    )

                    if existing_status not in {
                        "COMPLETED",
                        "FAILED",
                        "PARTIAL",
                        "CANCELLED",
                    }:
                        # IMPORTANT:
                        # Do not create another workflow.
                        # Return the already-running workflow.
                        return existing

                    self.redis.clear_active_workflow(
                        str(user_id),
                        existing_id,
                    )
        domain, selected = self.matching.get_context_for_selection(domain_id, subdomain_ids)
        sources = self.matching.mapped_sources(selected)
        subdomain_names = {str(s["id"]): s.get("name") for s in selected}
        for source in sources:
            source["subdomain_names"] = [subdomain_names.get(str(sid), "") for sid in source.get("subdomain_ids", [])]

        queued_id = self._status("queued")
        running_id = self._status("running")

        run_row = self.db.table("workflow_runs").insert({"domain_id": domain["id"], "created_by": user_id,
            "status_id": queued_id, "total_sources": len(sources)}).execute().data or []
        workflow_run_id = str(run_row[0]["id"]) if run_row else None
        if workflow_run_id and user_id:
            self.redis.set_active_workflow(
                str(user_id),
                workflow_run_id,
            )
        if not workflow_run_id:
            raise RuntimeError("Could not start the sources run")
        self.db.table("workflow_runs").update({"status_id": running_id,
            "started_at": datetime.now(timezone.utc).isoformat()}).eq("id", workflow_run_id).execute()
        jobs: dict[str, str] = {}
        for source in sources:
            row = self.db.table("crawler_jobs").insert({"source_id": source["id"], "created_by": user_id,
                "workflow_run_id": workflow_run_id, "status_id": queued_id}).execute().data or []
            if row:
                jobs[str(source["id"])] = row[0]["id"]
        for job_id in jobs.values():
            self.db.table("crawler_jobs").update({"status_id": running_id,
                "started_at": datetime.now(timezone.utc).isoformat()}).eq("id", job_id).execute()

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
                "message": f"Opening {len(sources)} mapped sites...",
                "activity": f"Opening {len(sources)} mapped sites...",
                "current_site": "",
                "activity_log": [f"Opening {len(sources)} mapped sites..."],
                "crawled": 0,
                "kpi_passed": 0,
                "match_passed": 0,
                "sources_done": 0,
                "sources_total": len(sources),
                "checked": 0,
            },
        }
        
        snapshot = _run_snapshot(workflow_run_id) or {}

        if user_id:
            self.redis.update_session(
                str(user_id),
                active_workflow_id=workflow_run_id,
                current_workflow="content_generation",
                current_step="crawling",
                selected_source_posts=[],
                target_platforms=[],
                generation_status="CRAWLING",
            )

        self._persist_run(workflow_run_id)

        return snapshot

    def get_run(
        self,
        run_id: str,
        user_id: str | None,
    ) -> dict[str, Any] | None:
        row = _RUNS.get(run_id)

        if row:
            if (
                user_id
                and row.get("user_id")
                and str(row["user_id"]) != str(user_id)
            ):
                return None

            return _run_snapshot(run_id)

        if not user_id:
            return None

        # Redis workflow state is keyed by user_id.
        persisted = self.redis.get_workflow(str(user_id))

        if not persisted:
            return None

        if (
            persisted.get("user_id")
            and str(persisted["user_id"]) != str(user_id)
        ):
            return None

        # Make sure this is the requested workflow.
        persisted_run_id = str(
            persisted.get("workflow_run_id") or ""
        )

        if persisted_run_id != str(run_id):
            return None

        return persisted

    def cancel(self, run_id: str, user_id: str | None) -> dict[str, Any] | None:
        row = _RUNS.get(run_id)
        if not row:
            return None
        if user_id and row.get("user_id") and str(row["user_id"]) != str(user_id):
            return None

        status = str(row.get("job_status") or "")
        if status in {"COMPLETED", "FAILED", "PARTIAL", "CANCELLED"}:
            return _run_snapshot(run_id)

        row["cancel_requested"] = True
        self._push_activity(
            run_id,
            "Stopping search…",
            stage=str((row.get("progress") or {}).get("stage") or "crawling"),
            message="Stopping search…",
        )

        task = _RUN_TASKS.get(run_id)
        if task and not task.done():
            task.cancel()
        else:
            self._mark_cancelled(run_id, row)

        return _run_snapshot(run_id)

    def _mark_cancelled(self, run_id: str, row: dict[str, Any]) -> None:
        row["job_status"] = "CANCELLED"
        self._push_activity(
            run_id,
            "Search stopped",
            stage="completed",
            message="Search stopped",
            current_site="",
        )
        try:
            status_id = self._status("cancelled") or self._status("failed")
            self.db.table("workflow_runs").update(
                {
                    "status_id": status_id,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", run_id).execute()
        except Exception as exc:
            log.warning("workflow_cancel_persist_failed run_id=%s error=%s", run_id, exc)

    def is_cancel_requested(self, run_id: str) -> bool:
        row = _RUNS.get(run_id) or {}
        return bool(row.get("cancel_requested")) or str(row.get("job_status") or "") == "CANCELLED"

    def _set_progress(self, run_id: str, **values: Any) -> None:
        row = _RUNS.get(run_id)

        if not row:
            return

        progress = dict(row.get("progress") or {})
        progress.update(values)
        row["progress"] = progress

        self._persist_run(run_id)

    def _push_activity(
        self,
        run_id: str,
        line: str,
        **values: Any,
    ) -> None:
        row = _RUNS.get(run_id)

        if not row:
            return

        progress = dict(row.get("progress") or {})
        log_lines = list(
            progress.get("activity_log") or []
        )

        if not log_lines or log_lines[0] != line:
            log_lines = [
                line,
                *log_lines,
            ][:_ACTIVITY_LIMIT]

        progress.update(values)
        progress["activity"] = line

        if "message" not in values:
            progress["message"] = line

        progress["activity_log"] = log_lines
        row["progress"] = progress

        self._persist_run(run_id)
        
    def _persist_run(self, run_id: str) -> None:
        row = _RUNS.get(run_id)

        if not row:
            return

        user_id = row.get("user_id")

        # The current RedisStateService is user-keyed:
        # workflow:<user_id>
        if not user_id:
            return

        snapshot = _run_snapshot(run_id)

        if not snapshot:
            return

        self.redis.set_workflow(
            str(user_id),
            {
                **snapshot,
                "user_id": str(user_id),
                "domain_id": str(
                    (row.get("domain") or {}).get("id") or ""
                ),
                "subdomain_ids": [
                    str(item.get("id"))
                    for item in row.get("selected") or []
                    if item.get("id")
                ],
                "selected_sources": [
                    str(item.get("id"))
                    for item in row.get("sources") or []
                    if item.get("id")
                ],
            },
        )

    async def execute(self, run_id: str) -> None:
        row = _RUNS.get(run_id)
        if not row:
            return
        domain = row["domain"]
        selected = row["selected"]
        sources = row["sources"]
        jobs = row["jobs"]
        progress_lock = asyncio.Lock()
        try:
            self._push_activity(
                run_id,
                f"Opening {len(sources)} mapped sites…",
                stage="crawling",
                crawled=0,
                kpi_passed=0,
                match_passed=0,
                sources_done=0,
                sources_total=len(sources),
                checked=0,
                current_site="",
            )
            reputation_task = asyncio.create_task(self.reputation.check(sources))

            async def on_source_start(source: dict[str, Any]) -> None:
                if self.is_cancel_requested(run_id):
                    raise asyncio.CancelledError()
                host = _site_label(source)
                async with progress_lock:
                    self._push_activity(
                        run_id,
                        f"Scanning {host}…",
                        stage="crawling",
                        current_site=host,
                        sources_total=len(sources),
                    )

            async def on_article_found(source: dict[str, Any], article: dict[str, Any]) -> None:
                if self.is_cancel_requested(run_id):
                    raise asyncio.CancelledError()
                host = _site_label(source)
                title = _title_preview(article)
                async with progress_lock:
                    progress = dict((_RUNS.get(run_id) or {}).get("progress") or {})
                    crawled = int(progress.get("crawled") or 0) + 1
                    self._push_activity(
                        run_id,
                        f"Found “{title}” on {host}",
                        stage="crawling",
                        crawled=crawled,
                        current_site=host,
                        sources_total=len(sources),
                    )

            async def on_source_done(
                result: dict[str, Any],
                done_count: int,
                total: int,
                source: dict[str, Any] | None = None,
            ) -> None:
                if self.is_cancel_requested(run_id):
                    raise asyncio.CancelledError()
                articles = result.get("articles") or []
                host = _site_label(source) if source else "site"
                failed = result.get("status") == "FAILED" or result.get("crawl_status") == "FAILED"
                if failed:
                    line = f"Skipped {host} (blocked or unavailable)"
                elif articles:
                    line = f"Finished {host} · {len(articles)} articles"
                else:
                    line = f"Finished {host} · no articles"
                async with progress_lock:
                    progress = dict((_RUNS.get(run_id) or {}).get("progress") or {})
                    failed_so_far = int(progress.get("_failed_sources") or 0)
                    if failed:
                        failed_so_far += 1
                    self._push_activity(
                        run_id,
                        line,
                        stage="crawling",
                        sources_done=done_count,
                        sources_total=total,
                        current_site=host,
                        _failed_sources=failed_so_far,
                        message=f"Finding articles ({done_count}/{total} sites)…",
                    )

            async def on_page_seen(source: dict[str, Any], pages_seen: int, _articles_so_far: int) -> None:
                if self.is_cancel_requested(run_id):
                    raise asyncio.CancelledError()
                host = _site_label(source)
                async with progress_lock:
                    self._push_activity(
                        run_id,
                        f"Reading {host} · checked {pages_seen} pages",
                        stage="crawling",
                        current_site=host,
                        pages_seen=pages_seen,
                        sources_total=len(sources),
                        message=f"Still scanning {host}…",
                    )

            crawl_results = await self.crawler.crawl(
                sources,
                user_id=str(row.get("user_id") or ""),
                on_source_start=on_source_start,
                on_source_done=on_source_done,
                on_article_found=on_article_found,
                on_page_seen=on_page_seen,
                should_cancel=lambda: self.is_cancel_requested(run_id),
            )
            reputations = await reputation_task
            failed = [
                item
                for item in crawl_results
                if item.get("crawl_status", item.get("status")) == "FAILED" or item.get("status") == "FAILED"
            ]
            all_articles = [
                article
                for crawl in crawl_results
                for article in crawl.get("articles", [])
            ]
            self._push_activity(
                run_id,
                f"Reviewing {len(all_articles)} articles…" if all_articles else "No articles found yet…",
                stage="kpi",
                crawled=len(all_articles),
                sources_done=len(crawl_results),
                sources_total=len(sources),
                kpi_passed=0,
                match_passed=0,
                checked=0,
                current_site="",
            )

            source_by_id = {str(s["id"]): s for s in sources}
            kpi_passed, kpi_rejected, relevance_passed, relevance_rejected, processed = [], [], [], [], []
            checked = 0
            for crawl in crawl_results:
                source = source_by_id.get(str(crawl["source_id"]))
                if not source:
                    continue
                for article in crawl.get("articles", []):
                    checked += 1
                    kpi = self.kpi.validate(
                        article,
                        source,
                        domain,
                        reputations.get(str(source["id"]), {}),
                        all_articles,
                    )
                    if kpi["validation_status"] != "PASSED":
                        kpi_rejected.append(kpi)
                    else:
                        kpi_passed.append(kpi)
                    if checked == 1 or checked % 3 == 0 or checked == len(all_articles):
                        self._push_activity(
                            run_id,
                            f"Reviewing articles {checked}/{len(all_articles)}…",
                            stage="kpi",
                            crawled=len(all_articles),
                            kpi_passed=len(kpi_passed),
                            checked=checked,
                        )

            if kpi_passed:
                self._push_activity(
                    run_id,
                    f"Matching articles to your topics (0/{len(kpi_passed)})…",
                    stage="matching",
                    checked=len(all_articles),
                    crawled=len(all_articles),
                    kpi_passed=len(kpi_passed),
                    match_passed=0,
                    current_site="",
                )
            else:
                self._push_activity(
                    run_id,
                    "No articles to match yet",
                    stage="matching",
                    checked=len(all_articles),
                    crawled=len(all_articles),
                    kpi_passed=0,
                    match_passed=0,
                    current_site="",
                )

            for index, kpi in enumerate(kpi_passed, start=1):
                if self.is_cancel_requested(run_id):
                    raise asyncio.CancelledError()
                match = await self.matching.match_article(
                    article=kpi,
                    domain=domain,
                    subdomains=selected,
                )
                article_id = kpi.get("id") or kpi.get("article_id")
                if article_id:
                    self.db.table("source_validations").update(
                        {"matching_details": match}
                    ).eq("article_id", str(article_id)).execute()
                combined = {**kpi, "matching": match}
                if not match.get("final_relevance"):
                    relevance_rejected.append({**combined, "rejection_stage": "RELEVANCE_FILTER"})
                else:
                    relevance_passed.append(combined)
                    processed.append(self.processing.process(combined))
                title = _title_preview(kpi)
                self._push_activity(
                    run_id,
                    f"Matching “{title}” ({index}/{len(kpi_passed)})…",
                    stage="matching",
                    crawled=len(all_articles),
                    kpi_passed=len(kpi_passed),
                    match_passed=len(relevance_passed),
                    message=f"Matching articles to your topics ({index}/{len(kpi_passed)})…",
                )

            if kpi_rejected:
                avg = round(
                    sum(float(item.get("overall_kpi_score") or 0) for item in kpi_rejected)
                    / max(1, len(kpi_rejected)),
                    2,
                )
                log.warning(
                    "kpi_rejected_avg_score=%s sample_reasons=%s",
                    avg,
                    (kpi_rejected[0].get("kpi") or {}).get("reasons"),
                )
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
            status = (
                "FAILED"
                if crawl_results and len(failed) == len(crawl_results)
                else ("PARTIAL" if failed else "COMPLETED")
            )
            if not crawl_results:
                status = "COMPLETED"
            for crawl in crawl_results:
                job_id = jobs.get(str(crawl.get("source_id")))
                if job_id:
                    crawl_failed = crawl in failed
                    self.db.table("crawler_jobs").update(
                        {
                            "status_id": self._status("failed" if crawl_failed else "completed"),
                            "completed_at": datetime.now(timezone.utc).isoformat(),
                            "articles_found": len(crawl.get("articles", [])),
                            "error_message": crawl.get("error"),
                        }
                    ).eq("id", job_id).execute()
            self.db.table("workflow_runs").update(
                {
                    "status_id": self._status(status),
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "successful_sources": len(crawl_results) - len(failed),
                    "failed_sources": len(failed),
                }
            ).eq("id", run_id).execute()
            articles = self._to_source_articles(
                processed,
                selected,
            )

            row["articles"] = articles
            row["job_status"] = status
            self._push_activity(
                run_id,
                f"Done · {len(relevance_passed)} matched",
                stage="completed",
                crawled=len(all_articles),
                kpi_passed=len(kpi_passed),
                match_passed=len(relevance_passed),
                sources_done=len(crawl_results),
                sources_total=len(sources),
                current_site="",
            )
            if row.get("user_id"):
                self.redis.update_session(
                    str(row["user_id"]),
                    active_workflow_id=run_id,
                    current_workflow="content_generation",
                    current_step="select_content",
                    selected_source_posts=articles,
                    generation_status="READY",
                )

                if status in {
                    "COMPLETED",
                    "FAILED",
                    "PARTIAL",
                }:
                    self.redis.clear_active_workflow(
                        str(row["user_id"]),
                        run_id,
                    )
        except asyncio.CancelledError:
            log.warning("workflow_cancelled run_id=%s", run_id)
            self._mark_cancelled(run_id, row)
            raise
        except Exception as exc:
            log.warning(
                "workflow_execute_failed run_id=%s error=%s",
                run_id,
                exc,
                exc_info=True,
            )

            row["job_status"] = "FAILED"
            row["articles"] = []

            self._set_progress(
                run_id,
                stage="completed",
                message=str(exc)[:200],
            )

            self.db.table("workflow_runs").update(
                {
                    "status_id": self._status("FAILED"),
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", run_id).execute()

            if row.get("user_id"):
                self.redis.clear_active_workflow(
                    str(row["user_id"]),
                    run_id,
                )

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
        key = name.lower()
        if key in self._status_cache:
            return self._status_cache[key]
        response = self.db.table("statuses").select("id").eq("status_name", key).limit(1).execute()
        rows = (response.data if response is not None else None) or []
        status_id = rows[0]["id"] if rows else None
        self._status_cache[key] = status_id
        return status_id


def spawn_workflow(run_id: str) -> None:
    existing = _RUN_TASKS.get(run_id)
    if existing and not existing.done():
        return

    task = asyncio.create_task(WorkflowService().execute(run_id))
    _TASKS.add(task)
    _RUN_TASKS[run_id] = task

    def _cleanup(done: asyncio.Task) -> None:
        _TASKS.discard(done)
        if _RUN_TASKS.get(run_id) is done:
            _RUN_TASKS.pop(run_id, None)

    task.add_done_callback(_cleanup)
