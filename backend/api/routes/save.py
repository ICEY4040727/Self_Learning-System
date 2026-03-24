from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json
import os
from backend.db.database import get_db
from backend.api.routes.auth import get_current_user
from backend.models.models import User, Save, Session as SessionModel, ChatMessage, Subject, TeacherPersona, LearnerProfile
from backend.core.config import get_settings

router = APIRouter()
settings = get_settings()


class SaveCreate(BaseModel):
    subject_id: int
    save_name: str
    session_id: Optional[int] = None


class SaveResponse(BaseModel):
    id: int
    save_name: str
    created_at: datetime

    class Config:
        from_attributes = True


# Create save
@router.post("/save", response_model=SaveResponse)
async def create_save(
    save_data: SaveCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    subject = db.query(Subject).filter(
        Subject.id == save_data.subject_id,
        Subject.tenant_id == current_user.tenant_id
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    session = None
    if save_data.session_id:
        session = db.query(SessionModel).filter(
            SessionModel.id == save_data.session_id,
            SessionModel.user_id == current_user.id
        ).first()

    # Gather save data
    save_content = {
        "session_meta": {
            "relationship_stage": session.relationship_stage if session else "stranger",
            "teacher_persona_id": session.teacher_persona_id if session else None,
            "subject_id": save_data.subject_id
        },
        "chat_history": [],
        "progress": {},
        "learner_profile_snapshot": None,
        "memory_ids": []
    }

    # Get chat history
    if session:
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id
        ).order_by(ChatMessage.timestamp).all()

        save_content["chat_history"] = [
            {
                "sender_type": m.sender_type,
                "content": m.content,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None
            }
            for m in messages
        ]

    # Create save directory if not exists
    save_dir = os.path.join(settings.save_directory, str(current_user.id))
    os.makedirs(save_dir, exist_ok=True)

    # Write save file
    file_name = f"{save_data.save_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    file_path = os.path.join(save_dir, file_name)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(save_content, f, ensure_ascii=False, indent=2)

    # Create save record
    db_save = Save(
        user_id=current_user.id,
        subject_id=save_data.subject_id,
        session_id=save_data.session_id,
        save_name=save_data.save_name,
        file_path=file_path,
        memory_ids=save_content["memory_ids"]
    )
    db.add(db_save)
    db.commit()
    db.refresh(db_save)

    return db_save


# Get saves list
@router.get("/save", response_model=List[SaveResponse])
async def get_saves(
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Save).filter(Save.user_id == current_user.id)
    if subject_id:
        query = query.filter(Save.subject_id == subject_id)
    return query.order_by(Save.created_at.desc()).all()


# Get save by id
@router.get("/save/{save_id}")
async def get_save(
    save_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    save = db.query(Save).filter(
        Save.id == save_id,
        Save.user_id == current_user.id
    ).first()
    if not save:
        raise HTTPException(status_code=404, detail="Save not found")

    # Read save file
    if not os.path.exists(save.file_path):
        raise HTTPException(status_code=404, detail="Save file not found")

    with open(save.file_path, 'r', encoding='utf-8') as f:
        save_data = json.load(f)

    return {
        "id": save.id,
        "save_name": save.save_name,
        "created_at": save.created_at,
        "data": save_data
    }


# Delete save
@router.delete("/save/{save_id}")
async def delete_save(
    save_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    save = db.query(Save).filter(
        Save.id == save_id,
        Save.user_id == current_user.id
    ).first()
    if not save:
        raise HTTPException(status_code=404, detail="Save not found")

    # Delete file
    if os.path.exists(save.file_path):
        os.remove(save.file_path)

    # Delete record
    db.delete(save)
    db.commit()

    return {"message": "Save deleted"}