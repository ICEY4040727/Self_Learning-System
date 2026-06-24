from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from backend.api.routes.auth import get_current_user
from backend.core.conflicts.user_llm_settings import raise_settings_conflict_http
from backend.db.database import get_db
from backend.models import models as models_module
from backend.models.models import (
    Character,
    ChatMessage,
    Course,
    LearnerProfile,
    LearningDiary,
    MemoryFact,
    ProgressTracking,
    User,
    World,
    WorldCharacter,
)
from backend.services.character_llm_settings import normalize_character_llm_settings
from backend.services.user_llm_settings import (
    get_effective_llm_config,
    lock_user_for_update,
    normalize_base_url,
    serialize_provider_settings,
    update_generation_params,
    update_provider_settings,
)

router = APIRouter()


# =============================================================================
# 命名规范说明:
#
# traveler vs learner 的区分:
#   - traveler: 游戏角色层 (Character.type="traveler", WorldCharacter.role="traveler")
#              玩家在游戏世界中的化身，关联故事/叙事
#   - learner:  学习追踪层 (LearnerProfile, learner_profile_id)
#              记录用户的学习状态、偏好、元认知等信息
#
# 示例:
#   - Session.traveler_character_id: 玩家扮演的旅人角色
#   - Session.learner_profile_id: 用户的学习档案
# =============================================================================

# World AI generate cooldown
_world_gen_cooldowns: dict[int, float] = {}
_WORLD_GEN_COOLDOWN = 10  # seconds

WORLD_GENERATE_PROMPT = """你是一个世界构建师。用户描述了他们想要的学习世界，请生成世界壳建议。

用户描述：{description}

请严格按 JSON 格式输出：
{{
  "name_suggestion": "世界名称（4-10字）",
  "description": "世界说明（60-160字，描述这个世界为什么适合长期学习）",
  "background_picture": "默认背景图路径，例如 /themes/academy.jpg"
}}

注意：
- 世界是用于学习的长期容器，不是剧情简介
- background_picture 只返回单个默认背景图路径
- 直接输出 JSON，不要任何推理、思考、解释或额外内容
- 不要输出思考过程，只输出最终 JSON"""


class WorldGenerateRequest(BaseModel):
    description: str = Field(..., min_length=5, max_length=500)
    inspiration_type: str = "freeform"  # freeform | style_reference


class WorldGenerateResponse(BaseModel):
    name_suggestion: str
    description: str
    background_picture: str | None = None


# Phase 1.5 DD1: PERSONA_TEMPLATES 保留用于提示词构建，不再用于 TeacherPersona 创建
# Issue #15/#213: 同时支持中文名和英文 key（前端传英文 key 如 'socrates'）
PERSONA_TEMPLATES = {
    "socrates":      ["耐心", "追问型", "启发型"],
    "苏格拉底型":     ["耐心", "追问型", "启发型"],
    "einstein":      ["鼓励型", "探索型", "启发型"],
    "爱因斯坦型":     ["鼓励型", "探索型", "启发型"],
    "aristotle":     ["严谨", "体系化", "百科全书"],
    "亚里士多德型":   ["严谨", "体系化", "百科全书"],
    "sunzi":         ["策略性", "举一反三", "引导型"],
    "孙子型":         ["策略性", "举一反三", "引导型"],
    "custom":        ["耐心", "启发型"],
    "默认":          ["耐心", "启发型"],
}


# Pydantic Schemas
class CharacterCreate(BaseModel):
    name: str
    # type: "sage" | "traveler" - 导师或旅人角色
    type: str = "sage"
    avatar: str | None = None
    personality: str | None = None
    background: str | None = None
    speech_style: str | None = None
    greeting: str | None = None
    tags: list[str] | None = None
    title: str | None = None
    sprites: dict | None = None
    llm_settings: dict | None = None
    system_prompt_template: str | None = None
    template_name: str | None = "默认"  # 人格模板名称（用于生成 traits）
    # 性格滑块值 (Phase 1 新增)
    # 格式: {"strictness": 5, "pace": 5, "questioning": 5, "warmth": 5, "humor": 5}
    traits: dict | None = None
    # Phase 1.5 DD1: is_active 替代 TeacherPersona.is_active
    is_active: bool = True


class CharacterUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    avatar: str | None = None
    personality: str | None = None
    background: str | None = None
    speech_style: str | None = None
    greeting: str | None = None
    tags: list[str] | None = None
    title: str | None = None
    sprites: dict | None = None
    llm_settings: dict | None = None
    system_prompt_template: str | None = None
    template_name: str | None = None
    traits: dict | None = None
    is_active: bool | None = None


class CharacterResponse(CharacterCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)


class CharacterStatsResponse(BaseModel):
    total_characters: int
    sage_count: int
    traveler_count: int
    active_worlds: int


class CharacterLevelupRequest(BaseModel):
    experience_points: int = 0


class CharacterLevelupResponse(BaseModel):
    id: int
    level: int
    experience_points: int
    message: str


class SageInfo(BaseModel):
    id: int
    name: str
    title: str
    symbol: str
    color: str
    accentColor: str
    type: str  # "sage" or "traveler"


class WorldCreate(BaseModel):
    name: str
    description: str | None = None
    background_picture: str | None = None

    model_config = ConfigDict(extra="forbid")


class WorldUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    background_picture: str | None = None

    model_config = ConfigDict(extra="forbid")


class WorldResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: str | None = None
    background_picture: str | None = None
    sages: list[SageInfo] | None = None
    travelers: list[SageInfo] | None = None
    stageLabel: str | None = None
    relationship: dict | None = None
    courses: list["CourseResponse"] | None = None

    model_config = ConfigDict(from_attributes=True)


def _extract_world_background_picture(world: World) -> str | None:
    return world.background_picture


class WorldCharacterCreate(BaseModel):
    character_id: int
    role: str = Field(..., pattern=r"^(sage|traveler)$")
    is_primary: bool = False
    world_title: str | None = None
    world_background: str | None = None
    relationship_seed: str | None = None
    world_greeting: str | None = None


class WorldCharacterUpdate(BaseModel):
    world_title: str | None = None
    world_background: str | None = None
    relationship_seed: str | None = None
    world_greeting: str | None = None


class WorldCharacterContextGenerateRequest(BaseModel):
    role: Literal["sage", "traveler"] | None = None
    seed_hint: str | None = Field(default=None, max_length=500)


class WorldCharacterContextGenerateResponse(BaseModel):
    world_title: str
    world_background: str
    relationship_seed: str
    world_greeting: str | None = None
    warnings: list[str] | None = None


class WorldCharacterResponse(BaseModel):
    id: int
    world_id: int
    character_id: int
    role: str
    is_primary: bool
    world_title: str | None = None
    world_background: str | None = None
    relationship_seed: str | None = None
    world_greeting: str | None = None
    character_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


WORLD_CHARACTER_CONTEXT_GENERATE_PROMPT = """你是一个学习世界的角色上下文设计师。

请根据“世界设定”和“角色本体”，生成这个角色进入当前世界后的绑定上下文。

角色在当前世界中的职责：{role}

世界设定：
{world_context}

角色本体：
{character_context}

用户额外提示：
{seed_hint}

请严格输出 JSON，不要 markdown 代码块：
{{
  "world_title": "该世界内的身份或称号，4-14字",
  "world_background": "该角色在这个世界里的背景，80-160字，只写当前世界，不改写角色本体",
  "relationship_seed": "该角色与学习者/导师在这个世界的相识或关系起点，30-80字",
  "world_greeting": "如果该角色是 sage，写一句首次进入课程时的开场白；如果是 traveler，可以写 null"
}}

规则：
- 这是学习系统，不是普通小说设定；背景必须服务于后续学习对话。
- 不要把世界背景写回角色本体；只写“当前世界里”的身份、经历和相识前提。
- sage 的 world_greeting 要自然、短，像对唯一学生说话，不要说“大家好”。
- traveler 不是 LLM 发言角色，world_greeting 可以为 null。
- 不要输出解释、推理过程或额外字段。
"""


def _world_context_for_character_generation(world: World) -> str:
    parts = [f"世界名称: {world.name}"]
    if world.description:
        parts.append(f"世界简介: {world.description}")

    return "\n".join(parts)


def _character_context_for_world_generation(character: Character) -> str:
    parts = [
        f"角色名: {character.name}",
        f"角色类型: {character.type}",
    ]
    if character.title:
        parts.append(f"全局称号: {character.title}")
    if character.personality:
        parts.append(f"人格/学习风格: {character.personality}")
    if character.tags:
        tags = "、".join(character.tags) if isinstance(character.tags, list) else str(character.tags)
        parts.append(f"标签: {tags}")
    if character.background:
        parts.append(f"旧全局背景，仅作参考: {character.background}")
    if character.greeting:
        parts.append(f"全局兜底开场白: {character.greeting}")
    return "\n".join(parts)


# Phase 1.5 DD1: TeacherPersona 相关类已删除，人格数据直接存储在 Character 模型中


class LearnerProfileCreate(BaseModel):
    world_id: int
    profile: dict | None = None


class LearnerProfileResponse(LearnerProfileCreate):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)


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


class LessonPlanCreate(BaseModel):
    course_id: int
    content: str


class LessonPlanResponse(LessonPlanCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)


class LearningDiaryCreate(BaseModel):
    course_id: int
    date: datetime
    content: str
    reflection: str | None = None


class LearningDiaryResponse(LearningDiaryCreate):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class ProgressTrackingCreate(BaseModel):
    course_id: int
    topic: str
    mastery_level: int = 0
    next_review: datetime | None = None


class ProgressTrackingResponse(ProgressTrackingCreate):
    id: int
    user_id: int
    last_review: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# Character endpoints
