from unittest.mock import Mock

import app.services.workflow_service as module
from app.services.workflow_service import WorkflowService


def service():
    s = WorkflowService.__new__(WorkflowService)
    s.redis = Mock()
    return s


def test_get_run_falls_back_to_redis_and_enforces_owner(monkeypatch):
    s = service()
    monkeypatch.setattr(module, "_RUNS", {})
    s.redis.get_workflow.return_value = {
        "workflow_run_id": "r1",
        "user_id": "u1",
        "job_status": "RUNNING",
    }

    assert s.get_run("r1", "u1")["workflow_run_id"] == "r1"
    assert s.get_run("r1", "u2") is None


def test_get_run_uses_memory_snapshot_and_checks_owner(monkeypatch):
    s = service()
    monkeypatch.setitem(module._RUNS, "r1", {"user_id": "u1", "job_status": "RUNNING"})
    monkeypatch.setattr(
        module,
        "_run_snapshot",
        lambda run_id: {"workflow_run_id": run_id, "job_status": "RUNNING"},
    )

    assert s.get_run("r1", "u1")["workflow_run_id"] == "r1"
    assert s.get_run("r1", "u2") is None
    module._RUNS.pop("r1", None)


def test_set_progress_persists_snapshot(monkeypatch):
    s = service()
    monkeypatch.setitem(
        module._RUNS,
        "r1",
        {"user_id": "u1", "progress": {"stage": "crawl"}},
    )
    monkeypatch.setattr(
        module,
        "_run_snapshot",
        lambda run_id: {"workflow_run_id": run_id, "progress": {"stage": "crawl", "checked": 3}},
    )

    s._set_progress("r1", checked=3)

    assert module._RUNS["r1"]["progress"]["checked"] == 3
    s.redis.set_workflow.assert_called_once()
    args = s.redis.set_workflow.call_args.args
    assert args[0] == "u1"
    assert args[1]["workflow_run_id"] == "r1"
    module._RUNS.pop("r1", None)


def test_push_activity_deduplicates_and_persists(monkeypatch):
    s = service()
    monkeypatch.setitem(
        module._RUNS,
        "r1",
        {"user_id": "u1", "progress": {"activity_log": ["old"]}},
    )
    monkeypatch.setattr(module, "_run_snapshot", lambda run_id: {"workflow_run_id": run_id})

    s._push_activity("r1", "new", checked=2)
    progress = module._RUNS["r1"]["progress"]
    assert progress["activity"] == "new"
    assert progress["message"] == "new"
    assert progress["activity_log"] == ["new", "old"]
    s.redis.set_workflow.assert_called_once()
    module._RUNS.pop("r1", None)


def test_persist_run_writes_snapshot_and_source_ids(monkeypatch):
    s = service()
    row = {
        "user_id": "u1",
        "domain": {"id": "d1"},
        "selected": [{"id": "sub1"}],
        "sources": [{"id": "src1"}],
    }
    monkeypatch.setitem(module._RUNS, "r1", row)
    monkeypatch.setattr(
        module,
        "_run_snapshot",
        lambda run_id: {"workflow_run_id": run_id, "job_status": "RUNNING"},
    )

    s._persist_run("r1")

    s.redis.set_workflow.assert_called_once_with(
        "u1",
        {
            "workflow_run_id": "r1",
            "job_status": "RUNNING",
            "user_id": "u1",
            "domain_id": "d1",
            "subdomain_ids": ["sub1"],
            "selected_sources": ["src1"],
        },
    )
    module._RUNS.pop("r1", None)
