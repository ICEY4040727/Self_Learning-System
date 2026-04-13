"""
UserProfile Service - 用户全局画像服务（增量更新版）

根据 learning_memory_theory.md 第五部分的设计，实现跨世界特征聚合。
采用增量更新策略，避免每次全量重算。

核心设计：
- UserProfile.profile 存储两部分数据：
  - raw_worlds: 每个世界的原始 LearnerProfile 数据（带时间戳）
  - aggregated: 聚合后的结果（缓存）

- 当 LearnerProfile 更新时，只更新对应的 raw_worlds[world_id]
- 读取时，聚合 raw_worlds 生成结果
"""

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.models.models import LearnerProfile, MemoryFact, UserProfile

# MSKT 元认知四维度
MSKT_DIMENSIONS = ["planning", "monitoring", "regulating", "reflecting"]

# 学习偏好特征
PREFERENCE_TRAITS = ["visual_examples", "analogy_based", "step_by_step", "pace"]


def normalize_mskt_value(value: str | None) -> int:
    """将 MSKT 字符串值归一化为数值用于趋势计算"""
    mapping = {"weak": 1, "moderate": 2, "strong": 3}
    return mapping.get(value, 0)


def compute_metacognition_trend(world_profiles: list[dict]) -> dict[str, Any]:
    """
    计算元认知趋势 - 展示成长而非快照

    设计原则：
    - 需要 ≥2 个世界的数据才能计算趋势
    - 值可能是 "weak/moderate/strong"，需要归一化处理
    """
    result = {}

    for dim in MSKT_DIMENSIONS:
        dim_records = []
        for profile in world_profiles:
            dim_data = profile.get("metacognition", {}).get(dim)
            if dim_data:
                dim_records.append({
                    "world_id": profile.get("world_id"),
                    "value": dim_data.get("value"),
                    "t_updated": dim_data.get("t_updated"),
                    "evidence": dim_data.get("evidence", "")
                })

        if not dim_records:
            continue

        # 计算趋势（需要 ≥2 个时间点）
        if len(dim_records) >= 2:
            dim_records.sort(key=lambda x: x.get("t_updated") or "")
            earliest = normalize_mskt_value(dim_records[0].get("value"))
            latest = normalize_mskt_value(dim_records[-1].get("value"))
            trend = "improving" if latest > earliest else "stable"

            result[dim] = {
                "current": dim_records[-1].get("value"),
                "trend": trend,
                "evidence_count": len(dim_records),
                "latest_evidence": dim_records[-1].get("evidence", "")
            }
        else:
            result[dim] = {
                "current": dim_records[0].get("value"),
                "trend": "unknown",
                "evidence_count": 1
            }

    return result


def compute_preference_stability(world_profiles: list[dict]) -> dict[str, Any]:
    """
    计算偏好稳定性 - 衡量偏好在世界间的一致性

    为什么需要稳定性？
    - 高稳定性 → 偏好在多个世界都一致，可信度高
    - 低稳定性 → 偏好可能是领域特定的
    """
    result = {}

    for trait in PREFERENCE_TRAITS:
        trait_values = []
        for profile in world_profiles:
            trait_data = profile.get("preferences", {}).get(trait)
            if trait_data:
                trait_values.append({
                    "world_id": profile.get("world_id"),
                    "value": trait_data.get("value"),
                    "confidence": trait_data.get("confidence", 0.5)
                })

        if len(trait_values) < 2:
            result[trait] = {"status": "insufficient_data"}
            continue

        values = [v["value"] for v in trait_values]

        # 布尔值：计算一致率
        if all(isinstance(v, bool) for v in values):
            true_count = sum(1 for v in values if v)
            consistency = true_count / len(values)
            result[trait] = {
                "stable": consistency >= 0.7,  # ≥70% 一致认为稳定
                "consistency": consistency,
                "display": "稳定" if consistency >= 0.7 else "变化中"
            }

        # 枚举值：找出最常见的
        elif all(isinstance(v, str) for v in values):
            most_common = Counter(values).most_common(1)[0]
            result[trait] = {
                "stable": most_common[1] / len(values) >= 0.7,
                "most_common": most_common[0],
                "display": most_common[0]
            }
        else:
            # 混合类型或未知类型
            result[trait] = {"status": "unsupported_type"}

    return result