@router.post("/character", response_model=CharacterResponse)
def create_character(
    character: CharacterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Phase 1.5 DD1: template_name 和 traits 直接存储在 Character 模型中
    template_name = character.template_name
    traits = character.traits
    llm_settings = normalize_character_llm_settings(character.llm_settings)

    # 只传递 Character 模型支持的字段
    # sprites 不能是空列表，必须是 dict 或 None
    sprites = character.sprites
    if isinstance(sprites, list) and len(sprites) == 0:
        sprites = None

    db_character = Character(
        user_id=current_user.id,
        name=character.name,
        type=character.type,
        avatar=character.avatar,
        personality=character.personality,
        background=character.background,
        speech_style=character.speech_style,
        greeting=character.greeting,
        sprites=sprites,
        llm_settings=llm_settings,
        system_prompt_template=character.system_prompt_template,
        title=character.title,
        tags=character.tags,
        # Phase 1.5 DD1: traits 和 template_name 直接存入 Character
        template_name=template_name,
        traits=traits,
        is_active=True,  # 默认激活
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


# Character stats endpoint - MUST be before /character/{character_id} to avoid path conflict
@router.get("/character/stats", response_model=CharacterStatsResponse)
def get_character_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get character statistics for the current user."""
    total = db.query(Character).filter(Character.user_id == current_user.id).count()
    sage_count = db.query(Character).filter(
        Character.user_id == current_user.id,
        Character.type == "sage"
    ).count()
    traveler_count = db.query(Character).filter(
        Character.user_id == current_user.id,
        Character.type == "traveler"
    ).count()
    # Count worlds that have at least one character bound
    active_worlds = db.query(WorldCharacter.world_id).join(
        Character, WorldCharacter.character_id == Character.id
    ).filter(
        Character.user_id == current_user.id
    ).distinct().count()

    return CharacterStatsResponse(
        total_characters=total,
        sage_count=sage_count,
        traveler_count=traveler_count,
        active_worlds=active_worlds,
    )


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
    character: CharacterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_character = db.query(Character).filter(
        Character.id == character_id,
        Character.user_id == current_user.id
    ).first()
    if not db_character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Phase 1.5 DD1: 仅更新显式传入的字段，避免把未提交字段重置为默认值
    data = character.model_dump(exclude_unset=True)
    if "llm_settings" in data:
        data["llm_settings"] = normalize_character_llm_settings(data.get("llm_settings"))
    if "sprites" in data and isinstance(data["sprites"], list) and len(data["sprites"]) == 0:
        data["sprites"] = None
    for key, value in data.items():
        setattr(db_character, key, value)

    db.commit()
    db.refresh(db_character)
    return db_character


@router.delete("/character/{character_id}", status_code=204)
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


# Character avatar upload endpoint
@router.post("/character/{character_id}/avatar")
async def upload_character_avatar(
    character_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload character avatar (single image)."""
    from pathlib import Path

    character = db.query(Character).filter(
        Character.id == character_id,
        Character.user_id == current_user.id,
    ).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"文件类型 '{file.content_type}' 不支持，允许：png, jpeg, webp"
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="文件超过 2MB 限制")

    static_base = Path(__file__).resolve().parents[2] / "static" / "characters" / str(character_id)
    static_base.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "").suffix or ".png"
    avatar_path = static_base / f"avatar{ext}"
    avatar_path.write_bytes(content)

    avatar_url = f"/static/characters/{character_id}/avatar{ext}"
    character.avatar = avatar_url
    db.commit()

    return {"avatar": avatar_url}


