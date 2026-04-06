from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.routes.auth import get_current_user
from backend.core.security import decrypt_api_key
from backend.db.database import get_db
from backend.models.models import (
    Character,
    ChatMessage,
    Course,
    LearnerProfile,
    TeacherPersona,
    User,
    World,
    WorldCharacter,
    _default_relationship,
)
from backend.models.models import Session as SessionModel
from backend.services.learning_engine import learning_engine

router = APIRouter()


# Chat Request/Response models
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)


class ChatResponse(BaseModel):
    type: str  # text, tool_request, choice
    reply: str
    choices: list[str] | None = None
    emotion: dict | None = None
    relationship_stage: str | None = None
    relationship: dict | None = None
    relationship_events: list[dict] | None = None
    expression_hint: str | None = None  # "happy", "thinking", "concerned", "default"


EXPRESSION_MAP = {
    "curiosity": "thinking",
    "confusion": "concerned",
    "frustration": "concerned",
    "excitement": "happy",
    "satisfaction": "happy",
    "boredom": "default",
    "anxiety": "concerned",
    "neutral": "default",
}


GREETINGS = {
    "stranger": "你好，我是{name}。很高兴认识你！今天想学点什么呢？",
    "acquaintance": "嗨，又见面了。今天想继续上次的话题吗？",
    "friend": "来了来了！今天状态怎么样？",
    "mentor": "准备好挑战更深的问题了吗？",
    "partner": "老朋友，我们继续探索吧。",
}


def _get_greeting(stage: str, persona_name: str | None) -> str:
    template = GREETINGS.get(stage, GREETINGS["stranger"])
    return template.format(name=persona_name or "老师")


class ToolConfirmRequest(BaseModel):
    tool: str
    query: str
    reason: str


