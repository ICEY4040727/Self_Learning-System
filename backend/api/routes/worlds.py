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
from backend.models.models import Character, Course, User, World, WorldCharacter

from backend.api.routes.courses import CourseResponse
from backend.services.user_llm_settings import get_effective_llm_config


router = APIRouter()

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

            # 如果提供了 user_id，获取课程进度（canonical · A2-3）
            if current_user_id:
                from backend.services.progress_facade import progress_facade

                progress = progress_facade.get_course_lesson_progress_fraction(
                    db, course, current_user_id,
                )

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

