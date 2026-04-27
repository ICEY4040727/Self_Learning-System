"""Gamification Engine - 观察者模式成就检测引擎

检测成就条件，记录解锁。不调 LLM，零 API 成本。
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.models.models import RELATIONSHIP_STAGE_LABELS

logger = logging.getLogger(__name__)

# [2E-02] 复用 models 中的阶段定义，避免重复
_STAGE_ORDER = list(RELATIONSHIP_STAGE_LABELS.keys())


class GamificationEngine:
    """成就检测引擎 - 基于规则的成就解锁"""

    def check_achievements(
        self,
        db: Session,
        *,
        user_id: int,
        character_id: int,
        world_id: int,
        stats: dict[str, Any] | None = None,
        dimension_scores: dict[str, float] | None = None,
        current_stage: str | None = None,
        recent_facts: list | None = None,
    ) -> list[dict]:
        """检查所有未解锁的成就定义，返回新解锁的成就列表。

        Args:
            stats: 学习统计 {"total_sessions": N, "concepts_mastered": N, ...}
            dimension_scores: 画像维度 {"abstract_thinking": 0.6, ...}
            current_stage: 当前关系阶段
            recent_facts: 最近创建的 MemoryFact 列表
        """
        from backend.models.models import AchievementDef, Achievement

        stats = stats or {}
        dimension_scores = dimension_scores or {}
        recent_facts = recent_facts or []

        # 获取所有启用的成就定义
        all_defs = db.query(AchievementDef).filter(
            AchievementDef.enabled == True,
        ).all()

        if not all_defs:
            return []

        # 获取已解锁的 key 集合
        unlocked = db.query(Achievement.achievement_key).filter(
            Achievement.user_id == user_id,
            Achievement.character_id == character_id,
        ).all()
        unlocked_keys = {r[0] for r in unlocked}

        new_unlocks = []

        for adef in all_defs:
            if adef.key in unlocked_keys:
                continue

            # [TODO-N6] Schema drift between model (JSON) and migration
            # (TEXT seeds) — see narrative_engine for the full note.
            params = {}
            if adef.condition_params:
                raw = adef.condition_params
                if isinstance(raw, str):
                    params = json.loads(raw)
                elif isinstance(raw, dict):
                    params = raw

            triggered, ctx = self._check_condition(
                adef.condition_type, params,
                stats=stats,
                dimension_scores=dimension_scores,
                current_stage=current_stage,
                recent_facts=recent_facts,
            )

            if not triggered:
                continue

            # [TODO-N2] Wrap each INSERT in a SAVEPOINT so a UniqueConstraint
            # collision (race with a concurrent unlock) only rolls back this
            # one INSERT, not the entire process_message transaction. The
            # previous `db.rollback()` recovery destroyed mastery updates,
            # narrative writeback rows, and the ChatMessage saved earlier in
            # the same call.
            record = Achievement(
                user_id=user_id,
                character_id=character_id,
                achievement_key=adef.key,
                unlocked_at=datetime.now(UTC),
                context=ctx,
            )
            try:
                with db.begin_nested():
                    db.add(record)
            except Exception:
                # Either UniqueConstraint (already unlocked by concurrent
                # request) or some FK error — skip this achievement and move
                # on. The outer transaction is intact thanks to SAVEPOINT.
                logger.info(
                    "Achievement %s skipped on insert (likely already unlocked)",
                    adef.key,
                )
                continue

            new_unlocks.append({
                "key": adef.key,
                "display_name": adef.display_name,
                "description": adef.description,
                "rarity": adef.rarity,
                "icon": adef.icon,
                "category": adef.category,
                "context": ctx,
            })

        return new_unlocks

    def _check_condition(
        self,
        condition_type: str,
        params: dict,
        *,
        stats: dict[str, Any],
        dimension_scores: dict[str, float],
        current_stage: str | None,
        recent_facts: list,
    ) -> tuple[bool, dict | None]:
        """检查单个条件。返回 (triggered, context)。"""

        if condition_type == "stat_threshold":
            stat_key = params.get("stat", "")
            threshold = params.get("threshold", 1)
            value = stats.get(stat_key, 0)
            if value >= threshold:
                return True, {"stat": stat_key, "value": value, "threshold": threshold}

        elif condition_type == "dimension_crossing":
            dim = params.get("dimension", "")
            threshold = params.get("threshold", 0.5)
            score = dimension_scores.get(dim)
            if score is not None and score >= threshold:
                return True, {"dimension": dim, "value": score, "threshold": threshold}

        elif condition_type == "relationship_stage":
            target_stage = params.get("stage", "")
            stage_order = _STAGE_ORDER  # [2E-02] 复用全局定义
            if current_stage and current_stage in stage_order:
                idx = stage_order.index(current_stage)
                target_idx = stage_order.index(target_stage) if target_stage in stage_order else 0
                if idx >= target_idx:
                    return True, {"stage": current_stage}

        elif condition_type == "fact_transition":
            from_type = params.get("from", "")
            to_type = params.get("to", "")
            # Check if recent facts include the target type
            matching = [f for f in recent_facts if f.fact_type == to_type]
            if matching:
                return True, {"concept": (matching[-1].concept_tags or [""])[0]}

        elif condition_type == "fact_count_threshold":
            fact_type = params.get("fact_type", "")
            count = params.get("count", 1)
            matching = [f for f in recent_facts if f.fact_type == fact_type]
            if len(matching) >= count:
                return True, {"count": len(matching)}

        else:
            # [TODO-N4] An achievement def with an unknown condition_type
            # silently never unlocks. Surface for operator awareness.
            logger.warning(
                "GamificationEngine: unknown condition_type %r — achievement will never unlock",
                condition_type,
            )

        return False, None

    def get_achievements_status(
        self, db: Session, *, user_id: int, character_id: int,
    ) -> dict:
        """获取用户的成就状态概览。"""
        from backend.models.models import AchievementDef, Achievement

        unlocked = db.query(Achievement).filter(
            Achievement.user_id == user_id,
            Achievement.character_id == character_id,
        ).all()

        # [TODO-N7] O(N+M) lookup: build dict once, hit O(1) per def.
        # Old code did `next(a for a in unlocked if a.achievement_key == ...)`
        # inside the loop → O(N×M).
        unlocked_by_key = {a.achievement_key: a for a in unlocked}
        unlocked_keys = set(unlocked_by_key)
        all_defs = db.query(AchievementDef).filter(AchievementDef.enabled == True).all()

        unlocked_list = []
        locked_visible = []
        for adef in all_defs:
            if adef.key in unlocked_keys:
                ach = unlocked_by_key[adef.key]
                unlocked_list.append({
                    "key": adef.key,
                    "display_name": adef.display_name,
                    "rarity": adef.rarity,
                    "icon": adef.icon,
                    "category": adef.category,
                    "unlocked_at": ach.unlocked_at.isoformat() if ach.unlocked_at else None,
                })
            elif not adef.hidden:
                locked_visible.append({
                    "key": adef.key,
                    "display_name": adef.display_name,
                    "description": adef.description,
                    "category": adef.category,
                    "rarity": adef.rarity,
                })

        return {
            "unlocked": unlocked_list,
            "locked_visible": locked_visible,
            "total_unlocked": len(unlocked_list),
            "total_available": len(all_defs),
        }


# Global instance
gamification_engine = GamificationEngine()