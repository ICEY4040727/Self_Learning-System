from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import attributes
from sqlalchemy.orm import relationship as orm_relationship

from backend.db.database import Base


def _utcnow():
    return datetime.now(UTC)


# Relationship stage labels (shared across routes)
RELATIONSHIP_STAGE_LABELS = {
    "stranger": "初识",
    "acquaintance": "相识",
    "friend": "朋友",
    "mentor": "导师",
    "partner": "伙伴",
}


def _default_relationship():
    return {
        "dimensions": {
            "trust": 0.0,
            "familiarity": 0.0,
            "respect": 0.0,
            "comfort": 0.0,
        },
        "stage": "stranger",
        "history": [],
    }


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="student")
    encrypted_api_key = Column(String(255), nullable=True)
    default_provider = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    worlds = orm_relationship("World", back_populates="user", cascade="all, delete-orphan")
    characters = orm_relationship("Character", back_populates="user", cascade="all, delete-orphan")
    learner_profiles = orm_relationship("LearnerProfile", back_populates="user", cascade="all, delete-orphan")
    learning_diaries = orm_relationship("LearningDiary", back_populates="user", cascade="all, delete-orphan")
    progress_trackings = orm_relationship("ProgressTracking", back_populates="user", cascade="all, delete-orphan")
    sessions = orm_relationship("Session", back_populates="user", cascade="all, delete-orphan")
    checkpoints = orm_relationship("Checkpoint", back_populates="user", cascade="all, delete-orphan")
    textbooks = orm_relationship("Textbook", back_populates="user", cascade="all, delete-orphan")
    user_profile = orm_relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserProfile(Base):
    """用户全局画像 - 跨世界特征聚合（仅用于展示，不注入提示词）"""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    profile = Column(JSON, nullable=False, default=dict)  # 跨世界汇总数据
    computed_at = Column(DateTime, default=_utcnow)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = orm_relationship("User", back_populates="user_profile")


# =============================================================================
# 记忆事实表 (MemoryFact)
# 用于存储 AI 从对话中提取的关于学生的认知事实
#
# 设计说明:
# - character_id: 指向 sage character（AI 老师），记录该老师对学生的认知
# - world_id: 可为 NULL，表示跨世界事实（如学生名字、性格特点）
# - subject_id: 可选，用于关联特定课程/主题
# - fact_type: 事实类型（student_state/concept_struggle/concept_mastered/preference/event/commitment）
# - source_message_id: 溯源，指向产生该记忆的 AI 回复
# =============================================================================
class MemoryFact(Base):
    __tablename__ = "memory_facts"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=True)  # nullable: 跨世界事实
    subject_id = Column(String(50), nullable=True)
    fact_type = Column(String(30), nullable=False)  # student_state/concept_struggle/concept_mastered/preference/event/commitment
    content = Column(Text, nullable=False)
    concept_tags = Column(JSON, nullable=True, default=list)
    source_message_id = Column(Integer, nullable=True)  # 指向 ChatMessage.id（AI 回复）
    salience = Column(Float, default=0.5)  # 重要度 0.1-1.0
    created_at = Column(DateTime, default=_utcnow)
    last_recalled_at = Column(DateTime, default=_utcnow)
    recall_count = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=True)
    # [2A-02] 时态字段：t_valid = 记忆生效时间, t_invalid = 记忆失效/被纠正时间
    t_valid = Column(DateTime, nullable=True, comment="记忆生效时间（事实开始成立的时刻）")
    t_invalid = Column(DateTime, nullable=True, comment="记忆失效时间（事实被纠正/过期的时刻）")

    character = orm_relationship("Character", back_populates="memory_facts")
    world = orm_relationship("World", back_populates="memory_facts")


class World(Base):
    __tablename__ = "worlds"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    scenes = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=_utcnow)

    user = orm_relationship("User", back_populates="worlds")
    world_characters = orm_relationship("WorldCharacter", back_populates="world", cascade="all, delete-orphan")
    courses = orm_relationship("Course", back_populates="world", cascade="all, delete-orphan")
    sessions = orm_relationship("Session", back_populates="world", cascade="all, delete-orphan")
    checkpoints = orm_relationship("Checkpoint", back_populates="world", cascade="all, delete-orphan")
    learner_profiles = orm_relationship("LearnerProfile", back_populates="world", cascade="all, delete-orphan")
    memory_facts = orm_relationship("MemoryFact", back_populates="world", cascade="all, delete-orphan")
    fsrs_states = orm_relationship("FSRSState", back_populates="world", cascade="all, delete-orphan")


