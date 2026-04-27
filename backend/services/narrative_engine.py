"""Narrative Engine - 观察者模式叙事触发引擎

观察 MemoryFact 和 Relationship 变化，触发叙事事件。
不调 LLM，零 API 成本。
"""

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class _SafeDict(dict):
    """[TODO-N9] str.format_map source — missing keys leave the
    placeholder literal `{key}` in place instead of raising KeyError."""
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _safe_format(template: str, vars: dict) -> str:
    """One-pass placeholder substitution — no recursive expansion of values."""
    safe = _SafeDict({k: str(v) for k, v in vars.items()})
    try:
        return template.format_map(safe)
    except (ValueError, IndexError):
        # Malformed template (e.g. unmatched brace) — return as-is.
        return template


class NarrativeEngine:
    """叙事引擎 - 基于规则的叙事事件触发器"""

    # 内存冷却存储 {(user_id, character_id, trigger_type): last_trigger_time}
    # [R1-02] Acceptable: 内存级冷却记录，服务器重启后丢失。
    # 若未来需要持久化，可迁移至 DB 表或 Redis。
    _cooldowns: dict[tuple[int, int, str], datetime] = {}

    def check_triggers(
        self,
        db: Session,
        *,
        user_id: int,
        character_id: int,
        world_id: int,
        recent_facts: list | None = None,
        current_stage: str | None = None,
        prev_stage: str | None = None,
        context_vars: dict[str, Any] | None = None,
    ) -> list[dict]:
        """检查所有启用的叙事触发规则，返回触发的事件列表。

        Args:
            recent_facts: 最近创建的 MemoryFact 列表
            current_stage: 当前关系阶段
            prev_stage: 之前的关系阶段（用于检测变化）
            context_vars: 模板变量（如 {"concept": "递归"}）
        """
        from backend.models.models import NarrativeTriggerRule, MemoryFact

        rules = db.query(NarrativeTriggerRule).filter(
            NarrativeTriggerRule.enabled == True,
        ).all()

        if not rules:
            return []

        events = []
        now = datetime.now(UTC)
        context_vars = context_vars or {}

        for rule in rules:
            # 1. 检查冷却
            cooldown_key = (user_id, character_id, rule.trigger_type)
            last_time = self._cooldowns.get(cooldown_key)
            if last_time and (now - last_time) < timedelta(minutes=rule.cooldown_minutes):
                continue

            # 2. 检查条件
            triggered, extra_vars = self._check_condition(
                rule, db, character_id=character_id, world_id=world_id,
                recent_facts=recent_facts or [],
                current_stage=current_stage,
                prev_stage=prev_stage,
            )

            if not triggered:
                continue

            # 3. 更新冷却
            self._cooldowns[cooldown_key] = now

            # 4. 生成事件
            # [TODO-N9] format_map with a SafeDict so:
            #   - template literals like "the {bracket} thing" don't crash
            #     when the key isn't in vars (KeyError → leaves placeholder)
            #   - vals containing "{x}" no longer recursively trigger
            #     replacement against subsequent keys
            merged_vars = {**context_vars, **extra_vars}
            event_text = _safe_format(rule.event_template or "", merged_vars)

            event = {
                "type": rule.trigger_type,
                "text": event_text,
                "ui_template": rule.ui_template,
                "priority": rule.priority,
            }

            # 5. 写回记忆（观察者约束：fact_type 必须是 event）
            # [TODO-N5] Route through memory_manager.write_facts so dedup
            # (24h same-type/same-tags merge), t_valid timestamping, and any
            # future ChromaDB sync apply. Direct db.add bypassed all of that
            # — every cooldown-reset triggered a duplicate row.
            if rule.writeback_memory:
                try:
                    from backend.services.memory_manager import memory_manager

                    content = f"叙事事件: {event_text}"
                    tags = merged_vars.get("concept_tags", [rule.trigger_type])
                    if isinstance(tags, str):
                        tags = [tags]
                    memory_manager.write_facts(
                        db, character_id, world_id,
                        [{
                            "fact_type": "event",
                            "content": content,
                            "concept_tags": tags,
                            "salience": 0.6,
                        }],
                    )
                except Exception as e:
                    logger.warning(f"NarrativeEngine writeback failed: {e}")

            events.append(event)

        # 按 priority 排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        events.sort(key=lambda e: priority_order.get(e["priority"], 1))

        return events

    def _check_condition(
        self,
        rule,
        db: Session,
        *,
        character_id: int,
        world_id: int,
        recent_facts: list,
        current_stage: str | None,
        prev_stage: str | None,
    ) -> tuple[bool, dict]:
        """检查单条规则的条件。返回 (triggered, extra_template_vars)。"""
        from backend.models.models import MemoryFact

        # [TODO-N6] Both branches are real, not defensive padding:
        # - The model declares condition_params as JSON column → tests
        #   (create_all from model) and Postgres production return dict.
        # - The migration 2026_04_25_add_narrative_and_achievements.py
        #   creates the column as TEXT and seeds JSON-stringified rows →
        #   SQLite production returns str.
        # Schema drift to fix later; for now both forms must be parsed.
        params = {}
        if rule.condition_params:
            raw = rule.condition_params
            if isinstance(raw, str):
                params = json.loads(raw)
            elif isinstance(raw, dict):
                params = raw

        extra_vars: dict = {}

        if rule.condition_type == "fact_created":
            fact_type = params.get("fact_type")
            matching = [f for f in recent_facts if f.fact_type == fact_type]
            if matching:
                # Extract concept from the most recent matching fact
                tags = matching[-1].concept_tags or []
                if tags:
                    extra_vars["concept"] = tags[0]
                return True, extra_vars

        elif rule.condition_type == "fact_count_threshold":
            fact_type = params.get("fact_type", "concept_struggle")
            count_threshold = params.get("count", 3)
            window_minutes = params.get("window_minutes", 60)

            since = datetime.now(UTC) - timedelta(minutes=window_minutes)
            # [TODO-N3] world_id filter prevents cross-world leakage —
            # struggles in world A must not trigger narrative events in B.
            # Match observe_recent semantics: NULL world_id (cross-world
            # facts) also count.
            matching = db.query(MemoryFact).filter(
                MemoryFact.character_id == character_id,
                (MemoryFact.world_id == world_id)
                | (MemoryFact.world_id.is_(None)),
                MemoryFact.fact_type == fact_type,
                MemoryFact.created_at >= since,
            ).all()

            if len(matching) >= count_threshold:
                tags = matching[-1].concept_tags or []
                if tags:
                    extra_vars["concept"] = tags[0]
                extra_vars["concept_tags"] = tags
                return True, extra_vars

        elif rule.condition_type == "relationship_stage_change":
            if current_stage and prev_stage and current_stage != prev_stage:
                extra_vars["old_stage"] = prev_stage
                extra_vars["new_stage"] = current_stage
                return True, extra_vars

        elif rule.condition_type == "time_gap":
            # Checked by caller providing last_session_time in context
            pass  # Handled externally via context_vars

        else:
            # [TODO-N4] Surface dead-rule footgun: an admin can author a
            # rule with a condition_type the engine doesn't recognise and
            # it silently never fires. Log so operators notice.
            logger.warning(
                "NarrativeEngine: unknown condition_type %r on rule %r — silently skipping",
                rule.condition_type, rule.trigger_type,
            )

        return False, extra_vars


# Global instance
narrative_engine = NarrativeEngine()