"""
schemas/course_content.py
──────────────────────────────────────────────────────────────
Pydantic v2 schemas for CourseMaterial & LearningUnit endpoints.

Section layout:
  A. CourseMaterial  — upload / list / delete
  B. LearningUnit    — read / update / delete
  C. Segmentation    — request / response for POST generate-units
──────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, List, Optional

from pydantic import BaseModel, Field, field_validator


# ════════════════════════════════════════════════════════════
#  A. CourseMaterial
# ════════════════════════════════════════════════════════════

class CourseMaterialResponse(BaseModel):
    id:                int
    course_id:         int
    user_id:           int
    filename:          str
    original_filename: str
    content_type:      str
    file_size:         int
    extraction_status: str
    error_message:     Optional[str]
    created_at:        datetime
    updated_at:        Optional[datetime]

    model_config = {"from_attributes": True}


class CourseMaterialListResponse(BaseModel):
    materials: List[CourseMaterialResponse]
    total:     int


# ════════════════════════════════════════════════════════════
#  B. LearningUnit
# ════════════════════════════════════════════════════════════

BLOOM_LEVELS = frozenset({
    "remember", "understand", "apply",
    "analyze", "evaluate", "create",
})

UNIT_STATUSES = frozenset({"draft", "ready", "archived"})


class LearningUnitResponse(BaseModel):
    id:                     int
    course_id:              int
    unit_index:             int
    title:                  str
    summary:                str
    raw_content:            str
    learning_objectives:    List[str]
    bloom_level:            Optional[str]
    estimated_minutes:      int
    key_concepts:           List[str]
    prerequisite_unit_ids:  List[int]
    dialogue_hints:         List[str]
    status:                 str
    created_at:             datetime
    updated_at:             Optional[datetime]

    model_config = {"from_attributes": True}


class LearningUnitUpdate(BaseModel):
    """PATCH payload — all fields optional."""
    title:                 Optional[str]                   = None
    summary:               Optional[str]                   = None
    raw_content:           Optional[str]                   = None
    learning_objectives:   Optional[List[str]]             = None
    bloom_level:           Optional[str]                   = None
    estimated_minutes:     Optional[Annotated[int, Field(ge=5, le=240)]] = None
    key_concepts:          Optional[List[str]]             = None
    prerequisite_unit_ids: Optional[List[int]]             = None
    dialogue_hints:        Optional[List[str]]             = None
    status:                Optional[str]                   = None

    @field_validator("bloom_level")
    @classmethod
    def validate_bloom(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in BLOOM_LEVELS:
            raise ValueError(f"bloom_level must be one of {sorted(BLOOM_LEVELS)}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in UNIT_STATUSES:
            raise ValueError(f"status must be one of {sorted(UNIT_STATUSES)}")
        return v


class LearningUnitsListResponse(BaseModel):
    units: List[LearningUnitResponse]
    total: int


# ════════════════════════════════════════════════════════════
#  C. Segmentation  request / response
# ════════════════════════════════════════════════════════════

class GenerateUnitsRequest(BaseModel):
    """
    POST /api/courses/{course_id}/generate-units

    material_ids: 指定参与切分的教材 id 列表（空列表 = 使用该课程下全部 ready 教材）
    target_unit_count: 期望生成的课时数（0 = AI 自主决定）
    overwrite: True 时删除已有草稿单元后重新生成
    """
    material_ids:       List[int]                                  = Field(default_factory=list)
    target_unit_count:  Annotated[int, Field(ge=0, le=50)]         = 0
    overwrite:          bool                                       = False


class UnitDraft(BaseModel):
    """AI 服务内部中间结构，也作为 generate-units 响应的单元体。"""
    unit_index:             int
    title:                  str
    summary:                str
    raw_content:            str
    learning_objectives:    List[str]     = Field(default_factory=list)
    bloom_level:            Optional[str] = None
    estimated_minutes:      int           = 20
    key_concepts:           List[str]     = Field(default_factory=list)
    prerequisite_unit_indices: List[int]  = Field(default_factory=list)  # 临时用 index，落库时转 id
    dialogue_hints:         List[str]     = Field(default_factory=list)


class GenerateUnitsResponse(BaseModel):
    course_id:      int
    units_created:  int
    units:          List[LearningUnitResponse]
    warnings:       List[str]   = Field(default_factory=list)