# 角色类型说明 (Character.type):
#   - "sage": 导师角色 (AI教师)
#   - "traveler": 旅人角色 (玩家在游戏世界中的化身)
class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    # type: "sage" | "traveler" - 区分导师角色和学习者角色
    type = Column(String(20), nullable=False, default="sage")
    avatar = Column(String(255), nullable=True)
    personality = Column(Text, nullable=True)
    background = Column(Text, nullable=True)
    speech_style = Column(Text, nullable=True)
    sprites = Column(JSON, nullable=True)
    title = Column(String(100), nullable=True)  # 知者名片头衔
    tags = Column(JSON, nullable=True, default=list)  # 角色标签列表
    # TODO [2E-01]: experience_points/level 已决定不做经验值系统 (Plan E2)，
    # 但因前后端多处引用暂保留，待下版本清理
    experience_points = Column(Integer, nullable=False, default=0)  # 经验值
    level = Column(Integer, nullable=False, default=1)  # 等级
    # Phase 1.5: TeacherPersona 合并 (DD1)
    traits = Column(JSON, nullable=True, comment='性格参数 5 维 {strictness, pace, questioning, warmth, humor}')
    system_prompt_template = Column(Text, nullable=True, comment='自定义 system prompt 模板')
    template_name = Column(String(50), nullable=True, comment='角色模板 key，如 socrates/einstein')
    is_active = Column(Boolean, default=True, comment='是否可用于教学（DD1: 替代 TeacherPersona.is_active）')
    created_at = Column(DateTime, default=_utcnow)

    user = orm_relationship("User", back_populates="characters")
    # Phase 1.5 DD1: TeacherPersona 已删除，相关字段合并到 Character
    world_links = orm_relationship("WorldCharacter", back_populates="character", cascade="all, delete-orphan")
    memory_facts = orm_relationship("MemoryFact", back_populates="character", cascade="all, delete-orphan")


class WorldCharacter(Base):
    __tablename__ = "world_characters"
    __table_args__ = (UniqueConstraint("world_id", "character_id", name="uq_world_character"),)

    id = Column(Integer, primary_key=True, index=True)
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False)
    character_id = Column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    is_primary = Column(Boolean, default=False)

    world = orm_relationship("World", back_populates="world_characters")
    character = orm_relationship("Character", back_populates="world_links")


# Phase 1.5 DD1: TeacherPersona 模型已删除
# 人格数据直接存储在 Character 表中 (traits, system_prompt_template, template_name, is_active)


# 学习者档案 (LearnerProfile):
# 存储用户在特定世界中的学习状态、偏好、元认知等信息
# 注意：这是"学习追踪层"，与游戏角色层(traveler)是不同概念
class LearnerProfile(Base):
    __tablename__ = "learner_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False)
    profile = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = orm_relationship("User", back_populates="learner_profiles")
    world = orm_relationship("World", back_populates="learner_profiles")
    sessions = orm_relationship("Session", back_populates="learner_profile")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    target_level = Column(String(50), nullable=True)
    # meta JSON: 存储表单扩展字段 (current_level, motivation, pace, weekly_minutes, sage_ids 等)
    # 见文档: docs/v1.0.0前后端联调修复/世界_课程_角色_表单设计.md 附录 A
    meta = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime, default=_utcnow)

    world = orm_relationship("World", back_populates="courses")
    lesson_plans = orm_relationship("LessonPlan", back_populates="course", cascade="all, delete-orphan")
    learning_diaries = orm_relationship("LearningDiary", back_populates="course", cascade="all, delete-orphan")
    progress_trackings = orm_relationship("ProgressTracking", back_populates="course", cascade="all, delete-orphan")
    sessions = orm_relationship("Session", back_populates="course", cascade="all, delete-orphan")
    textbooks = orm_relationship("Textbook", back_populates="course", cascade="all, delete-orphan")


class LessonPlan(Base):
    __tablename__ = "lesson_plans"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    course = orm_relationship("Course", back_populates="lesson_plans")


class LearningDiary(Base):
    __tablename__ = "learning_diaries"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    content = Column(Text, nullable=False)
    reflection = Column(Text, nullable=True)

    course = orm_relationship("Course", back_populates="learning_diaries")
    user = orm_relationship("User", back_populates="learning_diaries")


class ProgressTracking(Base):
    __tablename__ = "progress_trackings"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic = Column(String(100), nullable=False)
    # [TODO-T3] discriminator: 'concept' = concept_tag from MemoryFact (mastery_tracker),
    # 'lesson' = course lesson title (teaching_planner). Without this column the two
    # writers stomped each other when a lesson title equaled a concept name.
    topic_type = Column(String(20), nullable=False, default="concept")
    mastery_level = Column(Integer, default=0)
    last_review = Column(DateTime, nullable=True)
    next_review = Column(DateTime, nullable=True)

    course = orm_relationship("Course", back_populates="progress_trackings")
    user = orm_relationship("User", back_populates="progress_trackings")


