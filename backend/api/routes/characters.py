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
from backend.models.models import Character, User, World, WorldCharacter

from backend.services.character_llm_settings import normalize_character_llm_settings
from backend.services.user_llm_settings import get_effective_llm_config


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
