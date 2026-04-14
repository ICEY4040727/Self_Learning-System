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
    MemoryFact,
    ProgressTracking,
    TeacherPersona,
    User,
    World,
)
from backend.models.models import (
    Session as SessionModel,
)
from backend.services.save_file_manager import SaveFileManager

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


class BranchRequest(BaseModel):
    branch_name: str | None = None


# v1.0 #193 存档导入/导出模型
class CheckpointExportData(BaseModel):
    """导出存档数据结构"""
    version: str = "1.0"
    save_name: str
    world_id: int
    session_id: int | None = None
    message_index: int
    created_at: str  # ISO 格式
    stage: str | None = None
    mastery_percent: float | None = None
    preview_text: str | None = None
    session_snapshot: dict | None = None


class CheckpointImportData(BaseModel):
    """导入存档数据结构"""
    version: str = "1.0"
    save_name: str = Field(..., max_length=100)
    world_id: int
    session_id: int | None = None
    message_index: int = 0
    stage: str | None = None
    mastery_percent: float | None = None
    preview_text: str | None = None
    session_snapshot: dict | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_full_save_data(
    db: Session,
    user_id: int,
    checkpoint: Checkpoint,
    db_session: SessionModel | None,
) -> dict:
    """构建完整存档 JSON 数据（Issue #207 v2.0 格式）"""
    state = checkpoint.state or {}
    relationship = state.get("relationship", models_module._default_relationship())

    # Session metadata
    session_meta = {}
    if db_session:
        session_meta = {
            "session_id": db_session.id,
            "course_id": db_session.course_id,
            "world_id": db_session.world_id,
            "sage_character_id": db_session.sage_character_id,
            "traveler_character_id": db_session.traveler_character_id,
            "relationship_stage": (db_session.relationship or {}).get("stage", "stranger"),
            "teacher_persona_id": db_session.teacher_persona_id,
            "learner_profile_id": db_session.learner_profile_id,
        }

    # Chat history
    chat_history = []
    if checkpoint.session_id is not None:
        messages = _get_session_messages(db, checkpoint.session_id, limit=checkpoint.message_index)
        chat_history = [
            {
                "sender_type": m.sender_type,
                "content": m.content,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                "emotion_analysis": m.emotion_analysis,
            }
            for m in messages
        ]

    # Learner profile snapshot
    learner_profile_snapshot = {}
    course_id = state.get("course_id")
    if course_id:
        lp = (
            db.query(LearnerProfile)
            .filter(
                LearnerProfile.user_id == user_id,
                LearnerProfile.world_id == checkpoint.world_id,
            )
            .order_by(LearnerProfile.id.desc())
            .first()
        )
        if lp:
            learner_profile_snapshot = lp.profile or {}

    # Memory snapshot
    memory_snapshot: dict = {"memory_ids": [], "facts": []}
    if db_session and db_session.sage_character_id:
        facts = (
            db.query(MemoryFact)
            .filter(MemoryFact.character_id == db_session.sage_character_id)
            .order_by(MemoryFact.salience.desc())
            .limit(50)
            .all()
        )
        memory_snapshot["memory_ids"] = [f.id for f in facts]
        memory_snapshot["facts"] = [
            {"id": f.id, "fact_type": f.fact_type, "content": f.content, "salience": f.salience}
            for f in facts
        ]

    # Progress snapshot
    progress_snapshot: dict = {"topics": []}
    if course_id:
        progress_list = (
            db.query(ProgressTracking)
            .filter(
                ProgressTracking.course_id == int(course_id),
                ProgressTracking.user_id == user_id,
            )
            .all()
        )
        progress_snapshot["topics"] = [
            {"topic": p.topic, "mastery_level": p.mastery_level}
            for p in progress_list
        ]

    return SaveFileManager.build_save_data(
        checkpoint_id=checkpoint.id,
        session_meta=session_meta,
        relationship=relationship,
        chat_history=chat_history,
        learner_profile_snapshot=learner_profile_snapshot,
        memory_snapshot=memory_snapshot,
        progress_snapshot=progress_snapshot,
    )