class ConceptMastery(Base):
    """概念掌握度 — per-(user, concept) 完全跨世界。

    [TR-A1] 从 ProgressTracking 拆出来。原 ProgressTracking 用 (course_id, user_id, topic)
    做隔离，导致同一个用户在 course A 学过的"递归"在 course B 不可见，
    跟"画像跨世界"的产品语义冲突。新表去掉 course_id / world_id，
    用 (user_id, concept_id) 做 UNIQUE，让概念掌握度真正跨世界共享。
    """
    __tablename__ = "concept_mastery"
    __table_args__ = (UniqueConstraint("user_id", "concept_id", name="uq_concept_mastery_user_concept"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    concept_id = Column(String(150), nullable=False)
    mastery_level = Column(Integer, default=0)
    last_review = Column(DateTime, nullable=True)
    next_review = Column(DateTime, nullable=True)


class FSRSState(Base):
    __tablename__ = "fsrs_states"
    __table_args__ = (UniqueConstraint("world_id", "concept_id", name="uq_fsrs_world_concept"),)

    id = Column(Integer, primary_key=True, index=True)
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False)
    concept_id = Column(String(150), nullable=False)
    difficulty = Column(Float, nullable=True)
    stability = Column(Float, nullable=True)
    last_review = Column(DateTime, nullable=True)
    next_review = Column(DateTime, nullable=True)
    reps = Column(Integer, default=0)
    # [TODO-T7] Authoritative py-fsrs Card.to_dict() payload — needed because
    # Card.from_dict requires card_id/state/step which the columns above don't
    # carry. Other columns are kept for ad-hoc SQL convenience only.
    card_data = Column(JSON, nullable=True)

    world = orm_relationship("World", back_populates="fsrs_states")


# 会话模型 (Session):
# 一个学习会话关联多个角色和档案:
#   - sage_character_id: 导师角色 (Character.type="sage") - AI教师角色
#   - traveler_character_id: 旅人角色 (Character.type="traveler") - 玩家游戏化身
#   - teacher_persona_id: 教师人格 - 导师的具体人格设定
#   - learner_profile_id: 学习者档案 - 记录用户学习状态
#
# 层级区分:
#   - traveler: 游戏角色层 (故事/游戏中玩家扮演的角色)
#   - learner_profile: 学习追踪层 (记录用户学习状态、偏好)
class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False)
    # 角色关联 (游戏角色层)
    sage_character_id = Column(Integer, ForeignKey("characters.id"), nullable=True)
    traveler_character_id = Column(Integer, ForeignKey("characters.id"), nullable=True)
    started_at = Column(DateTime, default=_utcnow)
    ended_at = Column(DateTime, nullable=True)
    system_prompt = Column(Text, nullable=True)
    relationship = Column(JSON, nullable=False, default=_default_relationship)
    # Optional links: sessions may start without active persona/profile or branch parent.
    # Phase 1.5 DD1: teacher_persona_id 保留用于向后兼容，不再引用 TeacherPersona 表
    # 新代码应直接使用 sage_character_id + Character.system_prompt_template
    teacher_persona_id = Column(Integer, nullable=True)
    learner_profile_id = Column(Integer, ForeignKey("learner_profiles.id"), nullable=True)
    parent_checkpoint_id = Column(Integer, ForeignKey("checkpoints.id"), nullable=True)
    branch_name = Column(String(120), nullable=True)

    course = orm_relationship("Course", back_populates="sessions")
    user = orm_relationship("User", back_populates="sessions")
    world = orm_relationship("World", back_populates="sessions")
    # Phase 1.5 DD1: TeacherPersona 已删除，不再需要此 relationship
    learner_profile = orm_relationship("LearnerProfile", back_populates="sessions")
    chat_messages = orm_relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    relationship_stage_records = orm_relationship("RelationshipStageRecord", back_populates="session", cascade="all, delete-orphan")
    parent_checkpoint = orm_relationship("Checkpoint", foreign_keys=[parent_checkpoint_id], post_update=True)

    @property
    def relationship_stage(self):
        rel = self.relationship or {}
        return rel.get("stage", "stranger")

    @relationship_stage.setter
    def relationship_stage(self, stage: str):
        rel = dict(self.relationship or _default_relationship())
        rel["stage"] = stage or "stranger"
        self.relationship = rel
        attributes.flag_modified(self, "relationship")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    sender_type = Column(String(20), nullable=False)
    sender_id = Column(Integer, nullable=True)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=_utcnow)
    emotion_analysis = Column(JSON, nullable=True)
    used_memory_ids = Column(JSON, nullable=True)

    session = orm_relationship("Session", back_populates="chat_messages")


class RelationshipStageRecord(Base):
    __tablename__ = "relationship_stages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    stage = Column(String(20), nullable=False)
    reason = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=_utcnow)

    session = orm_relationship("Session", back_populates="relationship_stage_records")


