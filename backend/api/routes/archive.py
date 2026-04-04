from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.routes.auth import get_current_user
from backend.db.database import get_db
from backend.models.models import (
    Character,
    Course,
    FSRSState,
    LearnerProfile,
    LearningDiary,
    ProgressTracking,
    TeacherPersona,
    User,
    World,
    WorldCharacter,
)
from backend.services import spaced_repetition

router = APIRouter()


# Pydantic Schemas
class CharacterCreate(BaseModel):
    name: str
    type: str = "sage"
    avatar: str | None = None
    personality: str | None = None
    background: str | None = None
    speech_style: str | None = None
    sprites: dict | None = None


class CharacterResponse(CharacterCreate):
    id: int

    class Config:
        from_attributes = True


class WorldCreate(BaseModel):
    name: str
    description: str | None = None
    scenes: dict | None = None


class WorldResponse(WorldCreate):
    id: int
    user_id: int

    class Config:
        from_attributes = True


class WorldCharacterCreate(BaseModel):
    character_id: int
    role: str = Field(..., pattern=r"^(sage|traveler)$")
    is_primary: bool = False


class WorldCharacterResponse(BaseModel):
    id: int
    world_id: int
    character_id: int
    role: str
    is_primary: bool
    character_name: str | None = None

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
    world_id: int
    profile: dict | None = None


class LearnerProfileResponse(LearnerProfileCreate):
    id: int
    user_id: int

    class Config:
        from_attributes = True


class CourseCreate(BaseModel):
    world_id: int
    name: str
    description: str | None = None
    target_level: str | None = None


class CourseResponse(CourseCreate):
    id: int

    class Config:
        from_attributes = True


class SubjectLegacyCreate(BaseModel):
    character_id: int
    name: str
    description: str | None = None
    target_level: str | None = None


class LessonPlanCreate(BaseModel):
    course_id: int
    content: str


class LessonPlanResponse(LessonPlanCreate):
    id: int

    class Config:
        from_attributes = True


class LearningDiaryCreate(BaseModel):
    course_id: int
    date: datetime
    content: str
    reflection: str | None = None


class LearningDiaryResponse(LearningDiaryCreate):
    id: int
    user_id: int

    class Config:
        from_attributes = True


class ProgressTrackingCreate(BaseModel):
    course_id: int
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
        Character.user_id == current_user.id
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
        Character.user_id == current_user.id
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
        Character.user_id == current_user.id
    ).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    db.delete(character)
    db.commit()
    return {"message": "Character deleted"}


