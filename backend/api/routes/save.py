from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.routes.auth import get_current_user
from backend.db.database import get_db
from backend.models import models as models_module
from backend.models.models import (
    Character,
    ChatMessage,
    Checkpoint,
    Course,
    LearnerProfile,
    TeacherPersona,
    User,
    World,
)
from backend.models.models import (
    Session as SessionModel,
)

router = APIRouter()


class CheckpointCreate(BaseModel):
    world_id: int
    save_name: str = Field(..., max_length=100, pattern=r"^[a-zA-Z0-9_\-\u4e00-\u9fff]+$")
    session_id: int | None = None
    message_index: int | None = None
    thumbnail_path: str | None = None


class CheckpointResponse(BaseModel):
    id: int
    world_id: int
    session_id: int | None = None
    save_name: str
    message_index: int
    thumbnail_path: str | None = None
    created_at: datetime
    date: str | None = None  # 格式化日期
    stage: str | None = None  # 关系阶段
    masteryPercent: float | None = None  # 掌握度
    previewText: str | None = None  # 预览文本

    class Config:
        from_attributes = True


class LegacySaveCreate(BaseModel):
    subject_id: int
    save_name: str = Field(..., max_length=100, pattern=r"^[a-zA-Z0-9_\-\u4e00-\u9fff]+$")
    session_id: int | None = None


class LegacySaveSummary(BaseModel):
    id: int
    save_name: str
    created_at: datetime


class BranchRequest(BaseModel):
    branch_name: str | None = None