def compute_learning_stats(db: Session, world_profiles: list[dict]) -> dict[str, Any]:
    """
    计算跨世界学习统计
    """
    total_concepts = 0
    total_sessions = 0
    mastery_scores = []

    for profile in world_profiles:
        world_id = profile.get("world_id")

        # 从记忆事实获取概念数 (P1 #183: 使用 MemoryFact 替代 Knowledge)
        memory_facts = db.query(MemoryFact).filter(MemoryFact.world_id == world_id).all()
        if memory_facts:
            # 统计概念
            concepts = set()
            for fact in memory_facts:
                if fact.concept_tags:
                    concepts.update(fact.concept_tags)
            total_concepts += len(concepts)

            # 计算该世界的平均掌握度
            if concepts:
                mastery_sum = sum(
                    int(fact.salience * 100)
                    for fact in memory_facts
                    if fact.concept_tags
                )
                avg_mastery = mastery_sum / len(concepts) if concepts else 0
                mastery_scores.append(avg_mastery)

        # 从 profile 获取会话数
        total_sessions += profile.get("session_count", 0)

    return {
        "total_concepts_learned": total_concepts,
        "total_sessions": total_sessions,
        "average_mastery": round(sum(mastery_scores) / len(mastery_scores), 2) if mastery_scores else 0,
        "worlds_explored": len(world_profiles)
    }


def compute_user_profile(db: Session, user_id: int) -> dict[str, Any]:
    """
    计算用户全局画像 - 聚合所有世界的 LearnerProfile

    这是全量计算函数，用于初始化或强制重算。
    """
    # 获取用户所有世界的 LearnerProfile
    learner_profiles = (
        db.query(LearnerProfile)
        .filter(LearnerProfile.user_id == user_id)
        .all()
    )

    # 转换为 dict 列表（包含 world_id）
    world_profiles = []
    for lp in learner_profiles:
        profile_data = lp.profile or {}
        profile_data["world_id"] = lp.world_id
        profile_data["updated_at"] = lp.updated_at.isoformat() if lp.updated_at else None
        world_profiles.append(profile_data)

    # 三个核心计算
    metacognition_trend = compute_metacognition_trend(world_profiles)
    preference_stability = compute_preference_stability(world_profiles)
    learning_stats = compute_learning_stats(db, world_profiles)

    return {
        "user_id": user_id,
        "computed_at": datetime.now(UTC).isoformat(),
        "metacognition_trend": metacognition_trend,
        "preference_stability": preference_stability,
        "learning_stats": learning_stats
    }


# ============================================
# 增量更新版本
# ============================================

def get_raw_worlds(profile: dict) -> dict[int, dict]:
    """获取原始世界数据"""
    return profile.get("raw_worlds", {})


def set_raw_worlds(profile: dict, raw_worlds: dict[int, dict]) -> None:
    """设置原始世界数据"""
    profile["raw_worlds"] = raw_worlds


def get_aggregated(profile: dict) -> dict:
    """获取聚合结果"""
    return profile.get("aggregated", {})


def set_aggregated(profile: dict, aggregated: dict) -> None:
    """设置聚合结果"""
    profile["aggregated"] = aggregated


def update_single_world(
    db: Session,
    user_profile: UserProfile,
    world_id: int,
    learner_profile: LearnerProfile
) -> dict:
    """
    增量更新单个世界的数据

    只更新该世界的原始数据，然后重新聚合。
    """
    profile = user_profile.profile or {}

    # 获取或创建 raw_worlds
    raw_worlds = get_raw_worlds(profile)

    # 获取当前 LearnerProfile 数据
    profile_data = learner_profile.profile or {}
    profile_data["world_id"] = world_id
    profile_data["updated_at"] = datetime.now(UTC).isoformat()

    # 增量更新：只更新这一个世界
    raw_worlds[world_id] = profile_data

    # 重新聚合所有世界的数据
    world_profiles = list(raw_worlds.values())
    metacognition_trend = compute_metacognition_trend(world_profiles)
    preference_stability = compute_preference_stability(world_profiles)
    learning_stats = compute_learning_stats(db, world_profiles)

    aggregated = {
        "metacognition_trend": metacognition_trend,
        "preference_stability": preference_stability,
        "learning_stats": learning_stats
    }

    # 更新 profile
    set_raw_worlds(profile, raw_worlds)
    set_aggregated(profile, aggregated)

    return profile


def update_session_count(
    db: Session,
    user_profile: UserProfile,
    world_id: int
) -> dict:
    """
    增量更新会话数

    只增加该世界的 session_count，不重算其他数据。
    """
    profile = user_profile.profile or {}
    raw_worlds = get_raw_worlds(profile)

    if world_id in raw_worlds:
        world_data = raw_worlds[world_id]
        world_data["session_count"] = world_data.get("session_count", 0) + 1
    else:
        # 如果世界不存在，创建新记录
        raw_worlds[world_id] = {"session_count": 1}

    # 更新 session_count（这是增量操作）
    aggregated = get_aggregated(profile)
    if aggregated:
        learning_stats = aggregated.get("learning_stats", {})
        learning_stats["total_sessions"] = learning_stats.get("total_sessions", 0) + 1
        aggregated["learning_stats"] = learning_stats

    set_raw_worlds(profile, raw_worlds)

    return profile


