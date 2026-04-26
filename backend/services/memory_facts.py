"""Memory Facts Service
记忆事实表 (MemoryFact) 操作服务

用于存储和检索 AI 从对话中提取的关于学生的认知事实。
"""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.models.models import Character, LearnerProfile, MemoryFact

logger = logging.getLogger(__name__)


class MemoryFactsService:
    """MemoryFact 表操作服务"""

    # Seed memory fact_type 枚举
    FACT_TYPE_STUDENT_STATE = "student_state"
    FACT_TYPE_CONCEPT_STRUGGLE = "concept_struggle"
    FACT_TYPE_CONCEPT_MASTERED = "concept_mastered"
    FACT_TYPE_PREFERENCE = "preference"
    FACT_TYPE_EVENT = "event"
    FACT_TYPE_COMMITMENT = "commitment"

    def write_memory_facts(
        self,
        db: Session,
        character_id: int,
        world_id: int | None,
        memories: list[dict[str, Any]],
        source_message_id: int | None = None,
    ) -> list[int]:
        """
        写入记忆事实

        Args:
            db: 数据库会话
            character_id: sage character ID（AI 老师）
            world_id: 世界 ID（可为 None 表示跨世界事实）
            memories: 记忆列表，每条包含 fact_type, content, concept_tags, salience, expires_at
            source_message_id: 溯源，指向 AI 回复的 ChatMessage.id

        Returns:
            新写入的记忆 ID 列表
        """
        now = datetime.now(UTC)
        memory_ids = []

        for mem in memories:
            fact_type = mem.get("fact_type", self.FACT_TYPE_EVENT)
            content = mem.get("content", "")[:500]  # 截断至 500 字

            if not content:
                continue

            fact = MemoryFact(
                character_id=character_id,
                world_id=world_id,
                fact_type=fact_type,
                content=content,
                concept_tags=mem.get("concept_tags", []),
                source_message_id=source_message_id,
                salience=mem.get("salience", 0.5),
                created_at=now,
                last_recalled_at=now,
                recall_count=0,
                expires_at=mem.get("expires_at"),
                # [2A-02] 记忆创建时设置生效时间
                t_valid=mem.get("t_valid", now),
            )
            db.add(fact)
            db.flush()
            memory_ids.append(fact.id)

        return memory_ids

    def retrieve_memories(
        self,
        db: Session,
        character_id: int,
        world_id: int | None = None,
        query: str | None = None,
        fact_types: list[str] | None = None,
        limit: int = 10,
        min_salience: float = 0.3,
    ) -> list[MemoryFact]:
        """
        检索记忆事实

        Args:
            db: 数据库会话
            character_id: sage character ID
            world_id: 世界 ID（可选，为 None 时跨世界检索）
            query: 搜索关键词（模糊匹配 content）
            fact_types: 事实类型过滤列表
            limit: 返回数量上限
            min_salience: 最低重要度阈值

        Returns:
            MemoryFact 对象列表
        """
        q = db.query(MemoryFact).filter(
            MemoryFact.character_id == character_id,
            MemoryFact.salience >= min_salience,
            # 未过期或无过期时间
            (MemoryFact.expires_at.is_(None) | (MemoryFact.expires_at > datetime.now(UTC)))
        )

        if world_id is not None:
            # 包含指定世界的事实 + 跨世界事实（world_id=NULL）
            q = q.filter(
                (MemoryFact.world_id == world_id) | (MemoryFact.world_id.is_(None))
            )

        if fact_types:
            q = q.filter(MemoryFact.fact_type.in_(fact_types))

        # [2F-01] 当 query 不为空时同时匹配 content ILIKE 和 concept_tags JSON
        if query:
            # [2A-05] 转义 ILIKE 通配符，防止非预期匹配
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            q = q.filter(
                MemoryFact.content.ilike(f"%{escaped}%", escape="\\")
                | MemoryFact.concept_tags.contains(f'"{query}"')
            )

        # 按 salience 降序 + created_at 降序排序
        memories = q.order_by(
            MemoryFact.salience.desc(),
            MemoryFact.created_at.desc()
        ).limit(limit).all()

        # [2A-04] 更新召回追踪：对每条返回的记忆递增 recall_count 并刷新 last_recalled_at
        now = datetime.now(UTC)
        for mem in memories:
            mem.recall_count = (mem.recall_count or 0) + 1
            mem.last_recalled_at = now
        db.flush()

        return memories

    def evolve_salience(self, db: Session, character_id: int | None = None) -> int:
        """
        [2A-01] 对记忆执行 salience 衰减。

        规则：
        - 基础衰减：salience -= salience_base_decay * days_since_last_recall
        - 召回增强：salience += salience_recall_factor * (rc / (rc + 10))
        - 类型修正：salience *= salience_type_multiplier[fact_type]
        - 保底保护：recall_count > 5 的记忆 salience 不低于 0.3
        - 下限：salience 永不低于 0.1

        Returns:
            更新的记忆数量
        """
        settings = get_settings()
        cfg = settings.learning_system
        base_decay = cfg["memory"]["salience_base_decay"]
        recall_factor = cfg["memory"]["salience_recall_factor"]
        type_multiplier = cfg.get("salience_type_multiplier", {})

        now = datetime.now(UTC)
        q = db.query(MemoryFact).filter(
            MemoryFact.salience > 0.1,  # 跳过已达下限的记忆
        )
        if character_id is not None:
            q = q.filter(MemoryFact.character_id == character_id)

        facts = q.all()
        updated = 0

        for fact in facts:
            # 自上次召回以来的天数（至少 1 天以产生衰减）
            last = fact.last_recalled_at or fact.created_at or now
            if last.tzinfo is None:
                last = last.replace(tzinfo=UTC)
            days = max((now - last).total_seconds() / 86400, 1.0)

            # 基础衰减
            new_salience = fact.salience - base_decay * days

            # 召回增强：被频繁召回的记忆衰减更慢
            rc = fact.recall_count or 0
            if rc > 0:
                boost = recall_factor * (rc / (rc + 10))
                new_salience += boost

            # 类型修正
            multiplier = type_multiplier.get(fact.fact_type, 1.0)
            new_salience *= multiplier

            # 保底保护：recall_count > 5 的记忆不低于 0.3
            if rc > 5:
                new_salience = max(new_salience, 0.3)

            # 下限
            new_salience = max(new_salience, 0.1)

            if abs(new_salience - fact.salience) > 0.001:
                fact.salience = round(new_salience, 4)
                updated += 1

        db.flush()
        logger.info("evolve_salience: scanned %d facts, updated %d", len(facts), updated)
        return updated

    def delete_expired_memories(self, db: Session) -> int:
        """删除过期记忆，返回删除数量"""
        deleted = db.query(MemoryFact).filter(
            MemoryFact.expires_at.isnot(None),
            MemoryFact.expires_at < datetime.now(UTC)
        ).delete()
        db.flush()
        return deleted

    def create_seed_memories(
        self,
        db: Session,
        sage_character_id: int,
        traveler_character: Character,
        learner_profile: LearnerProfile | None = None,
    ) -> list[int]:
        """
        创建 Seed Memory Facts

        从 traveler character 和 learner_profile 提取初始认知事实。

        Seed 内容（来自草案）:
        - 学生名字 (salience=0.9)
        - 学习方向 tags (salience=0.7)
        - 学习背景 background (salience=0.6)
        - 性格特点 personality (salience=0.5)
        - 已有学习经历 total_sessions (salience=0.8)
        - 平均掌握度 average_mastery (salience=0.85)
        - 学习偏好 preference_stability (salience=0.75)
        - 元认知趋势 metacognition_trend (salience=0.6)
        """
        memory_ids = []

        # 学生名字
        if traveler_character.name:
            memory_ids.extend(self.write_memory_facts(
                db=db,
                character_id=sage_character_id,
                world_id=None,  # 跨世界事实
                memories=[{
                    "fact_type": self.FACT_TYPE_STUDENT_STATE,
                    "content": f"学生名叫 {traveler_character.name}",
                    "salience": 0.9,
                }],
            ))

        # 学习方向 tags
        if traveler_character.tags:
            tags_str = ", ".join(traveler_character.tags) if isinstance(traveler_character.tags, list) else str(traveler_character.tags)
            memory_ids.extend(self.write_memory_facts(
                db=db,
                character_id=sage_character_id,
                world_id=None,
                memories=[{
                    "fact_type": self.FACT_TYPE_PREFERENCE,
                    "content": f"学习方向: {tags_str}",
                    "salience": 0.7,
                }],
            ))

        # 学习背景
        if traveler_character.background:
            memory_ids.extend(self.write_memory_facts(
                db=db,
                character_id=sage_character_id,
                world_id=None,
                memories=[{
                    "fact_type": self.FACT_TYPE_STUDENT_STATE,
                    "content": f"学生背景: {traveler_character.background}",
                    "salience": 0.6,
                }],
            ))

        # 性格特点
        if traveler_character.personality:
            memory_ids.extend(self.write_memory_facts(
                db=db,
                character_id=sage_character_id,
                world_id=None,
                memories=[{
                    "fact_type": self.FACT_TYPE_PREFERENCE,
                    "content": f"性格特点: {traveler_character.personality}",
                    "salience": 0.5,
                }],
            ))

        # 从 learner_profile 提取学习统计
        if learner_profile and learner_profile.profile:
            profile = learner_profile.profile

            # 已有学习经历
            learning_stats = profile.get("learning_stats", {})
            total_sessions = learning_stats.get("total_sessions", 0)
            if total_sessions > 0:
                memory_ids.extend(self.write_memory_facts(
                    db=db,
                    character_id=sage_character_id,
                    world_id=None,
                    memories=[{
                        "fact_type": self.FACT_TYPE_STUDENT_STATE,
                        "content": f"已有 {total_sessions} 次学习经历",
                        "salience": 0.8,
                    }],
                ))

            # 平均掌握度
            avg_mastery = learning_stats.get("average_mastery", 0)
            if avg_mastery > 0:
                mastery_percent = int(avg_mastery * 100)
                memory_ids.extend(self.write_memory_facts(
                    db=db,
                    character_id=sage_character_id,
                    world_id=None,
                    memories=[{
                        "fact_type": self.FACT_TYPE_CONCEPT_MASTERED,
                        "content": f"平均掌握度 {mastery_percent}%",
                        "salience": 0.85,
                    }],
                ))

            # 学习偏好
            pref_stability = profile.get("preference_stability", {})
            for pref_key, display_name in [
                ("visual_examples", "视觉化学习"),
                ("analogy_based", "类比学习"),
                ("step_by_step", "步骤化学习"),
            ]:
                if pref_stability.get(pref_key):
                    memory_ids.extend(self.write_memory_facts(
                        db=db,
                        character_id=sage_character_id,
                        world_id=None,
                        memories=[{
                            "fact_type": self.FACT_TYPE_PREFERENCE,
                            "content": f"偏好{display_name}",
                            "salience": 0.75,
                        }],
                    ))

            # 元认知趋势
            metacognition = profile.get("metacognition_trend", {})
            for dim, label in [
                ("planning", "规划"),
                ("monitoring", "监控"),
                ("regulating", "调节"),
                ("reflecting", "反思"),
            ]:
                if dim in metacognition:
                    trend_data = metacognition[dim]
                    current = trend_data.get("current", "unknown")
                    trend = trend_data.get("trend", "unknown")
                    memory_ids.extend(self.write_memory_facts(
                        db=db,
                        character_id=sage_character_id,
                        world_id=None,
                        memories=[{
                            "fact_type": self.FACT_TYPE_STUDENT_STATE,
                            "content": f"元认知-{label}能力: {current}({trend})",
                            "salience": 0.6,
                        }],
                    ))

        return memory_ids


# 全局实例
memory_facts_service = MemoryFactsService()
