from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.routes.auth import get_current_user
from backend.db.database import get_db
from backend.models.models import (
    Character,
    LearnerProfile,
    LearningDiary,
    ProgressTracking,
    Subject,
    TeacherPersona,
    User,
)
from backend.services import spaced_repetition

router = APIRouter()


# Pydantic Schemas
class CharacterCreate(BaseModel):
    name: str
    avatar: str | None = None
    personality: str | None = None
    background: str | None = None
    speech_style: str | None = None
    sprites: dict | None = None


class CharacterResponse(CharacterCreate):
    id: int

    class Config:
        from_attributes = True


class TeacherPersonaCreate(BaseModel):
    character_id: int
    name: str
    version: str = "1.0"
    traits: dict | None = None
    system_prompt_template: str | None = None
    is_active: bool = False


class TeacherPersonaResponse(TeacherPersonaCreate):
    id: int

    class Config:
        from_attributes = True


class LearnerProfileCreate(BaseModel):
    subject_id: int | None = None
    learning_style: dict | None = None
    cognitive_traits: dict | None = None
    emotional_traits: dict | None = None
    knowledge_graph: dict | None = None


class LearnerProfileResponse(LearnerProfileCreate):
    id: int
    user_id: int

    class Config:
        from_attributes = True


class SubjectCreate(BaseModel):
    character_id: int
    name: str
    description: str | None = None
    target_level: str | None = None
    scene_background: str | None = None


class SubjectResponse(SubjectCreate):
    id: int

    class Config:
        from_attributes = True


class LessonPlanCreate(BaseModel):
    subject_id: int
    content: str


class LessonPlanResponse(LessonPlanCreate):
    id: int

    class Config:
        from_attributes = True


class LearningDiaryCreate(BaseModel):
    subject_id: int
    date: datetime
    content: str
    reflection: str | None = None


class LearningDiaryResponse(LearningDiaryCreate):
    id: int
    user_id: int

    class Config:
        from_attributes = True


class ProgressTrackingCreate(BaseModel):
    subject_id: int
    topic: str
    mastery_level: int = 0
    next_review: datetime | None = None


class ProgressTrackingResponse(ProgressTrackingCreate):
    id: int
    user_id: int
    last_review: datetime | None = None

    class Config:
        from_attributes = True


# Character endpoints
@router.post("/character", response_model=CharacterResponse)
def create_character(
    character: CharacterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_character = Character(
        **character.model_dump(),
        tenant_id=current_user.tenant_id,
        user_id=current_user.id
    )
    db.add(db_character)
    db.commit()
    db.refresh(db_character)
    return db_character


@router.get("/character", response_model=list[CharacterResponse])
def get_characters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Character).filter(
        Character.tenant_id == current_user.tenant_id,
        Character.user_id == current_user.id
    ).all()


