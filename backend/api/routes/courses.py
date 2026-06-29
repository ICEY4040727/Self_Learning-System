from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from backend.api.routes.auth import get_current_user
from backend.db.database import get_db
from backend.models import models as models_module
from backend.models.models import (
    Character,
    ChatMessage,
    Course,
    MemoryFact,
    User,
    World,
    WorldCharacter,
)


router = APIRouter()

class CourseCreate(BaseModel):
    world_id: int
    name: str
    description: str | None = None
    target_level: str | None = None
    # meta JSON: 存储表单扩展字段 (Phase 1 新增)
    # 见文档: docs/v1.0.0前后端联调修复/世界_课程_角色_表单设计.md 附录 A
    # 格式: {"domain": "programming", "current_level": "none", "target_level": "applier",
    #        "motivation": "work", "pace": "normal", "weekly_minutes": 90, "sage_ids": [12, 17]}
    meta: dict | None = None


class CourseResponse(CourseCreate):
    id: int
    progress: float | None = None  # 0.0 - 1.0 课程完成度
    icon: str | None = None  # 课程图标

    model_config = ConfigDict(from_attributes=True)


class CourseInWorldCreate(BaseModel):
    name: str
    description: str | None = None
    target_level: str | None = None
    # meta JSON: 存储表单扩展字段 (Phase 1 新增)
    meta: dict | None = None


