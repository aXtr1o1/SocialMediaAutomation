from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

import app.core.security as security
import app.routers.auth as auth


def test_authenticated_user_does_not_use_token_cache(monkeypatch):
    response = SimpleNamespace(user=SimpleNamespace(id="u1", email="a@example.com"))
    supabase = Mock()
    supabase.auth.get_user.return_value = response
    monkeypatch.setattr(security, "get_supabase_auth_client", lambda: supabase)
    monkeypatch.setattr(security.AuthService, "ensure_profile", Mock())

    first = security.get_authenticated_supabase_user("token")
    second = security.get_authenticated_supabase_user("token")

    assert first is response.user
    assert second is response.user
    assert supabase.auth.get_user.call_count == 2


def _auth_user():
    return SimpleNamespace(id="user-1", email="user@example.com")


def _change_request(**overrides):
    values = dict(
        current_password="old-password",
        new_password="new-password",
        confirm_password="new-password",
        sign_out_all_devices=False,
    )
    values.update(overrides)
    return auth.ChangePasswordRequest(**values)


def test_change_password_rejects_mismatched_confirmation():
    with pytest.raises(HTTPException) as exc:
        auth.change_password(
            _change_request(confirm_password="different-password"),
            access_token="token",
            auth_user=_auth_user(),
        )
    assert exc.value.status_code == 400


def test_change_password_success_without_global_signout(monkeypatch):
    supabase = Mock()
    supabase.auth.sign_in_with_password.return_value = SimpleNamespace(user=object())
    admin = Mock()
    monkeypatch.setattr(auth, "get_supabase_auth_client", lambda: supabase)
    monkeypatch.setattr(auth, "get_supabase_client", lambda: SimpleNamespace(auth=SimpleNamespace(admin=admin)))

    result = auth.change_password(
        _change_request(),
        access_token="token",
        auth_user=_auth_user(),
    )

    assert result["signed_out_all_devices"] is False
    assert result["message"] == "Password updated."
    admin.update_user_by_id.assert_called_once()
    supabase.auth.admin.sign_out.assert_not_called()


def test_change_password_success_with_global_signout(monkeypatch):
    supabase = Mock()
    supabase.auth.sign_in_with_password.return_value = SimpleNamespace(user=object())
    admin = Mock()
    monkeypatch.setattr(auth, "get_supabase_auth_client", lambda: supabase)
    monkeypatch.setattr(auth, "get_supabase_client", lambda: SimpleNamespace(auth=SimpleNamespace(admin=admin)))

    result = auth.change_password(
        _change_request(sign_out_all_devices=True),
        access_token="token",
        auth_user=_auth_user(),
    )

    assert result["signed_out_all_devices"] is True
    assert "All other devices were signed out" in result["message"]
    supabase.auth.admin.sign_out.assert_called_once_with("token", scope="global")


def test_change_password_reports_signout_failure_after_password_change(monkeypatch):
    supabase = Mock()
    supabase.auth.sign_in_with_password.return_value = SimpleNamespace(user=object())
    supabase.auth.admin.sign_out.side_effect = RuntimeError("redis unavailable")
    admin = Mock()
    monkeypatch.setattr(auth, "get_supabase_auth_client", lambda: supabase)
    monkeypatch.setattr(auth, "get_supabase_client", lambda: SimpleNamespace(auth=SimpleNamespace(admin=admin)))

    with pytest.raises(HTTPException) as exc:
        auth.change_password(
            _change_request(sign_out_all_devices=True),
            access_token="token",
            auth_user=_auth_user(),
        )

    assert exc.value.status_code == 502