@router.get("/character/{character_id}", response_model=CharacterResponse)
def get_character(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    character = db.query(Character).filter(
        Character.id == character_id,
        Character.tenant_id == current_user.tenant_id
    ).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


@router.put("/character/{character_id}", response_model=CharacterResponse)
def update_character(
    character_id: int,
    character: CharacterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_character = db.query(Character).filter(
        Character.id == character_id,
        Character.tenant_id == current_user.tenant_id
    ).first()
    if not db_character:
        raise HTTPException(status_code=404, detail="Character not found")

    for key, value in character.model_dump().items():
        setattr(db_character, key, value)

    db.commit()
    db.refresh(db_character)
    return db_character


@router.delete("/character/{character_id}")
def delete_character(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    character = db.query(Character).filter(
        Character.id == character_id,
        Character.tenant_id == current_user.tenant_id
    ).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    db.delete(character)
    db.commit()
    return {"message": "Character deleted"}


# Teacher Persona endpoints
@router.post("/teacher_persona", response_model=TeacherPersonaResponse)
def create_teacher_persona(
    persona: TeacherPersonaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_persona = TeacherPersona(
        **persona.model_dump(),
        tenant_id=current_user.tenant_id
    )
    db.add(db_persona)
    db.commit()
    db.refresh(db_persona)
    return db_persona


@router.get("/teacher_persona", response_model=list[TeacherPersonaResponse])
def get_teacher_personas(
    character_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(TeacherPersona).filter(TeacherPersona.tenant_id == current_user.tenant_id)
    if character_id:
        query = query.filter(TeacherPersona.character_id == character_id)
    return query.all()


@router.put("/teacher_persona/{persona_id}/activate")
def activate_teacher_persona(
    persona_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    persona = db.query(TeacherPersona).filter(
        TeacherPersona.id == persona_id,
        TeacherPersona.tenant_id == current_user.tenant_id
    ).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Teacher persona not found")

    # Deactivate all other personas for this character
    db.query(TeacherPersona).filter(
        TeacherPersona.character_id == persona.character_id,
        TeacherPersona.id != persona_id
    ).update({"is_active": False})

    persona.is_active = True
    db.commit()
    return {"message": "Teacher persona activated"}


@router.put("/teacher_persona/{persona_id}", response_model=TeacherPersonaResponse)
def update_teacher_persona(
    persona_id: int,
    persona: TeacherPersonaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_persona = db.query(TeacherPersona).filter(
        TeacherPersona.id == persona_id,
        TeacherPersona.tenant_id == current_user.tenant_id
    ).first()
    if not db_persona:
        raise HTTPException(status_code=404, detail="Teacher persona not found")

    for key, value in persona.model_dump().items():
        setattr(db_persona, key, value)

    db.commit()
    db.refresh(db_persona)
    return db_persona


@router.delete("/teacher_persona/{persona_id}")
def delete_teacher_persona(
    persona_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    persona = db.query(TeacherPersona).filter(
        TeacherPersona.id == persona_id,
        TeacherPersona.tenant_id == current_user.tenant_id
    ).first()
    if not persona:
        raise HTTPException(status_code=404, detail="Teacher persona not found")

    db.delete(persona)
    db.commit()
    return {"message": "Teacher persona deleted"}


# Learner Profile endpoints
@router.post("/learner_profile", response_model=LearnerProfileResponse)
def create_learner_profile(
    profile: LearnerProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_profile = LearnerProfile(
        **profile.model_dump(),
        tenant_id=current_user.tenant_id,
        user_id=current_user.id
    )
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile


@router.get("/learner_profile", response_model=list[LearnerProfileResponse])
def get_learner_profiles(
    subject_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(LearnerProfile).filter(
        LearnerProfile.tenant_id == current_user.tenant_id,
        LearnerProfile.user_id == current_user.id
    )
    if subject_id:
        query = query.filter(LearnerProfile.subject_id == subject_id)
    return query.all()


@router.put("/learner_profile/{profile_id}", response_model=LearnerProfileResponse)
def update_learner_profile(
    profile_id: int,
    profile: LearnerProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_profile = db.query(LearnerProfile).filter(
        LearnerProfile.id == profile_id,
        LearnerProfile.tenant_id == current_user.tenant_id
    ).first()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Learner profile not found")

    for key, value in profile.model_dump().items():
        setattr(db_profile, key, value)

    db.commit()
    db.refresh(db_profile)
    return db_profile


# Subject endpoints
@router.post("/subjects", response_model=SubjectResponse)
def create_subject(
    subject: SubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_subject = Subject(
        **subject.model_dump(),
        tenant_id=current_user.tenant_id
    )
    db.add(db_subject)
    db.commit()
    db.refresh(db_subject)
    return db_subject


@router.get("/subjects", response_model=list[SubjectResponse])
def get_subjects(
    character_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Subject).filter(Subject.tenant_id == current_user.tenant_id)
    if character_id:
        query = query.filter(Subject.character_id == character_id)
    return query.all()


@router.get("/subjects/{subject_id}", response_model=SubjectResponse)
def get_subject(
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
    return subject


@router.put("/subjects/{subject_id}", response_model=SubjectResponse)
def update_subject(
    subject_id: int,
    subject: SubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_subject = db.query(Subject).filter(
        Subject.id == subject_id,
        Subject.tenant_id == current_user.tenant_id
    ).first()
    if not db_subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    for key, value in subject.model_dump().items():
        setattr(db_subject, key, value)

    db.commit()
    db.refresh(db_subject)
    return db_subject


@router.delete("/subjects/{subject_id}")
def delete_subject(
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

    db.delete(subject)
    db.commit()
    return {"message": "Subject deleted"}


# Learning Diary endpoints
@router.post("/learning_diary", response_model=LearningDiaryResponse)
def create_learning_diary(
    diary: LearningDiaryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
    subject_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(LearningDiary).filter(LearningDiary.user_id == current_user.id)
    if subject_id:
        query = query.filter(LearningDiary.subject_id == subject_id)
    return query.order_by(LearningDiary.date.desc()).all()


# Progress Tracking endpoints
@router.post("/progress", response_model=ProgressTrackingResponse)
def create_progress(
    progress: ProgressTrackingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_progress = ProgressTracking(
        **progress.model_dump(),
        user_id=current_user.id
    )
    db.add(db_progress)
    db.commit()
    db.refresh(db_progress)
    return db_progress


@router.get("/progress", response_model=list[ProgressTrackingResponse])
def get_progress(
    subject_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(ProgressTracking).filter(ProgressTracking.user_id == current_user.id)
    if subject_id:
        query = query.filter(ProgressTracking.subject_id == subject_id)
    return query.all()


@router.put("/progress/{progress_id}", response_model=ProgressTrackingResponse)
def update_progress(
    progress_id: int,
    progress: ProgressTrackingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_progress = db.query(ProgressTracking).filter(
        ProgressTracking.id == progress_id,
        ProgressTracking.user_id == current_user.id
    ).first()
    if not db_progress:
        raise HTTPException(status_code=404, detail="Progress not found")

    for key, value in progress.model_dump(exclude_unset=True).items():
        setattr(db_progress, key, value)

    db.commit()
    db.refresh(db_progress)
    return db_progress


# Review endpoint – FSRS spaced repetition
class ReviewRequest(BaseModel):
    rating: int = Field(ge=1, le=4)  # 1=Again, 2=Hard, 3=Good, 4=Easy


class ReviewResponse(BaseModel):
    id: int
    topic: str
    mastery_level: int
    retrievability: float
    next_review: datetime | None = None
    last_review: datetime | None = None


@router.post("/progress/{progress_id}/review", response_model=ReviewResponse)
def review_progress(
    progress_id: int,
    req: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a review for a topic and compute next review date via FSRS."""
    db_progress = db.query(ProgressTracking).filter(
        ProgressTracking.id == progress_id,
        ProgressTracking.user_id == current_user.id,
    ).first()
    if not db_progress:
        raise HTTPException(status_code=404, detail="Progress not found")

    result = spaced_repetition.review(db_progress.fsrs_state, req.rating)

    db_progress.fsrs_state = result["fsrs_state"]
    db_progress.last_review = result["last_review"]
    db_progress.next_review = result["due"]
    db_progress.mastery_level = result["mastery_level"]

    db.commit()
    db.refresh(db_progress)

    return ReviewResponse(
        id=db_progress.id,
        topic=db_progress.topic,
        mastery_level=db_progress.mastery_level,
        retrievability=result["retrievability"],
        next_review=db_progress.next_review,
        last_review=db_progress.last_review,
    )


@router.get("/progress/due", response_model=list[ProgressTrackingResponse])
def get_due_reviews(
    subject_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get topics that are due for review (next_review <= now)."""
    now = datetime.now(UTC)
    query = db.query(ProgressTracking).filter(
        ProgressTracking.user_id == current_user.id,
        ProgressTracking.next_review <= now,
    )
    if subject_id:
        query = query.filter(ProgressTracking.subject_id == subject_id)
    return query.order_by(ProgressTracking.next_review).all()


# Settings endpoints
class SettingsUpdate(BaseModel):
    default_provider: str | None = None
    api_key: str | None = None


class SettingsResponse(BaseModel):
    default_provider: str | None = None


@router.get("/settings", response_model=SettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return SettingsResponse(
        default_provider=current_user.default_provider
    )


@router.put("/settings")
def update_settings(
    settings: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if settings.default_provider:
        current_user.default_provider = settings.default_provider

    if settings.api_key:
        from backend.core.security import encrypt_api_key
        current_user.encrypted_api_key = encrypt_api_key(settings.api_key)

    db.commit()
    return {"message": "Settings updated"}


# Persona generation endpoint
class PersonaGenerateRequest(BaseModel):
    description: str = Field(..., min_length=5, max_length=500)


class PersonaGenerateResponse(BaseModel):
    system_prompt_template: str
    traits: list[str]
    name_suggestion: str


PERSONA_GENERATE_PROMPT = """\
你是一个教师人格设计师。根据用户的描述，生成一个教师人格配置。

用户描述：{description}

请严格按以下 JSON 格式输出，不要有其他内容：
{{
  "system_prompt_template": "2-3句话描述这位教师的性格、说话风格和教学哲学。注意：不要写具体的教学方法（如苏格拉底式提问），那些会由系统自动附加。只写性格和风格。",
  "traits": ["特质1", "特质2", "特质3", "特质4"],
  "name_suggestion": "一个合适的人格名称"
}}
"""


@router.post("/persona/generate", response_model=PersonaGenerateResponse)
async def generate_persona(
    req: PersonaGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    """Use LLM to generate a teacher persona from a natural language description."""
    import json
    import re

    from backend.core.security import decrypt_api_key
    from backend.services.llm.adapter import get_llm_adapter

    user_api_key = None
    provider = current_user.default_provider or "claude"
    if current_user.encrypted_api_key:
        user_api_key = decrypt_api_key(current_user.encrypted_api_key)

    if not user_api_key:
        raise HTTPException(status_code=400, detail="请先在设置页配置 API Key")

    adapter = get_llm_adapter(provider)
    prompt = PERSONA_GENERATE_PROMPT.format(description=req.description)

    response = await adapter.chat(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="你是人格设计师，只输出 JSON。",
        user_api_key=user_api_key,
    )

    # Parse JSON from response
    try:
        json_match = re.search(r"\{[\s\S]*\}", response)
        if not json_match:
            raise ValueError("No JSON found")
        data = json.loads(json_match.group())
        return PersonaGenerateResponse(
            system_prompt_template=data.get("system_prompt_template", ""),
            traits=data.get("traits", []),
            name_suggestion=data.get("name_suggestion", "自定义人格"),
        )
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=500, detail="AI 生成失败，请重试或使用预设模板")