def _get_checkpoint_state(checkpoint: Checkpoint) -> dict:
    """读取存档状态：优先从文件读取，fallback 到 DB state 字段"""
    if checkpoint.file_path:
        file_data = SaveFileManager.read_save_file(checkpoint.file_path)
        if file_data is not None:
            return file_data
    return checkpoint.state or {}


def _build_checkpoint_response(cp: Checkpoint, db: Session, user_id: int) -> CheckpointResponse:
    """Build CheckpointResponse with extended fields."""
    state = cp.state or {}
    relationship = state.get("relationship", {})

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

    date = cp.created_at.strftime("%Y-%m-%d %H:%M") if cp.created_at else None

    mastery = None
    course_id = state.get("course_id")
    if course_id:
        progress_list = db.query(ProgressTracking).filter(
            ProgressTracking.course_id == course_id,
            ProgressTracking.user_id == user_id,
        ).all()
        if progress_list:
            total = sum(p.mastery_level for p in progress_list)
            mastery = total / len(progress_list) / 100.0

    preview = None
    if cp.session_id:
        last_msgs = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == cp.session_id)
            .order_by(ChatMessage.id.desc())
            .limit(2)
            .all()
        )
        if last_msgs:
            preview = last_msgs[0].content[:100]

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


def _get_session_messages(db: Session, session_id: int, limit: int | None = None) -> list:
    """查询 session 的聊天记录（按 id 升序）"""
    q = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.id.asc())
    if limit is not None:
        q = q.limit(limit)
    return q.all()


def _count_session_messages(db: Session, session_id: int) -> int:
    """统计 session 的消息数量"""
    return int(db.query(ChatMessage).filter(ChatMessage.session_id == session_id).count())


def _get_owned_world(db: Session, current_user: User, world_id: int) -> World:
    world = db.query(World).filter(
        World.id == world_id,
        World.user_id == current_user.id,
    ).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")
    return world


def _get_owned_course(db: Session, current_user: User, subject_id: int) -> Course:
    course = (
        db.query(Course)
        .join(World, Course.world_id == World.id)
        .filter(Course.id == subject_id, World.user_id == current_user.id)
        .first()
    )
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


# ---------------------------------------------------------------------------
# Checkpoint CRUD
# ---------------------------------------------------------------------------

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
        message_index = _count_session_messages(db, db_session.id) if db_session else 0

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
    db.flush()  # flush to get checkpoint.id for filename

    # Issue #207: 写入完整存档到 JSON 文件
    save_data = _build_full_save_data(db, current_user.id, checkpoint, db_session)
    file_path = SaveFileManager.write_save_file(current_user.id, checkpoint.id, save_data)
    file_size = SaveFileManager.get_file_size(file_path)
    checkpoint.file_path = file_path
    checkpoint.file_size_bytes = file_size

    db.commit()
    db.refresh(checkpoint)
    return _build_checkpoint_response(checkpoint, db, current_user.id)


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


