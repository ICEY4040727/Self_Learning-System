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
from backend.models.models import Course, LearningDiary, User, World


router = APIRouter()

class LearningDiaryCreate(BaseModel):
    course_id: int
    date: datetime
    content: str
    reflection: str | None = None


class LearningDiaryResponse(LearningDiaryCreate):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)

# Learning Diary endpoints
@router.post("/learning_diary", response_model=LearningDiaryResponse)
def create_learning_diary(
    diary: LearningDiaryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = db.query(Course).join(World, Course.world_id == World.id).filter(
        Course.id == diary.course_id,
        World.user_id == current_user.id,
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    db_diary = LearningDiary(
        **diary.model_dump(),
        user_id=current_user.id
    )
    db.add(db_diary)
    db.commit()
    db.refresh(db_diary)
    return db_diary


@router.get("/learning_diary", response_model=list[LearningDiaryResponse])
def get_learning_diaries(
    course_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(LearningDiary).join(Course, LearningDiary.course_id == Course.id).join(
        World, Course.world_id == World.id
    ).filter(
        LearningDiary.user_id == current_user.id,
        World.user_id == current_user.id,
    )
    if course_id:
        query = query.filter(LearningDiary.course_id == course_id)
    return query.order_by(LearningDiary.date.desc()).all()
