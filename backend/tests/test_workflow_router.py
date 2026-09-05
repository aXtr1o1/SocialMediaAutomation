from types import SimpleNamespace
from unittest.mock import Mock

import app.routers.workflow as router


def test_get_workflow_session(monkeypatch):
    service = Mock()
    service.get_session.return_value = {"user_id": "u1"}
    monkeypatch.setattr(router, "RedisStateService", lambda: service)
    assert router.get_workflow_session(SimpleNamespace(id="u1")) == {"user_id": "u1"}
    service.get_session.assert_called_once_with("u1")


def test_update_workflow_session(monkeypatch):
    service = Mock()
    service.update_session.return_value = {"current_step": "review"}
    monkeypatch.setattr(router, "RedisStateService", lambda: service)
    payload = {"current_step": "review", "generation_status": "READY"}
    result = router.update_workflow_session(payload, SimpleNamespace(id="u1"))
    assert result["current_step"] == "review"
    service.update_session.assert_called_once_with("u1", **payload)


def test_update_workflow_step(monkeypatch):
    service = Mock()
    service.update_session.return_value = {"current_step": "generate"}
    monkeypatch.setattr(router, "RedisStateService", lambda: service)
    router.update_workflow_step({"current_step": "generate"}, SimpleNamespace(id="u1"))
    service.update_session.assert_called_once_with("u1", current_step="generate", current_workflow=None)


def test_clear_workflow_session(monkeypatch):
    service = Mock()
    monkeypatch.setattr(router, "RedisStateService", lambda: service)
    assert router.clear_workflow_session(SimpleNamespace(id="u1")) == {"message": "Workflow session cleared"}
    service.clear_session.assert_called_once_with("u1")