# World endpoints
@router.post("/worlds", response_model=WorldResponse)
def create_world(
    world: WorldCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_world = World(
        user_id=current_user.id,
        name=world.name,
        description=world.description,
        scenes=world.scenes or {},
    )
    db.add(db_world)
    db.commit()
    db.refresh(db_world)
    return db_world


@router.get("/worlds", response_model=list[WorldResponse])
def get_worlds(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(World)
        .filter(World.user_id == current_user.id)
        .order_by(World.created_at.desc())
        .all()
    )


@router.get("/worlds/{world_id}", response_model=WorldResponse)
def get_world(
    world_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    world = db.query(World).filter(
        World.id == world_id,
        World.user_id == current_user.id,
    ).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")
    return world


@router.put("/worlds/{world_id}", response_model=WorldResponse)
def update_world(
    world_id: int,
    world: WorldCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_world = db.query(World).filter(
        World.id == world_id,
        World.user_id == current_user.id,
    ).first()
    if not db_world:
        raise HTTPException(status_code=404, detail="World not found")

    db_world.name = world.name
    db_world.description = world.description
    db_world.scenes = world.scenes or {}
    db.commit()
    db.refresh(db_world)
    return db_world


@router.delete("/worlds/{world_id}")
def delete_world(
    world_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    world = db.query(World).filter(
        World.id == world_id,
        World.user_id == current_user.id,
    ).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")
    db.delete(world)
    db.commit()
    return {"message": "World deleted"}


# WorldCharacter endpoints
@router.post("/worlds/{world_id}/characters", response_model=WorldCharacterResponse)
def create_world_character(
    world_id: int,
    wc: WorldCharacterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    world = db.query(World).filter(
        World.id == world_id,
        World.user_id == current_user.id,
    ).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    character = db.query(Character).filter(
        Character.id == wc.character_id,
        Character.user_id == current_user.id,
    ).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    existing = db.query(WorldCharacter).filter(
        WorldCharacter.world_id == world_id,
        WorldCharacter.character_id == wc.character_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Character already bound to this world")

    db_wc = WorldCharacter(
        world_id=world_id,
        character_id=wc.character_id,
        role=wc.role,
        is_primary=wc.is_primary,
    )
    db.add(db_wc)
    db.commit()
    db.refresh(db_wc)
    return WorldCharacterResponse(
        id=db_wc.id,
        world_id=db_wc.world_id,
        character_id=db_wc.character_id,
        role=db_wc.role,
        is_primary=db_wc.is_primary,
        character_name=character.name,
    )


@router.get("/worlds/{world_id}/characters", response_model=list[WorldCharacterResponse])
def get_world_characters(
    world_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    world = db.query(World).filter(
        World.id == world_id,
        World.user_id == current_user.id,
    ).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    links = (
        db.query(WorldCharacter)
        .filter(WorldCharacter.world_id == world_id)
        .all()
    )
    result = []
    for link in links:
        char = db.query(Character).filter(Character.id == link.character_id).first()
        result.append(WorldCharacterResponse(
            id=link.id,
            world_id=link.world_id,
            character_id=link.character_id,
            role=link.role,
            is_primary=link.is_primary,
            character_name=char.name if char else None,
        ))
    return result


@router.delete("/worlds/{world_id}/characters/{character_id}")
def delete_world_character(
    world_id: int,
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    world = db.query(World).filter(
        World.id == world_id,
        World.user_id == current_user.id,
    ).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    link = db.query(WorldCharacter).filter(
        WorldCharacter.world_id == world_id,
        WorldCharacter.character_id == character_id,
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="WorldCharacter binding not found")

    db.delete(link)
    db.commit()
    return {"message": "Character unbound from world"}


# Character sprite upload
ALLOWED_EXPRESSIONS = {"default", "happy", "thinking", "concerned"}
ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB


@router.post("/characters/{character_id}/sprites")
async def upload_sprites(
    character_id: int,
    files: list[UploadFile],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload character expression sprites. Filenames must be default/happy/thinking/concerned."""
    from pathlib import Path

    # Verify ownership
    character = db.query(Character).filter(
        Character.id == character_id,
        Character.user_id == current_user.id,
    ).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Prepare storage directory
    static_base = Path(__file__).resolve().parents[2] / "static" / "characters" / str(character_id)
    static_base.mkdir(parents=True, exist_ok=True)

    sprites = dict(character.sprites or {})

    for file in files:
        # Extract expression name from filename (e.g. "happy.png" → "happy")
        name_stem = Path(file.filename or "").stem
        if name_stem not in ALLOWED_EXPRESSIONS:
            raise HTTPException(
                status_code=422,
                detail=f"文件名 '{file.filename}' 无效，允许的表情名：{', '.join(ALLOWED_EXPRESSIONS)}"
            )

        # Validate content type
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=422,
                detail=f"文件类型 '{file.content_type}' 不支持，允许：png, jpeg, webp"
            )

        # Read and check size
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"文件 '{file.filename}' 超过 2MB 限制"
            )

        # Save file
        ext = Path(file.filename or "").suffix or ".png"
        save_path = static_base / f"{name_stem}{ext}"
        save_path.write_bytes(content)

        # Update sprites dict
        sprites[name_stem] = f"/static/characters/{character_id}/{name_stem}{ext}"

    # Write to DB
    character.sprites = sprites
    db.commit()
    db.refresh(character)

    return {"sprites": sprites}


# Teacher Persona endpoints
@router.post("/teacher_persona", response_model=TeacherPersonaResponse)
def create_teacher_persona(
    persona: TeacherPersonaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify character ownership
    char = db.query(Character).filter(
        Character.id == persona.character_id,
        Character.user_id == current_user.id,
    ).first()
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")

    db_persona = TeacherPersona(
        **persona.model_dump()
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
    query = db.query(TeacherPersona).filter(TeacherPersona.character_id.in_(db.query(Character.id).filter(Character.user_id == current_user.id)))
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
        TeacherPersona.character_id.in_(db.query(Character.id).filter(Character.user_id == current_user.id))
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
        TeacherPersona.character_id.in_(db.query(Character.id).filter(Character.user_id == current_user.id))
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
        TeacherPersona.character_id.in_(db.query(Character.id).filter(Character.user_id == current_user.id))
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
    world = db.query(World).filter(
        World.id == profile.world_id,
        World.user_id == current_user.id,
    ).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    db_profile = LearnerProfile(
        user_id=current_user.id,
        world_id=profile.world_id,
        profile=profile.profile or {},
    )
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile


@router.get("/learner_profile", response_model=list[LearnerProfileResponse])
def get_learner_profiles(
    world_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(LearnerProfile).filter(
        LearnerProfile.user_id == current_user.id
    )
    if world_id:
        query = query.filter(LearnerProfile.world_id == world_id)
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
        LearnerProfile.user_id == current_user.id
    ).first()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Learner profile not found")

    world = db.query(World).filter(
        World.id == profile.world_id,
        World.user_id == current_user.id,
    ).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    db_profile.world_id = profile.world_id
    db_profile.profile = profile.profile or {}

    db.commit()
    db.refresh(db_profile)
    return db_profile


# Course endpoints
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


@router.delete("/courses/{course_id}")
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
    return {"message": "Course deleted"}


def _resolve_or_create_world_for_character(
    db: Session,
    current_user: User,
    character_id: int,
) -> int:
    character = db.query(Character).filter(
        Character.id == character_id,
        Character.user_id == current_user.id,
    ).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    link = db.query(WorldCharacter).join(
        World, WorldCharacter.world_id == World.id
    ).filter(
        WorldCharacter.character_id == character_id,
        World.user_id == current_user.id,
    ).order_by(
        WorldCharacter.is_primary.desc(),
        WorldCharacter.id.asc(),
    ).first()
    if link:
        return link.world_id

    world = World(
        user_id=current_user.id,
        name=f"{character.name} World",
        description=f"Auto-created world for {character.name}",
        scenes={},
    )
    db.add(world)
    db.flush()
    db.add(
        WorldCharacter(
            world_id=world.id,
            character_id=character.id,
            role="sage",
            is_primary=True,
        )
    )
    db.commit()
    return world.id


# Legacy subject endpoints for frontend compatibility.
@router.post("/subjects", response_model=CourseResponse)
def create_subject_legacy(
    payload: SubjectLegacyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    world_id = _resolve_or_create_world_for_character(db, current_user, payload.character_id)
    db_course = Course(
        world_id=world_id,
        name=payload.name,
        description=payload.description,
        target_level=payload.target_level,
    )
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course


@router.get("/subjects", response_model=list[CourseResponse])
def get_subjects_legacy(
    character_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Course).join(
        World, Course.world_id == World.id
    ).filter(
        World.user_id == current_user.id
    )
    if character_id is not None:
        query = query.join(
            WorldCharacter, WorldCharacter.world_id == Course.world_id
        ).filter(
            WorldCharacter.character_id == character_id
        )
    return query.distinct().all()


@router.get("/subjects/{subject_id}", response_model=CourseResponse)
def get_subject_legacy(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_course(subject_id, db, current_user)


@router.put("/subjects/{subject_id}", response_model=CourseResponse)
def update_subject_legacy(
    subject_id: int,
    payload: SubjectLegacyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_course = db.query(Course).join(
        World, Course.world_id == World.id
    ).filter(
        Course.id == subject_id,
        World.user_id == current_user.id,
    ).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")

    world_id = _resolve_or_create_world_for_character(db, current_user, payload.character_id)
    db_course.world_id = world_id
    db_course.name = payload.name
    db_course.description = payload.description
    db_course.target_level = payload.target_level
    db.commit()
    db.refresh(db_course)
    return db_course


@router.delete("/subjects/{subject_id}")
def delete_subject_legacy(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return delete_course(subject_id, db, current_user)


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


# Progress Tracking endpoints
@router.post("/progress", response_model=ProgressTrackingResponse)
def create_progress(
    progress: ProgressTrackingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = db.query(Course).join(World, Course.world_id == World.id).filter(
        Course.id == progress.course_id,
        World.user_id == current_user.id,
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

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
    course_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(ProgressTracking).join(Course, ProgressTracking.course_id == Course.id).join(
        World, Course.world_id == World.id
    ).filter(
        ProgressTracking.user_id == current_user.id,
        World.user_id == current_user.id,
    )
    if course_id:
        query = query.filter(ProgressTracking.course_id == course_id)
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
    db_progress = db.query(ProgressTracking).join(Course, ProgressTracking.course_id == Course.id).join(
        World, Course.world_id == World.id
    ).filter(
        ProgressTracking.id == progress_id,
        ProgressTracking.user_id == current_user.id,
        World.user_id == current_user.id,
    ).first()
    if not db_progress:
        raise HTTPException(status_code=404, detail="Progress not found")

    course = db.query(Course).filter(Course.id == db_progress.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    fsrs_state_row = db.query(FSRSState).filter(
        FSRSState.world_id == course.world_id,
        FSRSState.concept_id == db_progress.topic,
    ).first()

    existing_fsrs_state = None
    if fsrs_state_row:
        existing_fsrs_state = {
            "difficulty": fsrs_state_row.difficulty,
            "stability": fsrs_state_row.stability,
            "last_review": fsrs_state_row.last_review,
            "due": fsrs_state_row.next_review,
            "reps": fsrs_state_row.reps,
        }

    result = spaced_repetition.review(existing_fsrs_state, req.rating)

    db_progress.last_review = result["last_review"]
    db_progress.next_review = result["due"]
    db_progress.mastery_level = result["mastery_level"]

    fsrs_payload = result["fsrs_state"]
    if fsrs_state_row is None:
        fsrs_state_row = FSRSState(
            world_id=course.world_id,
            concept_id=db_progress.topic,
        )
        db.add(fsrs_state_row)

    fsrs_state_row.difficulty = fsrs_payload.get("difficulty")
    fsrs_state_row.stability = fsrs_payload.get("stability")
    fsrs_state_row.reps = fsrs_payload.get("reps") or 0
    fsrs_state_row.last_review = result["last_review"]
    fsrs_state_row.next_review = result["due"]

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
    course_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get topics that are due for review (next_review <= now)."""
    now = datetime.now(UTC)
    query = db.query(ProgressTracking).join(Course, ProgressTracking.course_id == Course.id).join(
        World, Course.world_id == World.id
    ).filter(
        ProgressTracking.user_id == current_user.id,
        ProgressTracking.next_review <= now,
        World.user_id == current_user.id,
    )
    if course_id:
        query = query.filter(ProgressTracking.course_id == course_id)
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


PERSONA_GENERATE_PROMPT = """你是一个角色设计师。根据用户的描述，为一个教学系统中的"知者"（教师角色）生成人格设定。

要求：
- 输出 JSON：{{"system_prompt_template": "...", "traits": ["...", "..."], "name_suggestion": "..."}}
- system_prompt_template：2-4 句话，只描述角色的身份背景、性格特征、说话风格
- 不要写任何教学方法（系统会自动添加苏格拉底教学法指令）
- 不要写"你是一位教师"这类泛化描述，要有具体的角色特色
- traits：3-5 个性格标签，如 ["温和", "反问", "哲学思维"]
- name_suggestion：根据描述推荐一个角色名

用户描述：{description}"""

# Simple in-memory cooldown (user_id → last_generate_time)
_generate_cooldowns: dict[int, float] = {}
_COOLDOWN_SECONDS = 30


@router.post("/persona/generate", response_model=PersonaGenerateResponse)
async def generate_persona(
    req: PersonaGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    """Use LLM to generate a teacher persona from a natural language description."""
    import json
    import re
    import time

    from backend.core.security import decrypt_api_key
    from backend.services.llm.adapter import get_llm_adapter

    # Cooldown check
    now = time.time()
    last = _generate_cooldowns.get(current_user.id, 0)
    if now - last < _COOLDOWN_SECONDS:
        remaining = int(_COOLDOWN_SECONDS - (now - last))
        raise HTTPException(status_code=429, detail=f"请 {remaining} 秒后再试")
    _generate_cooldowns[current_user.id] = now

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
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=500, detail="AI 生成失败，请重试或使用预设模板") from e
