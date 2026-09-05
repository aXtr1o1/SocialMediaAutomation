from unittest.mock import Mock

from app.services.redis_state_service import RedisStateService


def service():
    obj = RedisStateService.__new__(RedisStateService)
    obj.redis = Mock()
    obj.workflow_ttl = 100
    return obj


def test_key_builders():
    s = service()
    assert s.workflow_key("r1") == "workflow:r1"
    assert s.selection_workflow_key("u1", "d1", ["s2", "s1"]) == "workflow:selection:u1:d1|s1|s2"
    assert s.workflow_lock_key("u1") == "workflow:lock:u1"


def test_set_and_get_json():
    s = service()
    s._set_json("k", {"a": 1}, 50)
    s.redis.setex.assert_called_once_with("k", 50, '{"a": 1}')
    s.redis.get.return_value = '{"a": 1}'
    assert s._get_json("k") == {"a": 1}


def test_set_json_without_ttl_uses_set():
    s = service()
    s._set_json("k", {"a": 1})
    s.redis.set.assert_called_once_with("k", '{"a": 1}')


def test_get_json_handles_invalid_values():
    s = service()
    s.redis.get.return_value = "not-json"
    assert s._get_json("k") is None
    s.redis.get.return_value = "[]"
    assert s._get_json("k") == []


def test_workflow_set_get_update_and_clear():
    s = service()
    s.set_workflow("u1", {"status": "RUNNING"})
    args = s.redis.setex.call_args.args
    assert args[0] == "workflow:u1"
    assert '"status": "RUNNING"' in args[2]
    assert args[1] == 100

    s.redis.get.return_value = '{"status":"RUNNING"}'
    assert s.get_workflow("u1") == {"status": "RUNNING"}

    s.update_workflow("u1", {"current_step": "review"})
    s.redis.setex.assert_called()
    updated_payload = s.redis.setex.call_args.args[2]
    assert '"status": "RUNNING"' in updated_payload
    assert '"current_step": "review"' in updated_payload

    s.clear_workflow("u1")
    s.redis.delete.assert_called_with("workflow:u1")


def test_active_workflow_set_get_and_conditional_clear():
    s = service()
    s.get_workflow = Mock(return_value={"workflow_run_id": "r2"})
    assert s.get_active_workflow("u1") == "r2"

    s.update_workflow = Mock()
    s.set_active_workflow("u1", "r1")
    s.update_workflow.assert_called_with("u1", {"workflow_run_id": "r1"})

    s.get_active_workflow = Mock(return_value="r2")
    s.clear_active_workflow("u1", "r1")
    s.update_workflow.assert_called_once_with("u1", {"workflow_run_id": "r1"})

    s.get_active_workflow.return_value = "r1"
    s.clear_active_workflow("u1", "r1")
    assert s.update_workflow.call_args_list[-1] == (("u1", {"workflow_run_id": None}), {})


def test_selection_workflow_set_get_and_clear():
    s = service()
    s.set_selection_workflow("u1", "d1", ["s2", "s1"], "r1")
    key = "workflow:selection:u1:d1|s1|s2"
    payload = s.redis.setex.call_args.args[2]
    assert key == s.redis.setex.call_args.args[0]
    assert '"workflow_run_id": "r1"' in payload

    s.redis.get.return_value = '{"workflow_run_id":"r1"}'
    assert s.get_selection_workflow("u1", "d1", ["s1", "s2"]) == "r1"
    s.clear_selection_workflow("u1", "d1", ["s1", "s2"])
    s.redis.delete.assert_called_with(key)


def test_session_defaults_update_and_clear():
    s = service()
    s.get_workflow = Mock(return_value=None)
    session = s.get_session("u1")
    assert session["user_id"] == "u1"
    assert session["generation_status"] == "IDLE"
    assert session["active_generation_id"] is None

    s.update_session("u1", current_step="review", ignored=None)
    s.set_workflow.assert_not_called() if hasattr(s, "set_workflow") and isinstance(s.set_workflow, Mock) else None
    assert s.redis.setex.called

    s.clear_session("u1")
    s.redis.delete.assert_called_with("workflow:u1")


def test_active_generation_set_get_and_clear():
    s = service()
    s.get_workflow = Mock(return_value={"active_generation_id": "g1"})
    assert s.get_active_generation_id("u1") == "g1"

    s.update_workflow = Mock()
    s.set_active_generation_id("u1", "g2")
    s.update_workflow.assert_called_with("u1", {"active_generation_id": "g2"})

    s.clear_active_generation_id("u1")
    s.update_workflow.assert_called_with("u1", {"active_generation_id": None})


def test_workflow_lock_acquire_and_release():
    s = service()
    s.redis.set.return_value = True
    assert s.acquire_workflow_lock("u1", ttl_seconds=30) is True
    s.redis.set.assert_called_with("workflow:lock:u1", "1", nx=True, ex=30)

    s.release_workflow_lock("u1")
    s.redis.delete.assert_called_with("workflow:lock:u1")
