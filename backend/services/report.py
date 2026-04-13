"""
Report Service - 学习报告数据聚合服务

提供跨世界和单世界的学习报告数据聚合功能。
"""

from typing import Any

from sqlalchemy.orm import Session

from backend.models.models import (
    Character,
    Course,
    MemoryFact,
    RelationshipStageRecord,
    World,
)
from backend.models.models import (
    Session as SessionModel,
)

# =============================================================================
# 知识掌握度趋势
# =============================================================================

def get_mastery_trends_by_user(db: Session, user_id: int) -> dict[str, Any]:
    """
    获取用户跨世界的知识掌握度趋势。

    返回格式：
    {
        "trends": [
            {
                "concept_name": "递归",
                "mastery_level": 0.72,
                "last_updated": "2026-04-05T16:30:00Z",
                "world_id": 1,
                "world_name": "雅典学院"
            }
        ],
        "average_mastery": 0.65,
        "improved_count": 12,
        "declined_count": 3
    }
    """
    # 获取用户所有世界
    worlds = db.query(World).filter(World.user_id == user_id).all()

    trends = []
    total_mastery = 0.0
    concept_count = 0
    improved_count = 0
    declined_count = 0

    for world in worlds:
        # 获取该世界的记忆事实 (P1 #183: 使用 MemoryFact 替代 Knowledge)
        memory_facts = db.query(MemoryFact).filter(MemoryFact.world_id == world.id).all()

        if not memory_facts:
            continue

        # 从 memory_facts 提取概念掌握情况
        concepts = {}
        for fact in memory_facts:
            if fact.fact_type == "concept_mastered":
                tags = fact.concept_tags or []
                for tag in tags:
                    concepts[tag] = {"name": tag, "mastery": int(fact.salience * 100)}

        for concept_id, concept_data in concepts.items():
            if not isinstance(concept_data, dict):
                continue

            mastery = concept_data.get("mastery", 0)
            t_valid = concept_data.get("t_valid")

            trends.append({
                "concept_name": concept_data.get("name", concept_id),
                "mastery_level": mastery,
                "last_updated": t_valid or world.created_at.isoformat() if world.created_at else None,
                "world_id": world.id,
                "world_name": world.name
            })

            total_mastery += mastery
            concept_count += 1

            # 判断是否提升（基于 t_valid 排序，理论上后来的 mastery 应该更高）
            # 这里简化处理，实际应该比较历史值

    average_mastery = total_mastery / concept_count if concept_count > 0 else 0

    return {
        "trends": trends,
        "average_mastery": round(average_mastery, 2),
        "improved_count": improved_count,
        "declined_count": declined_count
    }


def get_world_mastery_trends(db: Session, world_id: int, user_id: int) -> list[dict[str, Any]]:
    """
    获取单个世界的知识掌握度趋势（按时间排序）。

    返回格式：
    [
        {"date": "2026-04-01", "average_mastery": 0.3, "concepts_learned": 5},
        {"date": "2026-04-02", "average_mastery": 0.35, "concepts_learned": 8},
    ]
    """
    # 获取该世界的记忆事实 (P1 #183: 使用 MemoryFact 替代 Knowledge)
    memory_facts = db.query(MemoryFact).filter(MemoryFact.world_id == world_id).all()

    if not memory_facts:
        return []

    # 从 memory_facts 提取概念
    concepts = {}
    for fact in memory_facts:
        if fact.concept_tags:
            for tag in fact.concept_tags:
                concepts[tag] = {"name": tag, "mastery": int(fact.salience * 100)}

    # 按日期分组计算平均掌握度
    mastery_by_date: dict[str, list[float]] = {}

    for _concept_id, concept_data in concepts.items():
        if not isinstance(concept_data, dict):
            continue

        t_valid = concept_data.get("t_valid")
        if not t_valid:
            continue

        # 提取日期部分
        date = t_valid[:10]  # "2026-04-05T16:30:00Z" -> "2026-04-05"

        if date not in mastery_by_date:
            mastery_by_date[date] = []
        mastery_by_date[date].append(concept_data.get("mastery", 0))

    # 构建趋势数据
    trends = []
    for date in sorted(mastery_by_date.keys()):
        mastery_values = mastery_by_date[date]
        trends.append({
            "date": date,
            "average_mastery": round(sum(mastery_values) / len(mastery_values), 2),
            "concepts_learned": len(mastery_values)
        })

    return trends


