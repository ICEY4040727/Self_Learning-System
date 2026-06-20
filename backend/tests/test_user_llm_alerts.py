"""Tests for User LLM patrol Feishu alerts."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.core.config import get_settings
from backend.services.user_llm_alerts import (
    feishu_bot_sign,
    notify_patrol_result,
    send_feishu_text,
    should_notify_patrol,
)
from backend.services.user_llm_repair import UserLLMPatrolResult, UserLLMRepairError
from backend.services.user_llm_db_audit import UserLLMInconsistency


def test_feishu_bot_sign_matches_official_algorithm():
    import base64
    import hashlib
    import hmac

    timestamp = "1597368523"
    secret = "test-secret"
    expected = base64.b64encode(
        hmac.new(f"{timestamp}\n{secret}".encode("utf-8"), digestmod=hashlib.sha256).digest()
    ).decode("utf-8")
    assert feishu_bot_sign(timestamp=timestamp, secret=secret) == expected


def test_should_notify_patrol_only_when_needed():
    clean = UserLLMPatrolResult([], [], 0, [], False)
    assert should_notify_patrol(clean, exit_code=0) is False

    dirty = UserLLMPatrolResult(
        pre_issues=[
            UserLLMInconsistency(
                user_id=1,
                username="u",
                field="model",
                legacy_value="a",
                json_value="b",
                message="m",
            )
        ],
        post_issues=[],
        repaired_user_count=1,
        repair_errors=[],
        applied_repair=True,
    )
    assert should_notify_patrol(dirty, exit_code=0) is True


@patch("backend.services.user_llm_alerts.httpx.post")
def test_send_feishu_text_includes_signature(mock_post, monkeypatch):
    monkeypatch.setenv("USER_LLM_PATROL_ALERT_WEBHOOK", "https://example.test/hook")
    monkeypatch.setenv("USER_LLM_PATROL_SECRET", "secret-value")
    get_settings.cache_clear()

    mock_response = MagicMock()
    mock_response.json.return_value = {"code": 0}
    mock_post.return_value = mock_response

    assert send_feishu_text(text="hello") is True
    payload = mock_post.call_args.kwargs["json"]
    assert payload["msg_type"] == "text"
    assert payload["content"]["text"] == "hello"
    assert "timestamp" in payload
    assert "sign" in payload

    get_settings.cache_clear()


@patch("backend.services.user_llm_alerts.send_feishu_text", return_value=True)
def test_notify_patrol_result_on_remaining_issues(mock_send):
    result = UserLLMPatrolResult(
        pre_issues=[
            UserLLMInconsistency(
                user_id=1,
                username="u",
                field="model",
                legacy_value="a",
                json_value="b",
                message="m",
            )
        ],
        post_issues=[
            UserLLMInconsistency(
                user_id=1,
                username="u",
                field="model",
                legacy_value="a",
                json_value="b",
                message="m",
            )
        ],
        repaired_user_count=0,
        repair_errors=[],
        applied_repair=False,
    )

    assert notify_patrol_result(
        result,
        exit_code=1,
        dry_run=True,
        applied_repair=False,
    )
    text = mock_send.call_args.kwargs["text"]
    assert "残留不一致: 1" in text
    assert "退出码: 1" in text


@patch("backend.services.user_llm_alerts.send_feishu_text", return_value=True)
def test_notify_patrol_result_reports_repair_errors(mock_send):
    result = UserLLMPatrolResult(
        pre_issues=[],
        post_issues=[],
        repaired_user_count=0,
        repair_errors=[UserLLMRepairError(user_id=9, username="bad", error="boom")],
        applied_repair=True,
    )

    notify_patrol_result(
        result,
        exit_code=1,
        dry_run=False,
        applied_repair=True,
    )
    text = mock_send.call_args.kwargs["text"]
    assert "修复失败: 1" in text
    assert "user_id=9" in text