@router.post("/checkpoints", response_model=CheckpointResponse)
async def create_checkpoint(
    payload: CheckpointCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    world = db.query(World).filter(
        World.id == payload.world_id,
        World.user_id == current_user.id,
    ).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    db_session = None
    if payload.session_id is not None:
        db_session = db.query(SessionModel).filter(
            SessionModel.id == payload.session_id,
            SessionModel.user_id == current_user.id,
            SessionModel.world_id == payload.world_id,
        ).first()
        if not db_session:
            raise HTTPException(status_code=404, detail="Session not found in world")

    message_index = payload.message_index
    if message_index is None:
        if db_session:
            message_index = int(
                db.query(ChatMessage).filter(ChatMessage.session_id == db_session.id).count()
            )
        else:
            message_index = 0

    relationship = (
        db_session.relationship
        if db_session and db_session.relationship
        else models_module._default_relationship()
    )

    state = {
        "relationship": relationship,
        "course_id": db_session.course_id if db_session else None,
        "sage_character_id": db_session.sage_character_id if db_session else None,
        "traveler_character_id": db_session.traveler_character_id if db_session else None,
    }

    checkpoint = Checkpoint(
        user_id=current_user.id,
        world_id=payload.world_id,
        session_id=payload.session_id,
        save_name=payload.save_name,
        message_index=message_index,
        state=state,
        thumbnail_path=payload.thumbnail_path,
    )
    db.add(checkpoint)
    db.commit()
    db.refresh(checkpoint)
    return checkpoint


def _build_checkpoint_response(cp: Checkpoint, db: Session, user_id: int) -> CheckpointResponse:
    """Build CheckpointResponse with extended fields."""
    state = cp.state or {}
    relationship = state.get("relationship", {})
    
    # Extract relationship stage
    stage = None
    if relationship:
        stage_map = {
            "stranger": "初识",
            "acquaintance": "相识",
            "friend": "朋友",
            "mentor": "导师",
            "partner": "伙伴",
        }
        stage = stage_map.get(relationship.get("stage", ""), relationship.get("stage"))
    
    # Format date
    date = cp.created_at.strftime("%Y-%m-%d %H:%M") if cp.created_at else None
    
    # Calculate mastery from progress tracking
    mastery = None
    course_id = state.get("course_id")
    if course_id:
        from backend.models.models import ProgressTracking
        progress_list = db.query(ProgressTracking).filter(
            ProgressTracking.course_id == course_id,
            ProgressTracking.user_id == user_id
        ).all()
        if progress_list:
            total = sum(p.mastery_level for p in progress_list)
            mastery = total / len(progress_list) / 100.0  # Convert to 0-1 range
    
    # Get preview text from chat history
    preview = None
    if cp.session_id:
        from backend.models.models import ChatMessage
        last_msgs = db.query(ChatMessage).filter(
            ChatMessage.session_id == cp.session_id
        ).order_by(ChatMessage.id.desc()).limit(2).all()
        if last_msgs:
            preview = last_msgs[0].content[:100] if last_msgs else None
    
    return CheckpointResponse(
        id=cp.id,
        world_id=cp.world_id,
        session_id=cp.session_id,
        save_name=cp.save_name,
        message_index=cp.message_index,
        thumbnail_path=cp.thumbnail_path,
        created_at=cp.created_at,
        date=date,
        stage=stage,
        masteryPercent=mastery,
        previewText=preview,
    )


@router.get("/checkpoints", response_model=list[CheckpointResponse])
async def list_checkpoints(
    world_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Checkpoint).filter(Checkpoint.user_id == current_user.id)
    if world_id is not None:
        query = query.filter(Checkpoint.world_id == world_id)
    checkpoints = query.order_by(Checkpoint.created_at.desc()).all()
    return [_build_checkpoint_response(cp, db, current_user.id) for cp in checkpoints]


def _get_owned_world(db: Session, current_user: User, world_id: int) -> World:
    world = db.query(World).filter(
        World.id == world_id,
        World.user_id == current_user.id,
    ).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")
    return world


@router.get("/worlds/{world_id}/checkpoints", response_model=list[CheckpointResponse])
async def list_world_checkpoints(
    world_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_world(db, current_user, world_id)
    return await list_checkpoints(world_id, db, current_user)


@router.post("/checkpoints/{checkpoint_id}/branch")
async def branch_from_checkpoint(
    checkpoint_id: int,
    payload: BranchRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    checkpoint = db.query(Checkpoint).filter(
        Checkpoint.id == checkpoint_id,
        Checkpoint.user_id == current_user.id,
    ).first()
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    _get_owned_world(db, current_user, checkpoint.world_id)
    state = checkpoint.state or {}

    source_session = None
    if checkpoint.session_id is not None:
        source_session = db.query(SessionModel).filter(
            SessionModel.id == checkpoint.session_id,
            SessionModel.user_id == current_user.id,
        ).first()

    course_id = state.get("course_id")
    if course_id is None and source_session is not None:
        course_id = source_session.course_id
    if course_id is None:
        raise HTTPException(status_code=400, detail="Checkpoint missing course context")

    course = _get_owned_course(db, current_user, int(course_id))
    if course.world_id != checkpoint.world_id:
        raise HTTPException(status_code=400, detail="Checkpoint world/course mismatch")

    sage_character_id = state.get("sage_character_id")
    traveler_character_id = state.get("traveler_character_id")
    relationship = state.get("relationship")
    if not isinstance(relationship, dict):
        relationship = (
            source_session.relationship
            if source_session and isinstance(source_session.relationship, dict)
            else models_module._default_relationship()
        )

    teacher_persona_id = None
    if sage_character_id is not None:
        character = db.query(Character).filter(
            Character.id == int(sage_character_id),
            Character.user_id == current_user.id,
        ).first()
        if character:
            persona = db.query(TeacherPersona).filter(
                TeacherPersona.character_id == character.id,
                TeacherPersona.is_active == True,
            ).order_by(TeacherPersona.id.asc()).first()
            if persona:
                teacher_persona_id = persona.id

    learner_profile = db.query(LearnerProfile).filter(
        LearnerProfile.user_id == current_user.id,
        LearnerProfile.world_id == checkpoint.world_id,
    ).order_by(LearnerProfile.id.desc()).first()

    branch_name = (
        payload.branch_name
        if payload and payload.branch_name
        else f"checkpoint-{checkpoint_id}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    )

    new_session = SessionModel(
        course_id=course.id,
        user_id=current_user.id,
        world_id=checkpoint.world_id,
        sage_character_id=int(sage_character_id) if sage_character_id is not None else None,
        traveler_character_id=int(traveler_character_id) if traveler_character_id is not None else None,
        teacher_persona_id=teacher_persona_id,
        learner_profile_id=learner_profile.id if learner_profile else None,
        relationship=relationship,
        parent_checkpoint_id=checkpoint.id,
        branch_name=branch_name,
    )
    db.add(new_session)
    db.flush()

    if source_session is not None:
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == source_session.id
        ).order_by(ChatMessage.id.asc()).limit(checkpoint.message_index).all()
        for msg in messages:
            db.add(
                ChatMessage(
                    session_id=new_session.id,
                    sender_type=msg.sender_type,
                    sender_id=msg.sender_id,
                    content=msg.content,
                    timestamp=msg.timestamp,
                    emotion_analysis=msg.emotion_analysis,
                    used_memory_ids=msg.used_memory_ids,
                )
            )

    db.commit()
    db.refresh(new_session)
    return {
        "session_id": new_session.id,
        "course_id": new_session.course_id,
        "world_id": new_session.world_id,
        "parent_checkpoint_id": new_session.parent_checkpoint_id,
        "branch_name": new_session.branch_name,
    }


@router.get("/worlds/{world_id}/timelines")
async def get_world_timelines(
    world_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_world(db, current_user, world_id)

    sessions = db.query(SessionModel).filter(
        SessionModel.user_id == current_user.id,
        SessionModel.world_id == world_id,
    ).order_by(SessionModel.started_at.asc()).all()
    checkpoints = db.query(Checkpoint).filter(
        Checkpoint.user_id == current_user.id,
        Checkpoint.world_id == world_id,
    ).order_by(Checkpoint.created_at.asc()).all()

    return {
        "world_id": world_id,
        "sessions": [
            {
                "id": s.id,
                "course_id": s.course_id,
                "parent_checkpoint_id": s.parent_checkpoint_id,
                "branch_name": s.branch_name,
                "started_at": s.started_at,
                "ended_at": s.ended_at,
                "relationship_stage": (s.relationship or {}).get("stage", "stranger"),
            }
            for s in sessions
        ],
        "checkpoints": [
            {
                "id": cp.id,
                "session_id": cp.session_id,
                "save_name": cp.save_name,
                "message_index": cp.message_index,
                "created_at": cp.created_at,
            }
            for cp in checkpoints
        ],
    }


@router.get("/worlds/{world_id}/knowledge-graph")
async def get_world_knowledge_graph(
    world_id: int,
    checkpoint_time: str | None = None,
    session_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取世界的知识图谱
    
    注意: 此端点已弃用，知识图谱功能已迁移到 memory_facts。
    当前返回空图谱，待前端适配后移除。
    """
    _get_owned_world(db, current_user, world_id)
    # TODO: P1 #183 - 知识图谱已迁移到 memory_facts，需重新实现或移除此端点
    return {"nodes": [], "edges": [], "links": []}


@router.get("/checkpoints/{checkpoint_id}")
async def get_checkpoint(
    checkpoint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    checkpoint = db.query(Checkpoint).filter(
        Checkpoint.id == checkpoint_id,
        Checkpoint.user_id == current_user.id,
    ).first()
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    return {
        "id": checkpoint.id,
        "world_id": checkpoint.world_id,
        "session_id": checkpoint.session_id,
        "save_name": checkpoint.save_name,
        "message_index": checkpoint.message_index,
        "thumbnail_path": checkpoint.thumbnail_path,
        "created_at": checkpoint.created_at,
        "state": checkpoint.state,
    }


@router.delete("/checkpoints/{checkpoint_id}")
async def delete_checkpoint(
    checkpoint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    checkpoint = db.query(Checkpoint).filter(
        Checkpoint.id == checkpoint_id,
        Checkpoint.user_id == current_user.id,
    ).first()
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    db.delete(checkpoint)
    db.commit()
    return {"message": "Checkpoint deleted"}


def _get_owned_course(
    db: Session,
    current_user: User,
    subject_id: int,
) -> Course:
    course = db.query(Course).join(
        World, Course.world_id == World.id
    ).filter(
        Course.id == subject_id,
        World.user_id == current_user.id,
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


# Legacy save endpoints for frontend compatibility.
@router.post("/save")
async def create_save_legacy(
    payload: LegacySaveCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    course = _get_owned_course(db, current_user, payload.subject_id)
    checkpoint = await create_checkpoint(
        CheckpointCreate(
            world_id=course.world_id,
            session_id=payload.session_id,
            save_name=payload.save_name,
        ),
        db,
        current_user,
    )
    return checkpoint


@router.get("/save", response_model=list[LegacySaveSummary])
async def list_save_legacy(
    subject_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Checkpoint).filter(Checkpoint.user_id == current_user.id)
    session_course_cache: dict[int, int | None] = {}
    if subject_id is not None:
        course = _get_owned_course(db, current_user, subject_id)
        query = query.filter(Checkpoint.world_id == course.world_id)
    checkpoints = query.order_by(Checkpoint.created_at.desc()).all()

    if subject_id is not None:
        filtered: list[Checkpoint] = []
        for checkpoint in checkpoints:
            state = checkpoint.state or {}
            checkpoint_course_id = state.get("course_id")
            if checkpoint_course_id is None and checkpoint.session_id is not None:
                if checkpoint.session_id not in session_course_cache:
                    session_row = db.query(SessionModel).filter(
                        SessionModel.id == checkpoint.session_id,
                        SessionModel.user_id == current_user.id,
                    ).first()
                    session_course_cache[checkpoint.session_id] = (
                        session_row.course_id if session_row else None
                    )
                checkpoint_course_id = session_course_cache[checkpoint.session_id]

            if checkpoint_course_id == subject_id:
                filtered.append(checkpoint)
        checkpoints = filtered

    return [
        LegacySaveSummary(
            id=cp.id,
            save_name=cp.save_name,
            created_at=cp.created_at,
        )
        for cp in checkpoints
    ]


@router.get("/save/{save_id}")
async def get_save_legacy(
    save_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    checkpoint = db.query(Checkpoint).filter(
        Checkpoint.id == save_id,
        Checkpoint.user_id == current_user.id,
    ).first()
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    state = checkpoint.state or {}
    relationship = state.get("relationship") or models_module._default_relationship()
    relationship_stage = relationship.get("stage", "stranger")
    expression = state.get("expression", "default")

    subject_id = state.get("course_id")
    if subject_id is None and checkpoint.session_id is not None:
        session_row = db.query(SessionModel).filter(
            SessionModel.id == checkpoint.session_id,
            SessionModel.user_id == current_user.id,
        ).first()
        if session_row:
            subject_id = session_row.course_id

    chat_history = []
    if checkpoint.session_id is not None:
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == checkpoint.session_id
        ).order_by(ChatMessage.id.asc()).limit(checkpoint.message_index).all()
        chat_history = [
            {
                "id": m.id,
                "sender_type": m.sender_type,
                "content": m.content,
            }
            for m in messages
        ]

    return {
        "id": checkpoint.id,
        "save_name": checkpoint.save_name,
        "created_at": checkpoint.created_at,
        "data": {
            "relationship_stage": relationship_stage,
            "expression": expression,
            "chat_history": chat_history,
            "session_meta": {"subject_id": subject_id},
        },
    }


@router.delete("/save/{save_id}")
async def delete_save_legacy(
    save_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await delete_checkpoint(save_id, db, current_user)