# Character levelup endpoint
@router.post("/character/{character_id}/levelup", response_model=CharacterLevelupResponse)
def character_levelup(
    character_id: int,
    req: CharacterLevelupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add experience points and handle levelup for a character."""
    character = db.query(Character).filter(
        Character.id == character_id,
        Character.user_id == current_user.id,
    ).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Initialize experience and level if not present
    current_exp = getattr(character, 'experience_points', 0) or 0
    current_level = getattr(character, 'level', 1) or 1

    # Add experience
    new_exp = current_exp + req.experience_points

    # Calculate level based on experience thresholds
    level_thresholds = [0, 100, 250, 500, 1000]
    new_level = 1
    for i, threshold in enumerate(level_thresholds):
        if new_exp >= threshold:
            new_level = i + 1

    # Update character
    character.experience_points = new_exp
    character.level = new_level
    db.commit()
    db.refresh(character)

    # Generate message
    if new_level > current_level:
        message = f"升级了！当前等级：{new_level}"
    else:
        next_threshold = level_thresholds[new_level] if new_level < len(level_thresholds) else level_thresholds[-1] * 2
        remaining = next_threshold - new_exp
        message = f"经验 +{req.experience_points}，距离下一级还需 {remaining} 点"

    return CharacterLevelupResponse(
        id=character.id,
        level=new_level,
        experience_points=new_exp,
        message=message,
    )


# World endpoints
def _world_character_response(
    link: WorldCharacter,
    character: Character | None = None,
) -> WorldCharacterResponse:
    """Serialize a world-character binding with its world-scoped context."""
    return WorldCharacterResponse(
        id=link.id,
        world_id=link.world_id,
        character_id=link.character_id,
        role=link.role,
        is_primary=link.is_primary,
        world_title=link.world_title,
        world_background=link.world_background,
        relationship_seed=link.relationship_seed,
        world_greeting=link.world_greeting,
        character_name=character.name if character else None,
    )


def _get_world_characters_by_role(db: Session, world_id: int, role: str) -> list[SageInfo]:
    """Get all characters of a given role bound to a world. Primary first."""
    links = db.query(WorldCharacter).filter(
        WorldCharacter.world_id == world_id,
        WorldCharacter.role == role,
    ).order_by(WorldCharacter.is_primary.desc()).all()

    default_color = "#ffd700" if role == "sage" else "#60a5fa"
    default_symbol = "" if role == "sage" else ""

    result = []
    for link in links:
        char = db.query(Character).filter(Character.id == link.character_id).first()
        if char:
            result.append(SageInfo(
                id=char.id,
                name=char.name,
                title=link.world_title or char.title or char.personality or "",
                symbol=char.avatar or default_symbol,
                color=(char.sprites or {}).get("color", default_color),
                accentColor=(char.sprites or {}).get("accentColor", "#fbbf24"),
                type=char.type or role,  # 从 Character 对象获取类型，fallback 到 role
            ))
    return result


def _build_world_response(world: World, db: Session, current_user_id: int = None) -> WorldResponse:
    """Build WorldResponse with sages, stageLabel, relationship data and courses."""
    sages = _get_world_characters_by_role(db, world.id, "sage")
    travelers = _get_world_characters_by_role(db, world.id, "traveler")

    # Get courses for this world with progress and icon
    courses = db.query(Course).filter(Course.world_id == world.id).all()
    course_list = []
    if courses:
        for course in courses:
            progress = None
            icon = ""  # 默认图标

            # 如果提供了 user_id，获取课程进度
            if current_user_id:
                course_progress = db.query(ProgressTracking).filter(
                    ProgressTracking.course_id == course.id,
                    ProgressTracking.user_id == current_user_id
                ).first()
                if course_progress:
                    progress = course_progress.mastery_level / 100.0

            course_list.append(CourseResponse(
                id=course.id,
                world_id=course.world_id,
                name=course.name,
                description=course.description,
                target_level=course.target_level,
                meta=course.meta,  # Phase 1 新增
                progress=progress,
                icon=icon,
            ))
    else:
        course_list = None

    # Try to get relationship stage from the most recent session
    from backend.models.models import Session as SessionModel
    latest_session = db.query(SessionModel).filter(
        SessionModel.world_id == world.id
    ).order_by(SessionModel.started_at.desc()).first()

    stage_label = None
    relationship = None
    if latest_session and latest_session.relationship:
        stage = latest_session.relationship.get("stage", "stranger")
        stage_label = models_module.RELATIONSHIP_STAGE_LABELS.get(stage, stage)
        relationship = latest_session.relationship

    return WorldResponse(
        id=world.id,
        user_id=world.user_id,
        name=world.name,
        description=world.description,
        background_picture=_extract_world_background_picture(world),
        sages=sages if sages else None,
        travelers=travelers if travelers else None,
        stageLabel=stage_label,
        relationship=relationship,
        courses=course_list,
    )


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
        background_picture=(world.background_picture or "").strip() or None,
    )
    db.add(db_world)
    db.flush()
    db.commit()
    db.refresh(db_world)
    return _build_world_response(db_world, db, current_user.id)


@router.get("/worlds", response_model=list[WorldResponse])
def get_worlds(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    worlds = (
        db.query(World)
        .filter(World.user_id == current_user.id)
        .order_by(World.created_at.desc())
        .all()
    )
    return [_build_world_response(w, db, current_user.id) for w in worlds]


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
    return _build_world_response(world, db)


@router.put("/worlds/{world_id}", response_model=WorldResponse)
def update_world(
    world_id: int,
    world: WorldUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_world = db.query(World).filter(
        World.id == world_id,
        World.user_id == current_user.id,
    ).first()
    if not db_world:
        raise HTTPException(status_code=404, detail="World not found")

    data = world.model_dump(exclude_unset=True)
    if "name" in data:
        db_world.name = data["name"]
    if "description" in data:
        db_world.description = data["description"]
    if "background_picture" in data:
        db_world.background_picture = (data["background_picture"] or "").strip() or None
    db.commit()
    db.refresh(db_world)
    return _build_world_response(db_world, db, current_user.id)


@router.delete("/worlds/{world_id}", status_code=204)
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


@router.post("/world/generate", response_model=WorldGenerateResponse)
async def generate_world(
    req: WorldGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    """Use LLM to generate world settings from a natural language description."""
    import json
    import re
    import time

    from backend.services.llm.adapter import get_llm_adapter
    from backend.services.llm.providers import provider_needs_api_key

    # Cooldown
    now = time.time()
    last = _world_gen_cooldowns.get(current_user.id, 0)
    if now - last < _WORLD_GEN_COOLDOWN:
        remaining = int(_WORLD_GEN_COOLDOWN - (now - last))
        raise HTTPException(status_code=429, detail=f"请 {remaining} 秒后再试")
    _world_gen_cooldowns[current_user.id] = now

    config = get_effective_llm_config(current_user)

    if provider_needs_api_key(config.provider) and not config.api_key:
        raise HTTPException(status_code=400, detail="请先在设置页配置 API Key")

    adapter = get_llm_adapter(
        config.provider,
        model=config.model,
        api_key=config.api_key,
        base_url=config.base_url,
    )

    prompt = WORLD_GENERATE_PROMPT.format(description=req.description)

    try:
        response = await adapter.chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="你是世界构建师，只输出合法 JSON。",
            user_api_key=config.api_key,
            max_tokens=4096,
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"AI 服务调用失败，请稍后重试。错误：{str(e)[:200]}",
        ) from e

    try:
        json_match = re.search(r"\{[\s\S]*\}", response)
        if not json_match:
            raise ValueError("No JSON found")
        data = json.loads(json_match.group())

        return WorldGenerateResponse(
            name_suggestion=data.get("name_suggestion", "未命名世界"),
            description=data.get("description", ""),
            background_picture=(data.get("background_picture") or "").strip() or None,
        )
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=422,
            detail=f"AI 生成格式错误，请重试。原始响应：{response[:200]}",
        ) from e


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

    if wc.is_primary:
        db.query(WorldCharacter).filter(
            WorldCharacter.world_id == world_id,
            WorldCharacter.role == wc.role,
            WorldCharacter.is_primary == True,  # noqa: E712
        ).update({"is_primary": False})

    db_wc = WorldCharacter(
        world_id=world_id,
        character_id=wc.character_id,
        role=wc.role,
        is_primary=wc.is_primary,
        world_title=wc.world_title,
        world_background=wc.world_background,
        relationship_seed=wc.relationship_seed,
        world_greeting=wc.world_greeting,
    )
    db.add(db_wc)
    db.commit()
    db.refresh(db_wc)
    return _world_character_response(db_wc, character)


@router.post(
    "/worlds/{world_id}/characters/{character_id}/generate-context",
    response_model=WorldCharacterContextGenerateResponse,
)
async def generate_world_character_context(
    world_id: int,
    character_id: int,
    req: WorldCharacterContextGenerateRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate world-scoped context for binding a character into a world.

    This endpoint is intentionally side-effect free. Callers can preview or
    edit the result, then persist it through the bind/update endpoints.
    """
    import json
    import re

    from backend.services.llm.adapter import get_llm_adapter
    from backend.services.llm.providers import provider_needs_api_key

    world = db.query(World).filter(
        World.id == world_id,
        World.user_id == current_user.id,
    ).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    character = db.query(Character).filter(
        Character.id == character_id,
        Character.user_id == current_user.id,
    ).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    req = req or WorldCharacterContextGenerateRequest()
    existing = db.query(WorldCharacter).filter(
        WorldCharacter.world_id == world_id,
        WorldCharacter.character_id == character_id,
    ).first()
    inferred_role = req.role or (existing.role if existing else None) or character.type or "sage"
    role = inferred_role if inferred_role in ("sage", "traveler") else "sage"

    config = get_effective_llm_config(current_user)
    if provider_needs_api_key(config.provider) and not config.api_key:
        raise HTTPException(status_code=400, detail="请先在设置页配置 API Key")

    adapter = get_llm_adapter(
        config.provider,
        model=config.model,
        api_key=config.api_key,
        base_url=config.base_url,
    )

    prompt = WORLD_CHARACTER_CONTEXT_GENERATE_PROMPT.format(
        role=role,
        world_context=_world_context_for_character_generation(world),
        character_context=_character_context_for_world_generation(character),
        seed_hint=req.seed_hint or "无",
    )

    response = await adapter.chat(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="你是世界角色上下文设计师，只输出合法 JSON。",
        user_api_key=config.api_key,
        temperature=config.temperature,
        max_tokens=min(config.max_tokens or 2048, 800),
    )

    try:
        json_match = re.search(r"\{[\s\S]*\}", response)
        if not json_match:
            raise ValueError("No JSON found")
        data = json.loads(json_match.group())

        warnings: list[str] = []
        world_title = data.get("world_title") or (existing.world_title if existing else None) or character.title
        if not world_title:
            world_title = "知者" if role == "sage" else "旅者"
            warnings.append("AI 未返回 world_title，已使用默认值。")

        world_background = data.get("world_background") or (existing.world_background if existing else None) or character.background
        if not world_background:
            world_background = f"{character.name}进入《{world.name}》，以{world_title}的身份参与学习旅程。"
            warnings.append("AI 未返回 world_background，已使用默认值。")

        relationship_seed = data.get("relationship_seed") or (existing.relationship_seed if existing else None)
        if not relationship_seed:
            relationship_seed = f"{character.name}与学习者在《{world.name}》中初次相遇。"
            warnings.append("AI 未返回 relationship_seed，已使用默认值。")

        world_greeting = data.get("world_greeting")
        if role != "sage":
            world_greeting = None

        return WorldCharacterContextGenerateResponse(
            world_title=str(world_title),
            world_background=str(world_background),
            relationship_seed=str(relationship_seed),
            world_greeting=str(world_greeting) if world_greeting else None,
            warnings=warnings or None,
        )
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=422,
            detail=f"AI 生成格式错误，请重试。原始响应：{response[:200]}",
        ) from e


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
        result.append(_world_character_response(link, char))
    return result


