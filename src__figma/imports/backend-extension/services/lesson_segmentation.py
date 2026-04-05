"""
services/lesson_segmentation.py
──────────────────────────────────────────────────────────────
AI 课时切分服务

流程：
  1. 拼接指定教材的 text_content
  2. 构造苏格拉底教学风格的结构化 Prompt
  3. 调用现有 LLM adapter（复用 provider/api_key 配置）
  4. 解析 JSON 响应 → list[UnitDraft]
  5. index → id 映射（prerequisite_unit_indices → prerequisite_unit_ids）
  6. 批量写入 LearningUnit 表

Prompt 设计原则：
  - 要求输出严格 JSON（无多余 markdown 包裹）
  - 每个 unit 包含 Bloom 层次、对话提示、前置依赖
  - 大教材自动截断到 60K token 并记录 warning
──────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.course_material  import CourseMaterial
from backend.models.learning_unit    import LearningUnit
from backend.models.course           import Course         # 现有模型
from backend.schemas.course_content  import UnitDraft, GenerateUnitsResponse, LearningUnitResponse
from backend.services.text_extraction import truncate_to_token_limit

logger = logging.getLogger(__name__)

# ── Prompt Templates ──────────────────────────────────────────

SYSTEM_PROMPT = """\
你是一位资深课程设计专家，擅长基于苏格拉底问答法构建互动式学习单元。

你的任务：将提供的课程教材切分为结构化的「学习单元（Learning Unit）」，\
每个单元围绕一个核心知识点，适合 AI 导师通过对话引导学习者掌握。

**输出约束（严格遵守）：**
- 仅输出合法 JSON 数组，不得有任何 markdown 代码块包裹、注释或多余文字
- JSON 数组中每个对象必须包含以下字段（类型严格匹配）：
  - unit_index: integer（0-based，连续递增）
  - title: string（15字以内，清晰概括核心概念）
  - summary: string（2-4句话，面向学习者）
  - raw_content: string（对应原文段落，完整保留）
  - learning_objectives: string[]（每条以 Bloom 动词开头，如"理解…""能够…""分析…"）
  - bloom_level: string（"remember"|"understand"|"apply"|"analyze"|"evaluate"|"create" 之一）
  - estimated_minutes: integer（5-60）
  - key_concepts: string[]（3-8个）
  - prerequisite_unit_indices: integer[]（依赖的前置单元 unit_index，可为空列表）
  - dialogue_hints: string[]（3-5条苏格拉底式引导问题，不对学习者展示）
"""

USER_PROMPT_TEMPLATE = """\
课程名称：{course_name}
课程描述：{course_description}
目标水平：{target_level}
期望课时数：{target_count}（0 表示由你自主决定，建议每 800-1500 字一个单元）

------- 教材内容（开始）-------
{material_content}
------- 教材内容（结束）-------