class StrategyRule(Base):
    """教学策略规则表 - 根据画像维度值匹配教学指令"""
    __tablename__ = "strategy_rules"

    id = Column(Integer, primary_key=True, index=True)
    dimension_key = Column(String(50), nullable=False)  # 关联 profile_dimension_defs.key
    low_instruction = Column(Text, nullable=True)   # 维度值 < 0.4
    mid_instruction = Column(Text, nullable=True)   # 0.4-0.7 (null = 不干预)
    high_instruction = Column(Text, nullable=True)  # > 0.7
    priority = Column(Integer, default=0)
    scene = Column(String(20), default="all")  # learning/review/all
    enabled = Column(Boolean, default=True)


class ProfileDimensionDef(Base):
    """可扩展的画像维度定义表 - 新增维度 = 新增一行数据"""
    __tablename__ = "profile_dimension_defs"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    category = Column(String(30), nullable=False)  # cognitive/metacognitive/affective
    source_fact_types = Column(JSON, nullable=True, default=list)
    aggregation_method = Column(String(20), nullable=False)  # ratio/count/conversion_rate/keyword_extract/emotion_balance
    aggregation_params = Column(JSON, nullable=True, default=dict)
    value_range = Column(JSON, nullable=True, default=lambda: {"min": 0.0, "max": 1.0})
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)


class NarrativeTriggerRule(Base):
    """叙事触发规则表 - 可配置的叙事事件触发器"""
    __tablename__ = "narrative_trigger_rules"

    id = Column(Integer, primary_key=True, index=True)
    trigger_type = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    # [TODO-N4] Implemented in narrative_engine._check_condition:
    #   fact_created, fact_count_threshold, relationship_stage_change
    # Listed here historically but NOT implemented (engine logs warning):
    #   profile_shift, session_event, time_gap
    condition_type = Column(String(30), nullable=False)
    condition_params = Column(JSON, nullable=True, default=dict)
    priority = Column(String(10), default="medium")  # high/medium/low
    writeback_memory = Column(Boolean, default=False)
    cooldown_minutes = Column(Integer, default=60)
    event_template = Column(Text, nullable=True)
    prompt_template = Column(Text, nullable=True)
    ui_template = Column(String(20), default="toast")  # toast/modal/badge
    enabled = Column(Boolean, default=True)


class AchievementDef(Base):
    """成就定义表 - 新增成就 = 新增一行数据"""
    __tablename__ = "achievement_defs"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(20), nullable=False)  # milestone/growth/relationship/resilience/exploration/hidden
    # [TODO-N4] Implemented in gamification._check_condition:
    #   stat_threshold, dimension_crossing, relationship_stage,
    #   fact_transition, fact_count_threshold
    # Listed here historically but NOT implemented (engine logs warning):
    #   consecutive_days
    condition_type = Column(String(30), nullable=False)
    condition_params = Column(JSON, nullable=True, default=dict)
    rarity = Column(String(10), default="common")  # common/rare/legendary
    icon = Column(String(50), nullable=True)
    hidden = Column(Boolean, default=False)  # 解锁前是否可见
    enabled = Column(Boolean, default=True)


class Achievement(Base):
    """成就解锁记录"""
    __tablename__ = "achievements"
    __table_args__ = (UniqueConstraint("user_id", "character_id", "achievement_key", name="uq_user_char_achievement"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    achievement_key = Column(String(50), nullable=False)
    unlocked_at = Column(DateTime, default=_utcnow)
    context = Column(JSON, nullable=True)  # 解锁上下文（如哪个概念）


class Textbook(Base):
    """教材上传记录

    存储用户上传的教材文件信息，关联到 Course。
    Phase 3 Step 2: 教材上传 + AI 课程生成
    """
    __tablename__ = "textbooks"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=True)
    content_type = Column(String(100), nullable=True)
    extracted_text = Column(Text, nullable=True, comment="提取的文本内容，用于 AI 处理")
    page_count = Column(Integer, nullable=True)
    # 状态: uploaded → extracting → extracted → processing → processed / error
    status = Column(String(20), default="uploaded")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    course = orm_relationship("Course", back_populates="textbooks")
    user = orm_relationship("User", back_populates="textbooks")


class Checkpoint(Base):
    __tablename__ = "checkpoints"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    save_name = Column(String(100), nullable=False)
    message_index = Column(Integer, nullable=False, default=0)
    state = Column(JSON, nullable=False, default=dict)
    # Issue #207: 文件存储路径（新存档用文件存储，旧存档 file_path 为 NULL）
    file_path = Column(String(255), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    thumbnail_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    user = orm_relationship("User", back_populates="checkpoints")
    world = orm_relationship("World", back_populates="checkpoints")
    session = orm_relationship("Session", foreign_keys=[session_id])