@router.patch("/worlds/{world_id}/characters/{character_id}", response_model=WorldCharacterResponse)
def update_world_character(
    world_id: int,
    character_id: int,
    wc: WorldCharacterUpdate,
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
        Character.id == character_id,
        Character.user_id == current_user.id,
    ).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    link = db.query(WorldCharacter).filter(
        WorldCharacter.world_id == world_id,
        WorldCharacter.character_id == character_id,
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="WorldCharacter binding not found")

    data = wc.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(link, key, value)

    db.commit()
    db.refresh(link)
    return _world_character_response(link, character)


@router.put("/worlds/{world_id}/characters/{character_id}/set-primary", response_model=WorldCharacterResponse)
def set_world_character_primary(
    world_id: int,
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a character as the primary one for its role in a world.

    If the character is not yet bound to the world, the binding is created
    on the fly (defaulting role from the character's own type).
    """
    world = db.query(World).filter(
        World.id == world_id,
        World.user_id == current_user.id,
    ).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    character = db.query(Character).filter(
        Character.id == character_id,
        Character.user_id == current_user.id,
    ).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    link = db.query(WorldCharacter).filter(
        WorldCharacter.world_id == world_id,
        WorldCharacter.character_id == character_id,
    ).first()

    role = link.role if link else (character.type or "sage")
    if role not in ("sage", "traveler"):
        role = "sage"

    # Demote any other primary of the same role.
    db.query(WorldCharacter).filter(
        WorldCharacter.world_id == world_id,
        WorldCharacter.role == role,
        WorldCharacter.is_primary == True,  # noqa: E712
        WorldCharacter.character_id != character_id,
    ).update({"is_primary": False})

    if not link:
        link = WorldCharacter(
            world_id=world_id,
            character_id=character_id,
            role=role,
            is_primary=True,
        )
        db.add(link)
    else:
        link.is_primary = True

    db.commit()
    db.refresh(link)
    return _world_character_response(link, character)


@router.delete("/worlds/{world_id}/characters/{character_id}", status_code=204)
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


# World-scoped learner profile (Phase 2F: frontend expects this route)
@router.get("/worlds/{world_id}/learner_profile")
def get_world_learner_profile(
    world_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the learner profile for a specific world.

    Frontend (CoursePage, Learning) expects this route to return
    { dimension_scores, strengths, weaknesses, learning_stats, last_updated }
    directly, unwrapped from the profile JSON column.
    """
    lp = db.query(LearnerProfile).filter(
        LearnerProfile.user_id == current_user.id,
        LearnerProfile.world_id == world_id,
    ).first()
    if lp is None:
        raise HTTPException(status_code=404, detail="Learner profile not found")

    profile = lp.profile if isinstance(lp.profile, dict) else {}
    return {
        "dimension_scores": profile.get("dimension_scores", {}),
        "strengths": profile.get("strengths", []),
        "weaknesses": profile.get("weaknesses", []),
        "learning_stats": profile.get("learning_stats", {}),
        "last_updated": profile.get("last_updated"),
    }


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
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from backend.services.progress_facade import progress_facade

    course = db.query(Course).join(World, Course.world_id == World.id).filter(
        Course.id == progress.course_id,
        World.user_id == current_user.id,
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    for key, value in progress_facade.progress_compat_headers(progress.course_id).items():
        response.headers[key] = value

    db_progress = progress_facade.create_progress_compat(
        db,
        user_id=current_user.id,
        course_id=progress.course_id,
        topic=progress.topic,
        mastery_level=progress.mastery_level,
        next_review=progress.next_review,
    )
    db.commit()
    if hasattr(db_progress, "__mapper__"):
        db.refresh(db_progress)
    return db_progress


@router.get("/progress", response_model=list[ProgressTrackingResponse])
def get_progress(
    response: Response,
    course_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from backend.services.progress_facade import progress_facade

    for key, value in progress_facade.progress_compat_headers(course_id).items():
        response.headers[key] = value
    if course_id is not None:
        canonical_index = progress_facade.get_canonical_lesson_index(
            db, course_id, current_user.id,
        )
        response.headers["X-Canonical-Current-Lesson-Index"] = str(canonical_index)

    return progress_facade.list_compat_progress_rows(db, current_user.id, course_id)


@router.put("/progress/{progress_id}", response_model=ProgressTrackingResponse)
def update_progress(
    progress_id: int,
    progress: ProgressTrackingCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from backend.services.progress_facade import progress_facade

    for key, value in progress_facade.progress_compat_headers(progress.course_id).items():
        response.headers[key] = value

    try:
        db_progress = progress_facade.update_progress_compat(
            db,
            progress_id=progress_id,
            user_id=current_user.id,
            course_id=progress.course_id,
            topic=progress.topic,
            mastery_level=progress.mastery_level,
            next_review=progress.next_review,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Progress not found")

    db.commit()
    if hasattr(db_progress, "__mapper__"):
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
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a review for a topic and compute next review date via FSRS."""
    from backend.services.progress_facade import progress_facade

    response.headers["Deprecation"] = "true"

    try:
        result = progress_facade.record_review_compat(
            db,
            progress_id=progress_id,
            user_id=current_user.id,
            rating=req.rating,
        )
    except LookupError as exc:
        detail = str(exc) or "Progress not found"
        raise HTTPException(status_code=404, detail=detail)

    db.commit()

    return ReviewResponse(
        id=result["id"],
        topic=result["topic"],
        mastery_level=result["mastery_level"],
        retrievability=result["retrievability"],
        next_review=result["next_review"],
        last_review=result["last_review"],
    )


@router.get("/progress/due", response_model=list[ProgressTrackingResponse])
def get_due_reviews(
    response: Response,
    course_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get topics that are due for review (next_review <= now)."""
    from backend.services.progress_facade import progress_facade

    for key, value in progress_facade.progress_compat_headers(course_id).items():
        response.headers[key] = value

    return progress_facade.list_due_reviews_compat(db, current_user.id, course_id)


# Settings endpoints
class SettingsUpdate(BaseModel):
    version: int = Field(..., ge=0)
    default_provider: str | None = None
    api_key: str | None = None
    clear_api_key: bool = False
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=200000)
    model: str | None = None
    base_url: str | None = None


class SettingsResponse(BaseModel):
    version: int
    default_provider: str | None = None
    api_key_configured: bool = False
    temperature: float | None = None
    max_tokens: int | None = None
    model: str | None = None
    base_url: str | None = None
    provider_settings: dict[str, dict[str, str | bool | None]] = Field(default_factory=dict)


class SettingsTestRequest(BaseModel):
    default_provider: str | None = None
    api_key: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=200000)
    model: str | None = None
    base_url: str | None = None


class SettingsTestResponse(BaseModel):
    ok: bool
    provider: str
    model: str | None = None
    base_url: str | None = None
    message: str


class SettingsModelsRequest(BaseModel):
    default_provider: str | None = None
    api_key: str | None = None
    model: str | None = None
    base_url: str | None = None


class SettingsModelsResponse(BaseModel):
    provider: str
    base_url: str | None = None
    source: str
    models: list[str] = Field(default_factory=list)
    message: str | None = None


def _normalize_settings_base_url(provider: str, base_url: str | None) -> str | None:
    return normalize_base_url(provider, base_url)


def _fallback_settings_models(provider: str) -> list[str]:
    from backend.services.llm.models import (
        CLAUDE_MODELS,
        OPENAI_COMPATIBLE_MODELS,
        OPENAI_MODELS,
        OLLAMA_MODELS,
    )

    if provider == "claude":
        return list(CLAUDE_MODELS.keys())
    if provider == "openai":
        return list(OPENAI_MODELS.keys())
    if provider == "local":
        return list(OLLAMA_MODELS.keys())
    return list(OPENAI_COMPATIBLE_MODELS.keys())


@router.get("/settings", response_model=SettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    active = get_effective_llm_config(current_user)
    return SettingsResponse(
        version=current_user.version,
        default_provider=active.provider,
        api_key_configured=active.api_key_configured,
        temperature=active.temperature,
        max_tokens=active.max_tokens,
        model=active.model,
        base_url=active.base_url,
        provider_settings=serialize_provider_settings(current_user),
    )


@router.put("/settings")
def update_settings(
    settings: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = lock_user_for_update(db, current_user.id)

    if user.version != settings.version:
        raise_settings_conflict_http(
            user_id=user.id,
            expected_version=settings.version,
            current_version=user.version,
        )

    target_provider = settings.default_provider or user.default_provider or "claude"

    try:
        with db.no_autoflush:
            update_generation_params(
                user,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )

            update_provider_settings(
                user,
                target_provider,
                api_key=settings.api_key,
                clear_api_key=settings.clear_api_key,
                model=settings.model,
                base_url=settings.base_url,
            )

        db.commit()
        db.refresh(user)
    except StaleDataError:
        db.rollback()
        raise_settings_conflict_http(
            user_id=user.id,
            expected_version=settings.version,
            via="commit_race",
        )

    return {"message": "Settings updated", "version": user.version}


@router.post("/settings/test-connection", response_model=SettingsTestResponse)
async def test_settings_connection(
    settings: SettingsTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = get_effective_llm_config(
        current_user,
        provider=settings.default_provider,
        api_key=settings.api_key,
        model=settings.model,
        base_url=settings.base_url,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )

    from backend.services.llm.providers import provider_needs_api_key
    if provider_needs_api_key(config.provider) and not config.api_key:
        return SettingsTestResponse(
            ok=False,
            provider=config.provider,
            model=config.model,
            base_url=config.base_url,
            message="API Key is not configured for this provider.",
        )

    try:
        from backend.services.llm.manager import get_llm_manager

        adapter = get_llm_manager().get_adapter(
            provider=config.provider,
            model=config.model,
            api_key=config.api_key,
            base_url=config.base_url,
        )
        await adapter.chat(
            messages=[{"role": "user", "content": "ping"}],
            system_prompt="Reply with a short ok.",
            user_api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=min(config.max_tokens, 32),
        )
    except Exception as exc:
        return SettingsTestResponse(
            ok=False,
            provider=config.provider,
            model=config.model,
            base_url=config.base_url,
            message=f"{type(exc).__name__}: {str(exc)[:300]}",
        )

    return SettingsTestResponse(
        ok=True,
        provider=config.provider,
        model=config.model,
        base_url=config.base_url,
        message="Connection test succeeded.",
    )


@router.post("/settings/models", response_model=SettingsModelsResponse)
async def list_settings_models(
    settings: SettingsModelsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = get_effective_llm_config(
        current_user,
        provider=settings.default_provider,
        api_key=settings.api_key,
        model=settings.model,
        base_url=settings.base_url,
    )

    if config.provider == "local":
        return SettingsModelsResponse(
            provider=config.provider,
            base_url=config.base_url,
            source="preset",
            models=_fallback_settings_models(config.provider),
            message="Local provider uses preset model suggestions.",
        )

    try:
        from backend.services.llm.manager import get_llm_manager
        from backend.services.llm.providers import provider_needs_api_key

        if provider_needs_api_key(config.provider) and not config.api_key:
            return SettingsModelsResponse(
                provider=config.provider,
                base_url=config.base_url,
                source="preset",
                models=_fallback_settings_models(config.provider),
                message="API Key is not configured; showing preset model suggestions.",
            )

        adapter = get_llm_manager().get_adapter(
            provider=config.provider,
            model=config.model,
            api_key=config.api_key,
            base_url=config.base_url,
        )
        remote_models = await adapter.list_models(user_api_key=config.api_key)
        if remote_models:
            return SettingsModelsResponse(
                provider=config.provider,
                base_url=config.base_url,
                source="remote",
                models=remote_models,
                message="Fetched models from gateway.",
            )
        return SettingsModelsResponse(
            provider=config.provider,
            base_url=config.base_url,
            source="preset",
            models=_fallback_settings_models(config.provider),
            message="Gateway returned no models; showing preset suggestions.",
        )
    except Exception as exc:
        return SettingsModelsResponse(
            provider=config.provider,
            base_url=config.base_url,
            source="fallback",
            models=_fallback_settings_models(config.provider),
            message=f"{type(exc).__name__}: {str(exc)[:300]}",
        )


# Persona generation endpoint
class PersonaGenerateRequest(BaseModel):
    description: str = Field(..., min_length=5, max_length=1000)  # P1 Fix: 扩到1000
    inspiration_type: Literal["character", "freeform"] = "freeform"  # 新增：用户提到具体角色 vs 自由描述
    world_id: int | None = None  # 新增：注入世界氛围让生成更契合


class PersonaGenerateResponse(BaseModel):
    name_suggestion: str
    title_suggestion: str | None = None  # 新增：知者名片头衔
    background: str | None = None  # 新增：背景故事草稿
    personality: str | None = None  # 新增：性格段落草稿
    speech_style: str | None = None  # 新增：说话风格描述
    traits: dict[str, int]  # 改类型：从 list[str] → 0-10 评分 dict，对齐滑块
    system_prompt_template: str
    greeting: str | None = None  # 新增：Step 5 预览用的初次见面台词
    warnings: list[str] | None = None  # 新增：版权角色处理软警告


PERSONA_GENERATE_PROMPT = """你是角色设计师。根据用户的灵感来源，为 Galgame 风格学习系统生成一位"知者"（导师角色）。

{world_context}

输入：{description}
输入类型：{inspiration_type}（character=用户提到一个具体角色；freeform=自由描述）

当输入类型为 character 时，遵循"风格借鉴"原则：
- 可以提取的：性格倾向（温和/严厉/古怪）、说话风格（文白/简练/比喻）、教学态度、典型情绪反应模式
- 禁止保留的：原作角色姓名、原作专有名词（霍格沃茨/呼吸法/查克拉等）、原作世界观背景、原作具体台词或口头禅、外貌细节复述
- name_suggestion 必须是原创新名字，不得包含原角色名的任何字
- background 必须放置在本系统的"知者"语境中（学院/书院/研究所等通用设定），不得提及原作世界
- 历史人物（孔子、苏格拉底）或公共领域人物（莎士比亚），上述限制放宽，但 name_suggestion 仍略作调整避免完全重名

输出严格 JSON（不要 markdown 代码块）：
{{
  "name_suggestion": "...",
  "title_suggestion": "雾港学院首席研究员（10字以内头衔）",
  "background": "100-180字背景故事",
  "personality": "60-100字性格描述",
  "speech_style": "20-40字说话风格（如：偏文白、爱用比喻）",
  "traits": {{
    "strictness": 0-10,
    "pace": 0-10,
    "questioning": 0-10,
    "warmth": 0-10,
    "humor": 0-10
  }},
  "system_prompt_template": "2-4句的角色身份+性格陈述，不要写教学方法",
  "greeting": "初次见面对学生说的一句话（30字内）"
}}

规则：
- 不要写教学方法（系统会自动注入苏格拉底教学法）
- 必须输出合法 JSON，不要 markdown 代码块
"""

# Simple in-memory cooldown (user_id → last_generate_time)
_generate_cooldowns: dict[int, float] = {}
_COOLDOWN_SECONDS = 30


@router.post("/persona/generate", response_model=PersonaGenerateResponse)
async def generate_persona(
    req: PersonaGenerateRequest,
    db: Session = Depends(get_db),  # 新增：查询 world 上下文
    current_user: User = Depends(get_current_user),
):
    """Use LLM to generate a teacher persona from a natural language description."""
    import json
    import re
    import time

    from backend.services.llm.adapter import get_llm_adapter
    from backend.services.llm.providers import provider_needs_api_key

    # Cooldown check
    now = time.time()
    last = _generate_cooldowns.get(current_user.id, 0)
    if now - last < _COOLDOWN_SECONDS:
        remaining = int(_COOLDOWN_SECONDS - (now - last))
        raise HTTPException(status_code=429, detail=f"请 {remaining} 秒后再试")
    _generate_cooldowns[current_user.id] = now

    config = get_effective_llm_config(current_user)

    if provider_needs_api_key(config.provider) and not config.api_key:
        raise HTTPException(status_code=400, detail="请先在设置页配置 API Key")

    adapter = get_llm_adapter(
        config.provider,
        model=config.model,
        api_key=config.api_key,
        base_url=config.base_url,
    )

    # 构建 world_context
    world_context = ""
    if req.world_id:
        from backend.models.models import World
        world = db.query(World).filter(World.id == req.world_id, World.user_id == current_user.id).first()
        if world:
            parts = [f"目标世界名称：{world.name}。"]
            if world.description:
                parts.append(f"目标世界说明：{world.description}")
            world_context = "".join(parts)

    prompt = PERSONA_GENERATE_PROMPT.format(
        description=req.description,
        inspiration_type=req.inspiration_type,
        world_context=world_context,
    )

    response = await adapter.chat(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="你是人格设计师，只输出合法 JSON。",
        user_api_key=config.api_key,
        max_tokens=1000,
    )

    # Parse JSON from response
    try:
        json_match = re.search(r"\{[\s\S]*\}", response)
        if not json_match:
            raise ValueError("No JSON found")
        data = json.loads(json_match.group())

        # 版权角色处理：检测可能泄露的词汇
        warnings = None
        if req.inspiration_type == "character":
            suspicious = re.findall(r"[\u4e00-\u9fa5]{2,4}", req.description)
            leaked = [t for t in suspicious
                      if t in data.get("name_suggestion", "")
                      or t in (data.get("background") or "")]
            if leaked:
                warnings = [f"AI 输出可能包含原作词汇：{', '.join(leaked)}，建议手动调整"]

        return PersonaGenerateResponse(
            name_suggestion=data.get("name_suggestion", "自定义人格"),
            title_suggestion=data.get("title_suggestion"),
            background=data.get("background"),
            personality=data.get("personality"),
            speech_style=data.get("speech_style"),
            traits=data.get("traits", {
                "strictness": 5,
                "pace": 5,
                "questioning": 5,
                "warmth": 5,
                "humor": 5
            }),
            system_prompt_template=data.get("system_prompt_template", ""),
            greeting=data.get("greeting"),
            warnings=warnings,
        )
    except (json.JSONDecodeError, ValueError) as e:
        # JSON 解析失败返回 422 而非 500，并把原始响应放进 detail 方便 debug
        raise HTTPException(status_code=422, detail=f"AI 生成格式错误，请重试。原始响应：{response[:200]}") from e
