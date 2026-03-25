from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from backend.db.database import get_db
from backend.api.routes.auth import get_current_user
from backend.models.models import User, Session as SessionModel, ChatMessage, TeacherPersona, LearnerProfile, Subject
from backend.services.learning_engine import learning_engine
from backend.core.security import decrypt_api_key

router = APIRouter()


# Chat Request/Response models
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    type: str  # text, tool_request, choice
    reply: str
    choices: Optional[List[str]] = None
    emotion: Optional[dict] = None
    relationship_stage: Optional[str] = None


class ToolConfirmRequest(BaseModel):
    tool: str
    query: str
    reason: str


# Start learning session
@router.post("/subjects/{subject_id}/start")
async def start_learning(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    subject = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.tenant_id == current_user.tenant_id
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    # Reuse existing active session if available
    existing = db.query(SessionModel).filter(
        SessionModel.subject_id == subject_id,
        SessionModel.user_id == current_user.id,
        SessionModel.ended_at == None
    ).order_by(SessionModel.started_at.desc()).first()

    if existing:
        teacher_persona = None
        if existing.teacher_persona_id:
            teacher_persona = db.query(TeacherPersona).filter(
                TeacherPersona.id == existing.teacher_persona_id
            ).first()
        return {
            "session_id": existing.id,
            "teacher_persona": teacher_persona.name if teacher_persona else None,
            "subject": subject.name,
            "relationship_stage": existing.relationship_stage,
        }

    # Get active teacher persona
    teacher_persona = db.query(TeacherPersona).filter(
        TeacherPersona.character_id == subject.character_id,
        TeacherPersona.is_active == True
    ).first()

    # Get learner profile for this subject
    learner_profile = db.query(LearnerProfile).filter(
        LearnerProfile.user_id == current_user.id,
        LearnerProfile.subject_id == subject_id,
    ).first()

    # Create new session
    db_session = SessionModel(
        tenant_id=current_user.tenant_id,
        subject_id=subject_id,
        user_id=current_user.id,
        system_prompt=teacher_persona.system_prompt_template if teacher_persona else None,
        teacher_persona_id=teacher_persona.id if teacher_persona else None,
        learner_profile_id=learner_profile.id if learner_profile else None,
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    return {
        "session_id": db_session.id,
        "teacher_persona": teacher_persona.name if teacher_persona else None,
        "subject": subject.name
    }


# Send chat message
@router.post("/subjects/{subject_id}/chat", response_model=ChatResponse)
async def send_message(
    subject_id: int,
    chat_request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get active session for this subject
    db_session = db.query(SessionModel).filter(
        SessionModel.subject_id == subject_id,
        SessionModel.user_id == current_user.id,
        SessionModel.ended_at == None
    ).order_by(SessionModel.started_at.desc()).first()

    if not db_session:
        # Auto-start a new session
        start_result = await start_learning(subject_id, db, current_user)
        # Get the newly created session
        db_session = db.query(SessionModel).filter(
            SessionModel.subject_id == subject_id,
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
        provider=provider
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

    return ChatResponse(
        type=result.get("type", "text"),
        reply=result.get("reply", ""),
        emotion=result.get("emotion"),
        relationship_stage=result.get("relationship_stage")
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

    session.ended_at = datetime.utcnow()
    db.commit()

    return {"message": "Session ended"}


# Get chat history
@router.get("/sessions/{session_id}/history")
async def get_history(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(SessionModel).filter(
        SessionModel.user_id == current_user.id
    )
    if subject_id:
        query = query.filter(SessionModel.subject_id == subject_id)

    sessions = query.order_by(SessionModel.started_at.desc()).all()
    return [
        {
            "id": s.id,
            "started_at": s.started_at,
            "ended_at": s.ended_at,
            "relationship_stage": s.relationship_stage,
            "subject_name": s.subject.name if s.subject else None,
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