@router.get("/worlds/{world_id}/checkpoints", response_model=list[CheckpointResponse])
async def list_world_checkpoints(
    world_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_world(db, current_user, world_id)
    return await list_checkpoints(world_id, db, current_user)


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

    # Issue #207: 优先从文件读取完整状态
    full_state = _get_checkpoint_state(checkpoint)
    return {
        "id": checkpoint.id,
        "world_id": checkpoint.world_id,
        "session_id": checkpoint.session_id,
        "save_name": checkpoint.save_name,
        "message_index": checkpoint.message_index,
        "thumbnail_path": checkpoint.thumbnail_path,
        "created_at": checkpoint.created_at,
        "state": full_state,
        "file_path": checkpoint.file_path,
        "file_size_bytes": checkpoint.file_size_bytes,
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

    # Issue #207: 同步删除存档文件
    if checkpoint.file_path:
        SaveFileManager.delete_save_file(checkpoint.file_path)

    db.delete(checkpoint)
    db.commit()
    return {"message": "Checkpoint deleted"}


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
                TeacherPersona.is_active == True,  # noqa: E712
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
        for msg in _get_session_messages(db, source_session.id, limit=checkpoint.message_index):
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

    sessions = (
        db.query(SessionModel)
        .filter(
            SessionModel.user_id == current_user.id,
            SessionModel.world_id == world_id,
        )
        .order_by(SessionModel.started_at.asc())
        .all()
    )
    checkpoints = (
        db.query(Checkpoint)
        .filter(
            Checkpoint.user_id == current_user.id,
            Checkpoint.world_id == world_id,
        )
        .order_by(Checkpoint.created_at.asc())
        .all()
    )

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


# ---------------------------------------------------------------------------
# Export / Import (Issue #207: export now returns file content directly)
# ---------------------------------------------------------------------------

@router.get("/checkpoints/{checkpoint_id}/export")
async def export_checkpoint(
    checkpoint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """导出存档为 JSON — 优先从文件读取 v2.0 格式"""
    checkpoint = db.query(Checkpoint).filter(
        Checkpoint.id == checkpoint_id,
        Checkpoint.user_id == current_user.id,
    ).first()
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    full_state = _get_checkpoint_state(checkpoint)

    # 如果有 v2.0 文件数据，直接返回
    if checkpoint.file_path and full_state.get("version") == "2.0":
        return full_state

    # Fallback: 旧格式导出
    session_snapshot = None
    if checkpoint.session_id:
        session = db.query(SessionModel).filter(
            SessionModel.id == checkpoint.session_id
        ).first()
        if session:
            messages = _get_session_messages(db, checkpoint.session_id, limit=checkpoint.message_index)
            session_snapshot = {
                "relationship": session.relationship,
                "course_id": session.course_id,
                "sage_character_id": session.sage_character_id,
                "traveler_character_id": session.traveler_character_id,
                "messages": [
                    {
                        "sender_type": m.sender_type,
                        "content": m.content,
                        "emotion_analysis": m.emotion_analysis,
                    }
                    for m in messages
                ],
            }

    return CheckpointExportData(
        version="1.0",
        save_name=checkpoint.save_name,
        world_id=checkpoint.world_id,
        session_id=checkpoint.session_id,
        message_index=checkpoint.message_index,
        created_at=checkpoint.created_at.isoformat(),
        stage=(checkpoint.state or {}).get("relationship", {}).get("stage"),
        mastery_percent=None,
        preview_text=None,
        session_snapshot=session_snapshot,
    )


@router.post("/checkpoints/import")
async def import_checkpoint(
    payload: CheckpointImportData,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从 JSON 导入存档"""
    world = db.query(World).filter(
        World.id == payload.world_id,
        World.user_id == current_user.id,
    ).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    state = {
        "relationship": {
            "stage": payload.stage or "stranger",
            "dimensions": {},
        },
    }
    if payload.session_snapshot:
        state.update({
            "course_id": payload.session_snapshot.get("course_id"),
            "sage_character_id": payload.session_snapshot.get("sage_character_id"),
            "traveler_character_id": payload.session_snapshot.get("traveler_character_id"),
        })

    checkpoint = Checkpoint(
        user_id=current_user.id,
        world_id=payload.world_id,
        session_id=payload.session_id,
        save_name=payload.save_name,
        message_index=payload.message_index,
        state=state,
    )
    db.add(checkpoint)
    db.flush()

    # Issue #207: 为导入的存档也生成文件
    save_data = _build_full_save_data(db, current_user.id, checkpoint, None)
    # 如果 payload 有 session_snapshot，覆盖 chat_history
    if payload.session_snapshot and payload.session_snapshot.get("messages"):
        save_data["chat_history"] = payload.session_snapshot["messages"]
    save_data["relationship"] = state.get("relationship", {})

    file_path = SaveFileManager.write_save_file(current_user.id, checkpoint.id, save_data)
    file_size = SaveFileManager.get_file_size(file_path)
    checkpoint.file_path = file_path
    checkpoint.file_size_bytes = file_size

    db.commit()
    db.refresh(checkpoint)

    return {
        "id": checkpoint.id,
        "save_name": checkpoint.save_name,
        "created_at": checkpoint.created_at,
        "file_path": checkpoint.file_path,
    }
