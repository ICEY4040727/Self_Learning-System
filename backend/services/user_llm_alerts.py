"""Outbound alerts for User LLM consistency patrol."""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import httpx

from backend.core.config import get_settings
from backend.services.user_llm_telemetry import MARKER_AUDIT

if TYPE_CHECKING:
    from backend.services.user_llm_repair import UserLLMPatrolResult

logger = logging.getLogger("user_llm.alerts")

FEISHU_WEBHOOK_TIMEOUT_SECONDS = 10.0


def feishu_bot_sign(*, timestamp: str, secret: str) -> str:
    """Sign payload for Feishu custom bot webhook (timestamp + newline + secret)."""
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def _alert_configured() -> tuple[str, str | None]:
    settings = get_settings()
    webhook = (settings.user_llm_patrol_alert_webhook or "").strip()
    secret = (settings.user_llm_patrol_secret or "").strip() or None
    return webhook, secret


def send_feishu_text(*, text: str) -> bool:
    """Post a text message to the configured Feishu bot webhook."""
    webhook, secret = _alert_configured()
    if not webhook:
        logger.info("[%s] event=alert_skipped reason=webhook_not_configured", MARKER_AUDIT)
        return False

    payload: dict[str, object] = {
        "msg_type": "text",
        "content": {"text": text},
    }
    if secret:
        timestamp = str(int(time.time()))
        payload["timestamp"] = timestamp
        payload["sign"] = feishu_bot_sign(timestamp=timestamp, secret=secret)

    try:
        response = httpx.post(
            webhook,
            json=payload,
            timeout=FEISHU_WEBHOOK_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        body = response.json()
        if body.get("code") not in (0, None):
            logger.error(
                "[%s] event=alert_failed provider=feishu code=%s msg=%s",
                MARKER_AUDIT,
                body.get("code"),
                body.get("msg"),
            )
            return False
    except Exception as exc:
        logger.error(
            "[%s] event=alert_failed provider=feishu error=%s",
            MARKER_AUDIT,
            exc,
        )
        return False

    logger.info("[%s] event=alert_sent provider=feishu", MARKER_AUDIT)
    return True


def format_patrol_alert_text(
    result: UserLLMPatrolResult,
    *,
    exit_code: int,
    dry_run: bool,
    applied_repair: bool,
) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    if exit_code != 0:
        status = "失败"
    elif result.pre_issues and applied_repair and not result.post_issues:
        status = "已自愈"
    elif result.pre_issues or result.post_issues:
        status = "需关注"
    else:
        status = "正常"

    lines = [
        "【User LLM 一致性巡检】",
        f"时间: {now}",
        f"状态: {status}",
        f"模式: {'dry-run' if dry_run else ('repair' if applied_repair else 'scan')}",
        f"预检不一致: {len(result.pre_issues)}",
        f"修复成功用户: {result.repaired_user_count}",
        f"修复失败: {len(result.repair_errors)}",
        f"残留不一致: {len(result.post_issues)}",
        f"退出码: {exit_code}",
    ]

    if result.repair_errors:
        lines.append("—— 修复失败明细 ——")
        for err in result.repair_errors[:5]:
            lines.append(f"- user_id={err.user_id} username={err.username}: {err.error}")
        if len(result.repair_errors) > 5:
            lines.append(f"- ... 另有 {len(result.repair_errors) - 5} 条")

    if result.post_issues:
        lines.append("—— 残留不一致样例 ——")
        for issue in result.post_issues[:5]:
            lines.append(
                f"- user_id={issue.user_id} field={issue.field}: {issue.message}"
            )
        if len(result.post_issues) > 5:
            lines.append(f"- ... 另有 {len(result.post_issues) - 5} 条")

    return "\n".join(lines)


def should_notify_patrol(
    result: UserLLMPatrolResult,
    *,
    exit_code: int,
) -> bool:
    return bool(
        exit_code != 0
        or result.pre_issues
        or result.post_issues
        or result.repair_errors
    )


def notify_patrol_result(
    result: UserLLMPatrolResult,
    *,
    exit_code: int,
    dry_run: bool,
    applied_repair: bool,
) -> bool:
    if not should_notify_patrol(result, exit_code=exit_code):
        return False
    text = format_patrol_alert_text(
        result,
        exit_code=exit_code,
        dry_run=dry_run,
        applied_repair=applied_repair,
    )
    return send_feishu_text(text=text)


def notify_patrol_exception(*, error: str) -> bool:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    text = "\n".join(
        [
            "【User LLM 一致性巡检】",
            f"时间: {now}",
            "状态: 失败",
            "原因: 脚本异常退出",
            f"错误: {error}",
        ]
    )
    return send_feishu_text(text=text)


def notify_patrol_process_failure(*, exit_code: int) -> bool:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    text = "\n".join(
        [
            "【User LLM 一致性巡检】",
            f"时间: {now}",
            "状态: 失败",
            "原因: 调度子进程非零退出",
            f"退出码: {exit_code}",
        ]
    )
    return send_feishu_text(text=text)