请严格按照系统 Prompt 的 JSON 格式输出所有学习单元。
"""


# ── Main service function ─────────────────────────────────────

async def generate_learning_units(
    db: Session,
    course: Course,
    user,
    material_ids: list[int],
    target_unit_count: int,
    overwrite: bool,
) -> GenerateUnitsResponse:
    """
    主入口：执行 AI 课时切分并落库。

    返回 GenerateUnitsResponse（含 units 列表与 warnings）。
    抛出 HTTPException 供路由层捕获。
    """
    from fastapi import HTTPException

    warnings: list[str] = []

    # ── 1. 收集教材文本 ────────────────────────────────────────
    query = (
        db.query(CourseMaterial)
        .filter(
            CourseMaterial.course_id == course.id,
            CourseMaterial.extraction_status == "ready",
        )
    )
    if material_ids:
        query = query.filter(CourseMaterial.id.in_(material_ids))

    materials = query.order_by(CourseMaterial.created_at).all()

    if not materials:
        raise HTTPException(
            status_code=422,
            detail="没有可用的已就绪教材。请先上传教材并等待文本提取完成。",
        )

    full_text = "\n\n===教材分隔===\n\n".join(
        f"【{m.original_filename}】\n{m.text_content or ''}"
        for m in materials
    )

    truncated_text, was_truncated = truncate_to_token_limit(full_text, max_tokens=60_000)
    if was_truncated:
        warnings.append(
            "教材内容超过 60K token 限制，已自动截断尾部内容。"
            "建议分批上传或拆分为多门课程。"
        )

    # ── 2. 调用 LLM ────────────────────────────────────────────
    raw_json = await _call_llm(
        db=db,
        user=user,
        course=course,
        material_content=truncated_text,
        target_count=target_unit_count,
    )

    # ── 3. 解析 JSON ───────────────────────────────────────────
    unit_drafts = _parse_unit_drafts(raw_json, warnings)
    if not unit_drafts:
        raise HTTPException(
            status_code=502,
            detail="AI 返回的结果无法解析为有效的课时列表，请重试。",
        )

    # ── 4. overwrite: 删除现有草稿 ─────────────────────────────
    if overwrite:
        deleted = (
            db.query(LearningUnit)
            .filter(
                LearningUnit.course_id == course.id,
                LearningUnit.status    == "draft",
            )
            .all()
        )
        for u in deleted:
            db.delete(u)
        db.flush()

    # ── 5. 落库 ────────────────────────────────────────────────
    saved_units = _persist_units(db, course.id, unit_drafts)

    db.commit()
    for u in saved_units:
        db.refresh(u)

    logger.info(
        "课时切分完成 course_id=%d units=%d warnings=%d",
        course.id, len(saved_units), len(warnings),
    )

    return GenerateUnitsResponse(
        course_id=course.id,
        units_created=len(saved_units),
        units=[LearningUnitResponse.model_validate(u) for u in saved_units],
        warnings=warnings,
    )


# ── LLM call ─────────────────────────────────────────────────

async def _call_llm(
    db: Session,
    user,
    course: Course,
    material_content: str,
    target_count: int,
) -> str:
    """调用现有 LLM adapter，返回模型原始输出字符串。"""
    from fastapi import HTTPException
    from backend.core.security          import decrypt_api_key
    from backend.services.llm.adapter   import get_llm_adapter

    provider  = getattr(user, "default_provider", None) or "claude"
    enc_key   = getattr(user, "encrypted_api_key", None)
    api_key   = decrypt_api_key(enc_key) if enc_key else None

    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="请先在「系统设置」中配置 API Key，才能使用 AI 课时切分功能。",
        )

    user_prompt = USER_PROMPT_TEMPLATE.format(
        course_name=course.name,
        course_description=course.description or "（无描述）",
        target_level=course.target_level or "中级",
        target_count=target_count if target_count > 0 else "由 AI 自主决定",
        material_content=material_content,
    )

    adapter = get_llm_adapter(provider)
    # adapter.complete 为现有接口：(system, user, api_key) -> str
    try:
        response = await adapter.complete(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_prompt,
            api_key=api_key,
            max_tokens=8192,
            temperature=0.3,     # 低温保证结构稳定
        )
    except Exception as exc:
        logger.error("LLM 调用失败 provider=%s: %s", provider, exc)
        raise HTTPException(status_code=502, detail=f"AI 服务调用失败：{exc}") from exc

    return response


# ── Parse ─────────────────────────────────────────────────────

def _parse_unit_drafts(raw: str, warnings: list[str]) -> list[UnitDraft]:
    """
    将 LLM 原始输出解析为 UnitDraft 列表。
    容错策略：
      1. 直接解析整个字符串
      2. 提取第一个 JSON 数组（兼容模型添加了文字说明的情况）
      3. 逐条解析（兼容模型返回 NDJSON 的情况）
    """
    text = raw.strip()

    # 移除可能的 markdown 代码块
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    data: list[dict] | None = None

    # 尝试 1: 直接解析
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试 2: 提取 JSON 数组
    if data is None:
        match = re.search(r"\[[\s\S]+\]", text)
        if match:
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

    if data is None:
        warnings.append(f"AI 返回内容无法解析为 JSON，原文前 200 字：{text[:200]}")
        return []

    if not isinstance(data, list):
        warnings.append("AI 返回值不是 JSON 数组。")
        return []

    drafts: list[UnitDraft] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            warnings.append(f"第 {i} 个元素不是对象，已跳过。")
            continue
        try:
            draft = UnitDraft(
                unit_index            = item.get("unit_index", i),
                title                 = str(item.get("title", f"单元 {i + 1}"))[:256],
                summary               = str(item.get("summary", "")),
                raw_content           = str(item.get("raw_content", "")),
                learning_objectives   = _ensure_str_list(item.get("learning_objectives")),
                bloom_level           = item.get("bloom_level"),
                estimated_minutes     = int(item.get("estimated_minutes", 20)),
                key_concepts          = _ensure_str_list(item.get("key_concepts")),
                prerequisite_unit_indices = _ensure_int_list(
                    item.get("prerequisite_unit_indices")
                ),
                dialogue_hints        = _ensure_str_list(item.get("dialogue_hints")),
            )
            drafts.append(draft)
        except Exception as exc:
            warnings.append(f"第 {i} 个单元解析失败（{exc}），已跳过。")

    # 按 unit_index 排序，重新编号保证连续
    drafts.sort(key=lambda d: d.unit_index)
    for j, d in enumerate(drafts):
        d.unit_index = j

    return drafts


# ── Persist ───────────────────────────────────────────────────

def _persist_units(
    db: Session,
    course_id: int,
    drafts: list[UnitDraft],
) -> list[LearningUnit]:
    """
    将 UnitDraft 列表写入数据库。
    prerequisite_unit_indices（0-based）在此阶段转为真实 id。
    因为是批量新增，先全部 flush 获取 id，再做 index→id 映射。
    """
    # 第一遍：全部 add 并 flush 获取自增 id
    units: list[LearningUnit] = []
    for draft in drafts:
        unit = LearningUnit(
            course_id             = course_id,
            unit_index            = draft.unit_index,
            title                 = draft.title,
            summary               = draft.summary,
            raw_content           = draft.raw_content,
            learning_objectives   = draft.learning_objectives,
            bloom_level           = draft.bloom_level,
            estimated_minutes     = max(5, min(240, draft.estimated_minutes)),
            key_concepts          = draft.key_concepts,
            prerequisite_unit_ids = [],          # 第二遍再填
            dialogue_hints        = draft.dialogue_hints,
            status                = "draft",
        )
        db.add(unit)
        units.append(unit)

    db.flush()  # 获取所有 id

    # index → id 映射表
    index_to_id = {u.unit_index: u.id for u in units}

    # 第二遍：填充 prerequisite_unit_ids
    for unit, draft in zip(units, drafts):
        unit.prerequisite_unit_ids = [
            index_to_id[idx]
            for idx in draft.prerequisite_unit_indices
            if idx in index_to_id
        ]

    return units


# ── Helpers ───────────────────────────────────────────────────

def _ensure_str_list(v) -> list[str]:
    if isinstance(v, list):
        return [str(x) for x in v if x is not None]
    return []


def _ensure_int_list(v) -> list[int]:
    if isinstance(v, list):
        result = []
        for x in v:
            try:
                result.append(int(x))
            except (TypeError, ValueError):
                pass
        return result
    return []
