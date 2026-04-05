"""
models/learning_unit.py
──────────────────────────────────────────────────────────────
LearningUnit — AI 切分生成的课时单元

核心设计原则：
  1. 每个 unit 对应课程材料中的一个「知识块」，学习引擎直接消费。
  2. unit_index 决定线性学习顺序；prerequisite_unit_ids 描述有向依赖。
  3. dialogue_hints 是给 LLM 对话引擎的辅助提示，不对学习者展示。
  4. status 允许人工干预（draft→ready），ready 状态才进入学习引擎。

字段说明：
  unit_index          在课程内的顺序编号（0-based）
  title               课时标题
  summary             2-3句概要（对学习者展示）
  raw_content         对应的原始教材片段（给 LLM 作上下文）
  learning_objectives 学习目标列表（Bloom 动词开头）
  bloom_level         认知层次 remember|understand|apply|analyze|evaluate|create
  estimated_minutes   预估学习时长（分钟）
  key_concepts        关键概念列表（与知识图谱节点联动）
  prerequisite_unit_ids  前置课时 id 列表（JSON 数组）
  dialogue_hints      对话引导提示列表（苏格拉底式教学专用）
  status              draft | ready | archived
──────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from sqlalchemy import (
    Column, DateTime, ForeignKey, Integer, JSON, String, Text, func
)
from sqlalchemy.orm import relationship

from backend.database import Base

UnitStatus    = str  # 'draft' | 'ready' | 'archived'
BloomLevel    = str  # 'remember' | 'understand' | 'apply' | 'analyze' | 'evaluate' | 'create'

BLOOM_LEVELS = frozenset({
    "remember", "understand", "apply",
    "analyze", "evaluate", "create",
})


class LearningUnit(Base):
    __tablename__ = "learning_units"

    id          = Column(Integer, primary_key=True, index=True)
    course_id   = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)

    # Ordering
    unit_index  = Column(Integer, nullable=False)

    # Content fields
    title                  = Column(String(256), nullable=False)
    summary                = Column(Text,        nullable=False)
    raw_content            = Column(Text,        nullable=False)   # 原始材料片段

    # Pedagogical metadata
    learning_objectives    = Column(JSON, default=list, nullable=False)  # list[str]
    bloom_level            = Column(String(20), nullable=True)
    estimated_minutes      = Column(Integer, default=20, nullable=False)
    key_concepts           = Column(JSON, default=list, nullable=False)  # list[str]
    prerequisite_unit_ids  = Column(JSON, default=list, nullable=False)  # list[int]

    # LLM teaching hints (not shown to learner)
    dialogue_hints         = Column(JSON, default=list, nullable=False)  # list[str]

    # Lifecycle
    status      = Column(String(20), default="draft", nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    course = relationship("Course", back_populates="learning_units")

    def __repr__(self) -> str:
        return (
            f"<LearningUnit id={self.id} course={self.course_id} "
            f"#{self.unit_index} {self.title!r} status={self.status}>"
        )