# Start learning session
@router.post("/courses/{course_id}/start")
async def start_learning(
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

    # Reuse existing active session if available
    existing = db.query(SessionModel).filter(
        SessionModel.course_id == course_id,
        SessionModel.user_id == current_user.id,
        SessionModel.ended_at == None
    ).order_by(SessionModel.started_at.desc()).first()

    if existing:
        teacher_persona = None
        sage_character = None
        traveler_character = None
        if existing.teacher_persona_id:
            teacher_persona = db.query(TeacherPersona).filter(
                TeacherPersona.id == existing.teacher_persona_id
            ).first()
            if teacher_persona:
                sage_character = db.query(Character).filter(Character.id == teacher_persona.character_id).first()
        if existing.sage_character_id and not sage_character:
            sage_character = db.query(Character).filter(Character.id == existing.sage_character_id).first()
        if existing.traveler_character_id:
            traveler_character = db.query(Character).filter(Character.id == existing.traveler_character_id).first()
        relationship = existing.relationship or _default_relationship()
        stage = relationship.get("stage", "stranger")
        return {
            "session_id": existing.id,
            "teacher_persona": teacher_persona.name if teacher_persona else None,
            "course": course.name,
            "relationship_stage": stage,
            "relationship": relationship,
            "greeting": _get_greeting(stage, teacher_persona.name if teacher_persona else None),
            "scenes": course.world.scenes if course.world and course.world.scenes else {},
            "sage_sprites": sage_character.sprites if sage_character else None,
            "traveler_sprites": traveler_character.sprites if traveler_character else None,
            "character_sprites": sage_character.sprites if sage_character else None,
        }

    sage_link = db.query(WorldCharacter).filter(
        WorldCharacter.world_id == course.world_id,
        WorldCharacter.role == "sage",
    ).order_by(WorldCharacter.is_primary.desc(), WorldCharacter.id.asc()).first()
    traveler_link = db.query(WorldCharacter).filter(
        WorldCharacter.world_id == course.world_id,
        WorldCharacter.role == "traveler",
    ).order_by(WorldCharacter.is_primary.desc(), WorldCharacter.id.asc()).first()

    sage_character_id = sage_link.character_id if sage_link else None
    traveler_character_id = traveler_link.character_id if traveler_link else None

    teacher_persona = None
    if sage_character_id is not None:
        teacher_persona = db.query(TeacherPersona).filter(
            TeacherPersona.character_id == sage_character_id,
            TeacherPersona.is_active == True,
        ).first()

    # Get learner profile for this world
    learner_profile = db.query(LearnerProfile).filter(
        LearnerProfile.user_id == current_user.id,
        LearnerProfile.world_id == course.world_id,
    ).first()

    # Create new session
    db_session = SessionModel(
        course_id=course_id,
        user_id=current_user.id,
        world_id=course.world_id,
        sage_character_id=sage_character_id,
        traveler_character_id=traveler_character_id,
        relationship=_default_relationship(),
        system_prompt=teacher_persona.system_prompt_template if teacher_persona else None,
        teacher_persona_id=teacher_persona.id if teacher_persona else None,
        learner_profile_id=learner_profile.id if learner_profile else None,
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    # Get characters for sprites
    sage_character = None
    traveler_character = None
    if sage_character_id is not None:
        sage_character = db.query(Character).filter(Character.id == sage_character_id).first()
    if traveler_character_id is not None:
        traveler_character = db.query(Character).filter(Character.id == traveler_character_id).first()

    return {
        "session_id": db_session.id,
        "teacher_persona": teacher_persona.name if teacher_persona else None,
        "course": course.name,
        "relationship_stage": "stranger",
        "relationship": db_session.relationship,
        "greeting": _get_greeting("stranger", teacher_persona.name if teacher_persona else None),
        "scenes": course.world.scenes if course.world and course.world.scenes else {},
        "sage_sprites": sage_character.sprites if sage_character else None,
        "traveler_sprites": traveler_character.sprites if traveler_character else None,
        "character_sprites": sage_character.sprites if sage_character else None,
    }


# Send chat message
@router.post("/courses/{course_id}/chat", response_model=ChatResponse)
async def send_message(
    course_id: int,
    chat_request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get active session for this course
    db_session = db.query(SessionModel).filter(
        SessionModel.course_id == course_id,
        SessionModel.user_id == current_user.id,
        SessionModel.ended_at == None
    ).order_by(SessionModel.started_at.desc()).first()

    if not db_session:
        # Auto-start a new session
        await start_learning(course_id, db, current_user)
        # Get the newly created session
        db_session = db.query(SessionModel).filter(
            SessionModel.course_id == course_id,
            SessionModel.user_id == current_user.id,
            SessionModel.ended_at == None
        ).order_by(SessionModel.started_at.desc()).first()

    if not db_session:
        raise HTTPException(status_code=500, detail="Failed to create session")

    # Get user's API key and provider
    user_api_key = None
    provider = "claude"
    if current_user.encrypted_api_key:
        user_api_key = decrypt_api_key(current_user.encrypted_api_key)
    if current_user.default_provider:
        provider = current_user.default_provider

    # Process message through LearningEngine
    # Note: LearningEngine handles session updates, we handle ChatMessage storage
    result = await learning_engine.process_message(
        session_id=db_session.id,
        user_message=chat_request.message,
        user_api_key=user_api_key,
        provider=provider,
        db=db,
    )

    # Save user message to database
    user_message = ChatMessage(
        session_id=db_session.id,
        sender_type="user",
        sender_id=current_user.id,
        content=chat_request.message,
        emotion_analysis=result.get("emotion"),
        used_memory_ids=result.get("used_memory_ids")
    )
    db.add(user_message)

    # Save teacher response to database
    teacher_message = ChatMessage(
        session_id=db_session.id,
        sender_type="teacher",
        content=result.get("reply", "")
    )
    db.add(teacher_message)
    db.commit()

    emotion_type = result.get("emotion", {}).get("emotion_type", "neutral") if result.get("emotion") else "neutral"
    expression = EXPRESSION_MAP.get(emotion_type, "default")

    return ChatResponse(
        type=result.get("type", "text"),
        reply=result.get("reply", ""),
        emotion=result.get("emotion"),
        relationship_stage=result.get("relationship_stage"),
        relationship=result.get("relationship"),
        relationship_events=result.get("relationship_events"),
        expression_hint=expression,
    )


# Confirm tool call
@router.post("/chat/tool_confirm")
async def confirm_tool(
    tool_request: ToolConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Execute tool and return result
    # This is a placeholder - will integrate actual tool execution
    return {
        "message": "Tool execution placeholder",
        "tool": tool_request.tool,
        "query": tool_request.query
    }


# End learning session
@router.post("/sessions/{session_id}/end")
async def end_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.ended_at = datetime.now(UTC)
    
    # Update LearnerProfile session_count
    if session.learner_profile_id:
        from backend.models.models import LearnerProfile
        learner_profile = db.query(LearnerProfile).filter(
            LearnerProfile.id == session.learner_profile_id
        ).first()
        if learner_profile:
            profile = learner_profile.profile or {}
            profile["session_count"] = profile.get("session_count", 0) + 1
            learner_profile.profile = profile
    
    # Update UserProfile (incremental update)
    from backend.services.user_profile import update_user_profile_after_session_end
    update_user_profile_after_session_end(db, current_user.id, session.world_id)
    
    db.commit()

    return {"message": "Session ended"}


# Get chat history
@router.get("/sessions/{session_id}/history")
async def get_history(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.timestamp).all()

    return [
        {
            "id": m.id,
            "sender_type": m.sender_type,
            "content": m.content,
            "timestamp": m.timestamp
        }
        for m in messages
    ]


# List user's sessions
@router.get("/sessions")
async def list_sessions(
    course_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(SessionModel).filter(
        SessionModel.user_id == current_user.id
    )
    if course_id:
        query = query.filter(SessionModel.course_id == course_id)

    sessions = query.order_by(SessionModel.started_at.desc()).all()
    return [
        {
            "id": s.id,
            "started_at": s.started_at,
            "ended_at": s.ended_at,
            "relationship_stage": s.relationship_stage,
            "course_name": s.course.name if s.course else None,
        }
        for s in sessions
    ]


# Get emotion trajectory for a session
@router.get("/sessions/{session_id}/emotion_trajectory")
async def get_emotion_trajectory(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Return emotion data for all user messages in a session."""
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id,
        ChatMessage.sender_type == "user",
        ChatMessage.emotion_analysis != None
    ).order_by(ChatMessage.timestamp).all()

    return [
        {
            "index": i + 1,
            "timestamp": m.timestamp,
            "emotion_type": m.emotion_analysis.get("emotion_type", "neutral"),
            "valence": m.emotion_analysis.get("valence", 0.5),
            "arousal": m.emotion_analysis.get("arousal", 0.5),
            "confidence": m.emotion_analysis.get("confidence", 0.0),
        }
        for i, m in enumerate(messages)
    ]


# ============================================
# User Profile - 用户全局画像
# ============================================

class RefreshUserProfileRequest(BaseModel):
    """手动刷新用户画像请求"""
    force: bool = Field(default=False, description="是否强制刷新（忽略缓存）")


@router.get("/user/profile", tags=["user"])
def get_user_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取用户全局画像（跨世界特征聚合）
    
    返回数据包括：
    - metacognition_trend: 元认知趋势（MSKT四维度）
    - preference_stability: 偏好稳定性
    - learning_stats: 学习统计
    
    这是懒计算模式：数据超过24小时会自动重新计算
    """
    from backend.services.user_profile import get_user_profile as compute_user_profile
    
    profile = compute_user_profile(db, user.id)
    
    return {
        "success": True,
        "data": profile
    }


@router.post("/user/profile/refresh", tags=["user"])
def refresh_user_profile(
    request: RefreshUserProfileRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    手动刷新用户画像
    
    如果 force=True，忽略缓存强制重新计算
    """
    from backend.services.user_profile import get_or_create_user_profile
    
    user_profile = get_or_create_user_profile(db, user.id)
    
    return {
        "success": True,
        "data": user_profile.profile,
        "computed_at": user_profile.computed_at.isoformat() if user_profile.computed_at else None
    }