def get_or_create_user_profile(db: Session, user_id: int) -> UserProfile:
    """
    获取或创建 UserProfile

    首次创建时执行全量计算，后续返回缓存。
    """
    user_profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == user_id)
        .first()
    )

    if not user_profile:
        # 首次创建，执行全量计算
        computed_data = compute_user_profile(db, user_id)
        user_profile = UserProfile(
            user_id=user_id,
            profile={
                "raw_worlds": {},
                "aggregated": computed_data,
                "computed_at": datetime.now(UTC).isoformat()
            },
            computed_at=datetime.now(UTC)
        )
        db.add(user_profile)
        db.commit()
        db.refresh(user_profile)

        # 填充 raw_worlds
        _populate_raw_worlds_from_db(db, user_profile)
    else:
        # 检查是否需要重新聚合（如果 raw_worlds 为空但 aggregated 存在）
        profile = user_profile.profile or {}
        if not get_raw_worlds(profile) and get_aggregated(profile):
            _populate_raw_worlds_from_db(db, user_profile)

    return user_profile


def _populate_raw_worlds_from_db(db: Session, user_profile: UserProfile) -> None:
    """从数据库填充 raw_worlds（迁移旧数据或修复）"""
    learner_profiles = (
        db.query(LearnerProfile)
        .filter(LearnerProfile.user_id == user_profile.user_id)
        .all()
    )

    profile = user_profile.profile or {}
    raw_worlds = get_raw_worlds(profile)

    for lp in learner_profiles:
        profile_data = lp.profile or {}
        profile_data["world_id"] = lp.world_id
        profile_data["updated_at"] = lp.updated_at.isoformat() if lp.updated_at else None
        raw_worlds[lp.world_id] = profile_data

    # 重新聚合
    world_profiles = list(raw_worlds.values())
    aggregated = {
        "metacognition_trend": compute_metacognition_trend(world_profiles),
        "preference_stability": compute_preference_stability(world_profiles),
        "learning_stats": compute_learning_stats(db, world_profiles)
    }

    set_raw_worlds(profile, raw_worlds)
    set_aggregated(profile, aggregated)
    user_profile.computed_at = datetime.now(UTC)

    db.commit()


def update_user_profile_after_chat(
    db: Session,
    user_id: int,
    world_id: int
) -> None:
    """
    在聊天消息后调用 - 增量更新

    只更新指定世界的 LearnerProfile 引用。
    """
    user_profile = get_or_create_user_profile(db, user_id)

    # 获取当前世界的 LearnerProfile
    learner_profile = (
        db.query(LearnerProfile)
        .filter(
            LearnerProfile.user_id == user_id,
            LearnerProfile.world_id == world_id
        )
        .first()
    )

    if learner_profile:
        # 增量更新该世界
        user_profile.profile = update_single_world(db, user_profile, world_id, learner_profile)
        user_profile.computed_at = datetime.now(UTC)
        db.commit()


def update_user_profile_after_session_end(
    db: Session,
    user_id: int,
    world_id: int
) -> None:
    """
    在会话结束后调用 - 增量更新会话数
    """
    user_profile = get_or_create_user_profile(db, user_id)

    # 增量更新会话数
    user_profile.profile = update_session_count(db, user_profile, world_id)
    user_profile.computed_at = datetime.now(UTC)
    db.commit()


def get_user_profile(db: Session, user_id: int) -> dict[str, Any]:
    """
    获取用户画像

    返回聚合后的数据。
    如果 raw_worlds 与 aggregated 不一致，重新计算。
    """
    user_profile = get_or_create_user_profile(db, user_id)
    profile = user_profile.profile or {}

    # 检查是否需要重新聚合
    raw_worlds = get_raw_worlds(profile)
    aggregated = get_aggregated(profile)

    if not aggregated or not raw_worlds:
        # 首次访问或数据损坏，重新计算
        computed = compute_user_profile(db, user_id)
        return computed

    # 检查是否过期（超过24小时）
    now = datetime.now(UTC)
    last_computed = user_profile.computed_at
    if last_computed and (now - last_computed).total_seconds() > 86400:
        # 重新聚合
        world_profiles = list(raw_worlds.values())
        aggregated = {
            "metacognition_trend": compute_metacognition_trend(world_profiles),
            "preference_stability": compute_preference_stability(world_profiles),
            "learning_stats": compute_learning_stats(db, world_profiles)
        }
        set_aggregated(profile, aggregated)
        user_profile.computed_at = now
        db.commit()

    # 返回聚合结果
    result = {
        "user_id": user_id,
        "computed_at": user_profile.computed_at.isoformat() if user_profile.computed_at else None,
        **aggregated
    }

    return result