# =============================================================================
# 关系进化历程
# =============================================================================

def get_relationship_history_by_user(db: Session, user_id: int) -> dict[str, Any]:
    """
    获取用户跨世界的关系进化历程。

    返回格式：
    {
        "events": [
            {
                "id": "evt-1",
                "world_id": 1,
                "world_name": "雅典学院",
                "character_name": "苏格拉底",
                "previous_stage": "acquaintance",
                "new_stage": "friend",
                "timestamp": "2026-04-01T10:00:00Z",
                "trigger_reason": "完成3次深入对话"
            }
        ],
        "current_stages": {"1": "friend", "2": "acquaintance"}
    }
    """
    # 获取所有关系阶段变化记录
    stage_records = (
        db.query(RelationshipStageRecord)
        .join(SessionModel, RelationshipStageRecord.session_id == SessionModel.id)
        .filter(SessionModel.user_id == user_id)
        .order_by(RelationshipStageRecord.updated_at.desc())
        .all()
    )

    events = []
    current_stages: dict[int, str] = {}

    # 获取世界信息缓存
    world_cache: dict[int, World] = {}

    for record in stage_records:
        session = (
            db.query(SessionModel)
            .filter(SessionModel.id == record.session_id)
            .first()
        )

        if not session:
            continue

        # 缓存世界信息
        if session.world_id not in world_cache:
            world_cache[session.world_id] = (
                db.query(World).filter(World.id == session.world_id).first()
            )
        world = world_cache.get(session.world_id)

        # 获取角色名
        character_name = "未知"
        if session.sage_character_id:
            character = (
                db.query(Character)
                .filter(Character.id == session.sage_character_id)
                .first()
            )
            if character:
                character_name = character.name

        event_id = f"evt-{record.id}"

        events.append({
            "id": event_id,
            "world_id": session.world_id,
            "world_name": world.name if world else "未知世界",
            "character_name": character_name,
            "previous_stage": _get_previous_stage(db, record, session),
            "new_stage": record.stage,
            "timestamp": record.updated_at.isoformat() if record.updated_at else None,
            "trigger_reason": record.reason
        })

        # 更新当前阶段
        if session.world_id not in current_stages:
            current_stages[session.world_id] = record.stage

    return {
        "events": events,
        "current_stages": current_stages
    }


def _get_previous_stage(
    db: Session,
    record: RelationshipStageRecord,
    session: SessionModel
) -> str:
    """获取前一个关系阶段"""
    # 查找同一会话中更早的阶段记录
    previous = (
        db.query(RelationshipStageRecord)
        .filter(
            RelationshipStageRecord.session_id == session.id,
            RelationshipStageRecord.id < record.id if record.id else True
        )
        .order_by(RelationshipStageRecord.id.desc())
        .first()
    )

    if previous:
        return previous.stage

    # 如果没有更早记录，从会话的初始关系状态获取
    if session.relationship:
        stage = session.relationship.get("stage")
        if stage:
            return stage

    return "stranger"


# =============================================================================
# 世界对比
# =============================================================================

