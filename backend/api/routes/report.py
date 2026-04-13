"""
Report API Routes - 学习报告相关 API

提供全局报告和世界档案相关的数据接口。
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.routes.auth import get_current_user
from backend.db.database import get_db
from backend.models.models import User
from backend.services.report import (
    build_world_comparison,
    get_mastery_trends_by_user,
    get_milestone_events,
    get_relationship_history_by_user,
    get_world_mastery_trends,
)

router = APIRouter()


# =============================================================================
# Pydantic Schemas
# =============================================================================

class MasteryTrendItem(BaseModel):
    concept_name: str
    mastery_level: float
    last_updated: str | None
    world_id: int
    world_name: str


class MasteryTrendResponse(BaseModel):
    trends: list[MasteryTrendItem]
    average_mastery: float
    improved_count: int
    declined_count: int


class RelationshipEvent(BaseModel):
    id: str
    world_id: int
    world_name: str
    character_name: str
    previous_stage: str
    new_stage: str
    timestamp: str | None
    trigger_reason: str | None


class RelationshipHistoryResponse(BaseModel):
    events: list[RelationshipEvent]
    current_stages: dict[int, str]


class WorldComparisonItem(BaseModel):
    world_id: int
    world_name: str
    total_sessions: int
    total_concepts: int
    average_mastery: float
    relationship_stage: str
    last_active: str | None


class MilestoneEvent(BaseModel):
    id: str
    type: str
    title: str
    description: str
    timestamp: str | None
    world_id: int | None


class WorldMasteryTrendItem(BaseModel):
    date: str
    average_mastery: float
    concepts_learned: int


# =============================================================================
# 全局报告 API（跨世界）
# =============================================================================

@router.get("/mastery-trends", response_model=MasteryTrendResponse)
def get_mastery_trends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取跨世界的知识掌握度趋势。
    """
    result = get_mastery_trends_by_user(db, current_user.id)

    # 转换为 Pydantic 模型
    trends = [
        MasteryTrendItem(
            concept_name=t["concept_name"],
            mastery_level=t["mastery_level"],
            last_updated=t["last_updated"],
            world_id=t["world_id"],
            world_name=t["world_name"],
        )
        for t in result.get("trends", [])
    ]

    return MasteryTrendResponse(
        trends=trends,
        average_mastery=result.get("average_mastery", 0),
        improved_count=result.get("improved_count", 0),
        declined_count=result.get("declined_count", 0),
    )


@router.get("/relationship-history", response_model=RelationshipHistoryResponse)
def get_relationship_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取关系进化历程。
    """
    result = get_relationship_history_by_user(db, current_user.id)

    # 转换 current_stages 的 key 为 int
    current_stages = {
        int(k): v for k, v in result.get("current_stages", {}).items()
    }

    return RelationshipHistoryResponse(
        events=[
            RelationshipEvent(**e) for e in result.get("events", [])
        ],
        current_stages=current_stages,
    )


@router.get("/world-comparison", response_model=list[WorldComparisonItem])
def get_world_comparison(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取世界对比数据。
    """
    result = build_world_comparison(db, current_user.id)
    return [WorldComparisonItem(**item) for item in result]


@router.get("/milestones", response_model=list[MilestoneEvent])
def get_milestones(
    world_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取里程碑事件。

    如果不指定 world_id，返回所有世界的里程碑。
    如果指定 world_id，返回该世界的里程碑。
    """
    result = get_milestone_events(
        db=db,
        world_id=world_id,
        user_id=current_user.id
    )
    return [MilestoneEvent(**e) for e in result]


# =============================================================================
# 世界档案 API（单世界）
# =============================================================================

@router.get("/worlds/{world_id}/mastery-trends", response_model=list[WorldMasteryTrendItem])
def get_world_mastery_trends_api(
    world_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取单个世界的知识掌握度趋势。
    """
    result = get_world_mastery_trends(db, world_id, current_user.id)
    return [WorldMasteryTrendItem(**item) for item in result]
