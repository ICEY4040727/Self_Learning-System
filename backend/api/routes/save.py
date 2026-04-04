from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.routes.auth import get_current_user
from backend.db.database import get_db
from backend.models import models as models_module
from backend.models.models import (
    Checkpoint,
    ChatMessage,
    Session as SessionModel,
    User,
    World,
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

    class Config:
        from_attributes = True


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


@router.get("/checkpoints", response_model=list[CheckpointResponse])
async def list_checkpoints(
    world_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Checkpoint).filter(Checkpoint.user_id == current_user.id)
    if world_id is not None:
        query = query.filter(Checkpoint.world_id == world_id)
    return query.order_by(Checkpoint.created_at.desc()).all()


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