def build_world_comparison(db: Session, user_id: int) -> list[dict[str, Any]]:
    """
    构建世界对比数据列表。

    返回格式：
    [
        {
            "world_id": 1,
            "world_name": "雅典学院",
            "total_sessions": 12,
            "total_concepts": 45,
            "average_mastery": 0.72,
            "relationship_stage": "friend",
            "last_active": "2026-04-05T16:00:00Z"
        }
    ]
    """
    worlds = db.query(World).filter(World.user_id == user_id).all()

    comparison = []

    for world in worlds:
        # 计算会话数
        total_sessions = (
            db.query(SessionModel)
            .filter(SessionModel.world_id == world.id)
            .count()
        )

        # 获取记忆事实统计 (P1 #183: 使用 MemoryFact 替代 Knowledge)
        memory_facts = db.query(MemoryFact).filter(MemoryFact.world_id == world.id).all()
        total_concepts = 0
        average_mastery = 0.0

        if memory_facts:
            # 统计概念数量和平均掌握度
            concept_mastery = {}
            for fact in memory_facts:
                if fact.concept_tags:
                    for tag in fact.concept_tags:
                        concept_mastery[tag] = int(fact.salience * 100)
            total_concepts = len(concept_mastery)
            if concept_mastery:
                average_mastery = sum(concept_mastery.values()) / total_concepts

        # 获取当前关系阶段
        latest_session = (
            db.query(SessionModel)
            .filter(SessionModel.world_id == world.id)
            .order_by(SessionModel.started_at.desc())
            .first()
        )

        relationship_stage = "stranger"
        if latest_session and latest_session.relationship:
            relationship_stage = latest_session.relationship.get("stage", "stranger")

        # 获取最后活跃时间
        last_active = None
        if latest_session:
            last_active = (
                latest_session.ended_at.isoformat()
                if latest_session.ended_at
                else latest_session.started_at.isoformat()
            )

        comparison.append({
            "world_id": world.id,
            "world_name": world.name,
            "total_sessions": total_sessions,
            "total_concepts": total_concepts,
            "average_mastery": round(average_mastery, 2),
            "relationship_stage": relationship_stage,
            "last_active": last_active
        })

    return comparison


# =============================================================================
# 里程碑事件
# =============================================================================

def get_milestone_events(
    db: Session,
    world_id: int | None = None,
    user_id: int | None = None
) -> list[dict[str, Any]]:
    """
    获取里程碑事件列表。

    事件类型：
    - relationship_upgrade: 关系阶段提升
    - concept_mastered: 概念掌握
    - session_completed: 会话完成
    """
    events = []
    event_id = 0

    # 关系阶段提升事件
    stage_query = (
        db.query(RelationshipStageRecord)
        .join(SessionModel, RelationshipStageRecord.session_id == SessionModel.id)
    )

    if world_id:
        stage_query = stage_query.filter(SessionModel.world_id == world_id)
    if user_id:
        stage_query = stage_query.filter(SessionModel.user_id == user_id)

    stage_records = stage_query.order_by(RelationshipStageRecord.updated_at.desc()).all()

    for record in stage_records:
        session = (
            db.query(SessionModel)
            .filter(SessionModel.id == record.session_id)
            .first()
        )
        if not session:
            continue

        world = db.query(World).filter(World.id == session.world_id).first()

        event_id += 1
        events.append({
            "id": f"milestone-{event_id}",
            "type": "relationship_upgrade",
            "title": f"关系进阶：{_get_stage_label(record.stage)}",
            "description": f"在{world.name if world else '未知世界'}达成{_get_stage_label(record.stage)}阶段",
            "timestamp": record.updated_at.isoformat() if record.updated_at else None,
            "world_id": session.world_id
        })

    # 会话完成事件（只记录有结束时间的会话）
    session_query = db.query(SessionModel).filter(SessionModel.ended_at.isnot(None))

    if world_id:
        session_query = session_query.filter(SessionModel.world_id == world_id)
    if user_id:
        session_query = session_query.filter(SessionModel.user_id == user_id)

    sessions = session_query.order_by(SessionModel.ended_at.desc()).limit(50).all()

    for session in sessions:
        world = db.query(World).filter(World.id == session.world_id).first()
        course = db.query(Course).filter(Course.id == session.course_id).first()

        event_id += 1
        events.append({
            "id": f"milestone-{event_id}",
            "type": "session_completed",
            "title": f"完成会话：{course.name if course else '未知课程'}",
            "description": f"在{world.name if world else '未知世界'}完成学习会话",
            "timestamp": session.ended_at.isoformat() if session.ended_at else None,
            "world_id": session.world_id
        })

    # 按时间倒序排序
    events.sort(
        key=lambda x: x.get("timestamp") or "",
        reverse=True
    )

    return events[:20]  # 最多返回20条


def _get_stage_label(stage: str) -> str:
    """获取阶段中文标签"""
    labels = {
        "stranger": "陌生人",
        "acquaintance": "相识",
        "friend": "朋友",
        "mentor": "导师",
        "partner": "伙伴"
    }
    return labels.get(stage, stage)
