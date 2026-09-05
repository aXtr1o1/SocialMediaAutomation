import asyncio
from unittest.mock import AsyncMock, Mock

import app.services.generation_service as module
from app.services.generation_service import GenerationService


def service():
    s = GenerationService.__new__(GenerationService)
    s.redis = Mock()
    return s


def test_create_job_persists_queued_job(monkeypatch):
    s = service()
    monkeypatch.setattr(module, "uuid4", lambda: "generation-1")

    result = s.create_job(user_id="u1", article_id="a1", platforms=["linkedin"])

    assert result == {
        "generation_id": "generation-1",
        "user_id": "u1",
        "article_id": "a1",
        "platforms": ["linkedin"],
        "status": "QUEUED",
        "posts": [],
        "drafts": [],
        "error": None,
    }
    s.redis.save_generation_job.assert_called_once_with("generation-1", result)


def test_run_job_completes_and_updates_workflow_session():
    async def run():
        s = service()
        s.redis.get_generation_job.side_effect = [
            {
                "generation_id": "g1",
                "user_id": "u1",
                "article_id": "a1",
                "platforms": ["linkedin"],
                "status": "QUEUED",
            },
            {
                "generation_id": "g1",
                "user_id": "u1",
                "article_id": "a1",
                "platforms": ["linkedin"],
                "status": "RUNNING",
            },
        ]
        s.redis.get_session.return_value = {"selected_source_posts": [{"id": "s1"}]}
        s.create = AsyncMock(
            return_value={
                "posts": [{"platform": "linkedin"}],
                "drafts": [{"id": "d1"}],
            }
        )

        await s.run_job("g1")

        s.redis.update_generation_job.assert_any_call("g1", status="RUNNING")
        s.redis.update_generation_job.assert_any_call(
            "g1",
            status="COMPLETED",
            posts=[{"platform": "linkedin"}],
            drafts=[{"id": "d1"}],
        )
        kwargs = s.redis.update_session.call_args.kwargs
        assert kwargs["current_step"] == "review"
        assert kwargs["generation_status"] == "COMPLETED"

    asyncio.run(run())


def test_run_job_marks_cancelled_on_task_cancellation():
    async def run():
        s = service()
        s.redis.get_generation_job.return_value = {
            "generation_id": "g1",
            "user_id": "u1",
            "article_id": "a1",
            "platforms": [],
            "status": "QUEUED",
        }
        s.create = AsyncMock(side_effect=asyncio.CancelledError())

        await s.run_job("g1")

        s.redis.update_generation_job.assert_any_call("g1", status="CANCELLED")
        s.redis.update_session.assert_called_with("u1", generation_status="CANCELLED")

    asyncio.run(run())


def test_run_job_marks_failed_on_exception():
    async def run():
        s = service()
        s.redis.get_generation_job.return_value = {
            "generation_id": "g1",
            "user_id": "u1",
            "article_id": "a1",
            "platforms": [],
            "status": "QUEUED",
        }
        s.create = AsyncMock(side_effect=RuntimeError("boom"))

        await s.run_job("g1")

        s.redis.update_generation_job.assert_any_call(
            "g1", status="FAILED", error="boom"
        )
        s.redis.update_session.assert_called_with("u1", generation_status="FAILED")

    asyncio.run(run())


def test_cancel_job_handles_missing_wrong_user_terminal_and_active(monkeypatch):
    s = service()

    s.redis.get_generation_job.return_value = None
    assert s.cancel_job("g1", "u1") is None

    s.redis.get_generation_job.return_value = {"user_id": "other", "status": "RUNNING"}
    assert s.cancel_job("g1", "u1") is None

    s.redis.get_generation_job.return_value = {"user_id": "u1", "status": "COMPLETED"}
    assert s.cancel_job("g1", "u1")["status"] == "COMPLETED"

    task = Mock()
    task.done.return_value = False
    monkeypatch.setitem(module._GENERATION_TASKS, "g1", task)

    before = {"user_id": "u1", "status": "RUNNING"}
    after = {"user_id": "u1", "status": "CANCELLED"}
    s.redis.get_generation_job.side_effect = [before, after]
    s.redis.update_generation_job.return_value = after

    result = s.cancel_job("g1", "u1")

    assert result["status"] == "CANCELLED"
    s.redis.update_generation_job.assert_called_once_with("g1", status="CANCELLED")
    task.cancel.assert_called_once()
    module._GENERATION_TASKS.pop("g1", None)