# Course endpoints
@router.post("/worlds/{world_id}/courses", response_model=CourseResponse)
def create_world_course(
    world_id: int,
    course: CourseInWorldCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_course(
        CourseCreate(
            world_id=world_id,
            name=course.name,
            description=course.description,
            target_level=course.target_level,
            meta=course.meta,  # Phase 1 新增
        ),
        db,
        current_user,
    )


@router.get("/worlds/{world_id}/courses", response_model=list[CourseResponse])
def get_world_courses(
    world_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_courses(world_id, db, current_user)


@router.post("/courses", response_model=CourseResponse)
def create_course(
    course: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    world = db.query(World).filter(
        World.id == course.world_id,
        World.user_id == current_user.id,
    ).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    db_course = Course(
        **course.model_dump()
    )
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course


@router.get("/courses", response_model=list[CourseResponse])
def get_courses(
    world_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Course).join(World, Course.world_id == World.id).filter(
        World.user_id == current_user.id
    )
    if world_id:
        query = query.filter(Course.world_id == world_id)
    return query.all()


@router.get("/courses/{course_id}", response_model=CourseResponse)
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = db.query(Course).join(World, Course.world_id == World.id).filter(
        Course.id == course_id,
        World.user_id == current_user.id,
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.put("/courses/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: int,
    course: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    world = db.query(World).filter(
        World.id == course.world_id,
        World.user_id == current_user.id,
    ).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    db_course = db.query(Course).join(World, Course.world_id == World.id).filter(
        Course.id == course_id,
        World.user_id == current_user.id,
    ).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")

    for key, value in course.model_dump().items():
        setattr(db_course, key, value)

    db.commit()
    db.refresh(db_course)
    return db_course


@router.delete("/courses/{course_id}", status_code=204)
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = db.query(Course).join(World, Course.world_id == World.id).filter(
        Course.id == course_id,
        World.user_id == current_user.id,
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    db.delete(course)
    db.commit()


# Issue #188: Course related APIs
# ============================================

class CourseSessionResponse(BaseModel):
    id: int
    started_at: datetime
    ended_at: datetime | None
    relationship_stage: str | None
    course_name: str | None = None
    message_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class MemoryFactStatsResponse(BaseModel):
    total: int
    by_type: dict[str, int]
    avg_salience: float


class MemoryFactResponse(BaseModel):
    id: int
    fact_type: str
    content: str
    concept_tags: list[str] | None
    salience: float
    created_at: datetime
    recall_count: int

    model_config = ConfigDict(from_attributes=True)


def _get_course_with_auth(course_id: int, db: Session, current_user: User) -> Course:
    """Verify course exists and user has access."""
    course = db.query(Course).join(World, Course.world_id == World.id).filter(
        Course.id == course_id,
        World.user_id == current_user.id,
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.get("/courses/{course_id}/sages")
def get_course_sages(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取课程关联的 Sage 角色列表。

    优先返回当前世界里真正可用的 Sage。
    如果 Course.meta.sage_ids 存在，则只保留已经绑定到该世界的 Sage，
    避免课程页展示点了会 404 的老师。
    """
    course = _get_course_with_auth(course_id, db, current_user)

    world_sage_links = db.query(WorldCharacter).filter(
        WorldCharacter.world_id == course.world_id,
        WorldCharacter.role == "sage",
    ).order_by(WorldCharacter.is_primary.desc(), WorldCharacter.id.asc()).all()
    world_sage_ids = [link.character_id for link in world_sage_links]
    world_link_by_character_id = {link.character_id: link for link in world_sage_links}

    # Course.meta.sage_ids 只作为课程级优先顺序，不再返回未绑定到该世界的角色。
    requested_ids = course.meta.get("sage_ids", []) if course.meta else []
    selected_ids = [sage_id for sage_id in requested_ids if sage_id in world_sage_ids]
    if not selected_ids:
        selected_ids = world_sage_ids

    if selected_ids:
        sages = db.query(Character).filter(
            Character.id.in_(selected_ids),
            Character.user_id == current_user.id,
        ).all()
    else:
        sages = []

    sage_by_id = {sage.id: sage for sage in sages}

    from backend.models.models import Session as SessionModel
    latest_sessions = db.query(SessionModel).filter(
        SessionModel.course_id == course_id,
        SessionModel.user_id == current_user.id,
        SessionModel.sage_character_id.in_(selected_ids if selected_ids else [0]),
    ).order_by(SessionModel.started_at.desc()).all()
    latest_session_by_sage_id: dict[int, SessionModel] = {}
    for session in latest_sessions:
        if session.sage_character_id and session.sage_character_id not in latest_session_by_sage_id:
            latest_session_by_sage_id[session.sage_character_id] = session

    def _fallback_symbol(character: Character) -> str:
        if character.tags and isinstance(character.tags, list) and character.tags:
            first = str(character.tags[0]).strip()
            if first:
                return first[:2]
        return character.name[:1]

    result = []
    for character_id in selected_ids:
        sage = sage_by_id.get(character_id)
        if not sage:
            continue
        link = world_link_by_character_id.get(character_id)
        latest_session = latest_session_by_sage_id.get(character_id)
        relationship_stage = None
        if latest_session and latest_session.relationship:
            relationship_stage = latest_session.relationship.get("stage", "stranger")

        result.append({
            "id": sage.id,
            "name": sage.name,
            "title": (link.world_title if link and link.world_title else None) or sage.title or sage.personality or "",
            "personality": sage.personality,
            "avatar": sage.avatar,
            "symbol": _fallback_symbol(sage),
            "relationshipStage": relationship_stage or "stranger",
            "lastSessionTime": latest_session.started_at.isoformat() if latest_session else None,
        })

    return result


@router.get("/courses/{course_id}/sessions", response_model=list[CourseSessionResponse])
def get_course_sessions(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取课程的所有学习会话。
    """
    course = _get_course_with_auth(course_id, db, current_user)

    from backend.models.models import Session as SessionModel
    sessions = db.query(SessionModel).filter(
        SessionModel.course_id == course_id,
        SessionModel.user_id == current_user.id,
    ).order_by(SessionModel.started_at.desc()).all()

    # Aggregate message count for each session
    session_ids = [s.id for s in sessions]
    message_counts: dict[int, int] = {}
    if session_ids:
        counts = db.query(ChatMessage.session_id, sa_func.count(ChatMessage.id)).filter(
            ChatMessage.session_id.in_(session_ids)
        ).group_by(ChatMessage.session_id).all()
        message_counts = dict(counts)

    return [
        CourseSessionResponse(
            id=s.id,
            started_at=s.started_at,
            ended_at=s.ended_at,
            relationship_stage=(s.relationship or {}).get("stage") if s.relationship else None,
            course_name=course.name,
            message_count=message_counts.get(s.id, 0),
        )
        for s in sessions
    ]


@router.get("/courses/{course_id}/memory-facts")
def get_course_memory_facts(
    course_id: int,
    stats_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取课程关联的记忆事实。

    - stats_only=true: 只返回统计信息
    - stats_only=false: 返回统计 + 记忆列表

    关联方式: 通过 course 的 world_id 查询 world 级别的记忆，
    或者通过 session 关联的 character_id 查询。
    """
    course = _get_course_with_auth(course_id, db, current_user)

    # 获取该课程世界的所有 sage characters
    sage_links = db.query(WorldCharacter).filter(
        WorldCharacter.world_id == course.world_id,
        WorldCharacter.role == "sage",
    ).all()
    sage_character_ids = [link.character_id for link in sage_links]

    if not sage_character_ids:
        if stats_only:
            return MemoryFactStatsResponse(total=0, by_type={}, avg_salience=0.0)
        return {"stats": MemoryFactStatsResponse(total=0, by_type={}, avg_salience=0.0), "facts": []}

    # 查询记忆事实
    facts_query = db.query(MemoryFact).filter(
        MemoryFact.character_id.in_(sage_character_ids),
        # 包含世界级别或跨世界记忆
        (MemoryFact.world_id == course.world_id) | (MemoryFact.world_id.is_(None))
    )

    facts = facts_query.all()

    # 计算统计
    total = len(facts)
    by_type: dict[str, int] = {}
    total_salience = 0.0

    for fact in facts:
        by_type[fact.fact_type] = by_type.get(fact.fact_type, 0) + 1
        total_salience += fact.salience

    avg_salience = total_salience / total if total > 0 else 0.0

    stats = MemoryFactStatsResponse(
        total=total,
        by_type=by_type,
        avg_salience=round(avg_salience, 3),
    )

    if stats_only:
        return stats

    return {
        "stats": stats,
        "facts": [
            MemoryFactResponse(
                id=f.id,
                fact_type=f.fact_type,
                content=f.content[:200],  # 限制内容长度
                concept_tags=f.concept_tags,
                salience=f.salience,
                created_at=f.created_at,
                recall_count=f.recall_count,
            )
            for f in facts[:50]  # 最多返回50条
        ],
    }
