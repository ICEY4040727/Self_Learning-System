"""
routes/course_content.py
──────────────────────────────────────────────────────────────
课程内容路由：教材管理 + AI 课时切分

挂载方式（在 main.py 中）：
    from backend.routes.course_content import router as content_router
    app.include_router(content_router, prefix="/api")

新增端点总览：
  POST   /api/courses/{course_id}/materials              上传教材文件
  GET    /api/courses/{course_id}/materials              列出教材
  DELETE /api/courses/{course_id}/materials/{mat_id}     删除教材

  POST   /api/courses/{course_id}/generate-units         AI 切分课时
  GET    /api/courses/{course_id}/units                  列出课时
  PATCH  /api/courses/{course_id}/units/{unit_id}        编辑课时
  DELETE /api/courses/{course_id}/units/{unit_id}        删除课时
  PATCH  /api/courses/{course_id}/units/{unit_id}/status 单独修改状态
──────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, HTTPException,
    Query, UploadFile, status,
)
from sqlalchemy.orm import Session

from backend.database            import get_db
from backend.core.auth           import get_current_user
from backend.models.course       import Course
from backend.models.course_material import (
    CourseMaterial, ALLOWED_CONTENT_TYPES, MAX_MATERIAL_SIZE_BYTES,
)
from backend.models.learning_unit import LearningUnit
from backend.schemas.course_content import (
    CourseMaterialResponse, CourseMaterialListResponse,
    LearningUnitResponse, LearningUnitUpdate, LearningUnitsListResponse,
    GenerateUnitsRequest, GenerateUnitsResponse,
)
from backend.services.text_extraction  import extract_text, ExtractionError
from backend.services.lesson_segmentation import generate_learning_units

logger = logging.getLogger(__name__)
router = APIRouter(tags=["course-content"])

# 文件存储目录（可替换为 S3/OSS）
UPLOAD_DIR = Path("uploads/course_materials")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════

def _get_course_for_user(course_id: int, user, db: Session) -> Course:
    """获取课程并校验归属（通过 world.user_id）。"""
    course = (
        db.query(Course)
        .join(Course.world)
        .filter(Course.id == course_id)
        .first()
    )
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在。")
    if course.world.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该课程。")
    return course


def _get_material(mat_id: int, course_id: int, user, db: Session) -> CourseMaterial:
    mat = db.query(CourseMaterial).filter(
        CourseMaterial.id        == mat_id,
        CourseMaterial.course_id == course_id,
        CourseMaterial.user_id   == user.id,
    ).first()
    if not mat:
        raise HTTPException(status_code=404, detail="教材不存在或无权访问。")
    return mat


def _get_unit(unit_id: int, course_id: int, db: Session) -> LearningUnit:
    unit = db.query(LearningUnit).filter(
        LearningUnit.id        == unit_id,
        LearningUnit.course_id == course_id,
    ).first()
    if not unit:
        raise HTTPException(status_code=404, detail="学习单元不存在。")
    return unit


# ══════════════════════════════════════════════════════════════
#  课程教材管理
# ══════════════════════════════════════════════════════════════

@router.post(
    "/courses/{course_id}/materials",
    response_model=CourseMaterialResponse,
    status_code=status.HTTP_201_CREATED,
    summary="上传课程教材",
)
async def upload_material(
    course_id:        int,
    file:             UploadFile = File(...),
    background_tasks: BackgroundTasks = ...,
    db:               Session = Depends(get_db),
    current_user      = Depends(get_current_user),
):
    """
    上传教材文件（.txt / .md / .pdf / .docx）。

    - 文件大小 ≤ 10 MB
    - 文本提取在后台异步执行（状态：pending → processing → ready/error）
    """
    course = _get_course_for_user(course_id, current_user, db)

    # ── Validate ───────────────────────────────────────────────
    content_type = file.content_type or ""
    if content_type.split(";")[0].strip() not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"不支持的文件类型 '{content_type}'。"
                "请上传 .txt / .md / .pdf / .docx 文件。"
            ),
        )

    content = await file.read()
    if len(content) > MAX_MATERIAL_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"文件超过 10 MB 限制（当前 {len(content) // 1024} KB）。",
        )

    # ── Store file ─────────────────────────────────────────────
    ext       = Path(file.filename or "upload").suffix.lower()
    server_fn = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / server_fn
    file_path.write_bytes(content)

    # ── DB record ──────────────────────────────────────────────
    mat = CourseMaterial(
        course_id         = course.id,
        user_id           = current_user.id,
        filename          = server_fn,
        original_filename = file.filename or server_fn,
        content_type      = content_type,
        file_size         = len(content),
        extraction_status = "pending",
    )
    db.add(mat)
    db.commit()
    db.refresh(mat)

    # ── Background text extraction ─────────────────────────────
    background_tasks.add_task(
        _extract_and_update,
        mat_id=mat.id,
        content=content,
        content_type=content_type,
        filename=file.filename or server_fn,
    )

    logger.info("教材上传成功 mat_id=%d course_id=%d file=%s", mat.id, course.id, server_fn)
    return mat


async def _extract_and_update(
    mat_id: int,
    content: bytes,
    content_type: str,
    filename: str,
) -> None:
    """后台任务：提取文本并更新 extraction_status。"""
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        mat = db.query(CourseMaterial).filter(CourseMaterial.id == mat_id).first()
        if not mat:
            return

        mat.extraction_status = "processing"
        db.commit()

        try:
            text = extract_text(content, content_type, filename)
            mat.text_content      = text
            mat.extraction_status = "ready"
            mat.error_message     = None
        except ExtractionError as exc:
            mat.extraction_status = "error"
            mat.error_message     = str(exc)
            logger.warning("文本提取失败 mat_id=%d: %s", mat_id, exc)
        except Exception as exc:
            mat.extraction_status = "error"
            mat.error_message     = f"内部错误：{exc}"
            logger.exception("文本提取意外失败 mat_id=%d", mat_id)

        db.commit()
    finally:
        db.close()


@router.get(
    "/courses/{course_id}/materials",
    response_model=CourseMaterialListResponse,
    summary="获取课程教材列表",
)
def list_materials(
    course_id:    int,
    db:           Session = Depends(get_db),
    current_user  = Depends(get_current_user),
):
    _get_course_for_user(course_id, current_user, db)
    materials = (
        db.query(CourseMaterial)
        .filter(CourseMaterial.course_id == course_id)
        .order_by(CourseMaterial.created_at.desc())
        .all()
    )
    return CourseMaterialListResponse(materials=materials, total=len(materials))


@router.delete(
    "/courses/{course_id}/materials/{mat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除课程教材",
)
def delete_material(
    course_id:   int,
    mat_id:      int,
    db:          Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    _get_course_for_user(course_id, current_user, db)
    mat = _get_material(mat_id, course_id, current_user, db)

    # 删除磁盘文件（忽略不存在错误）
    file_path = UPLOAD_DIR / mat.filename
    file_path.unlink(missing_ok=True)

    db.delete(mat)
    db.commit()


# ══════════════════════════════════════════════════════════════
#  AI 课时切分
# ══════════════════════════════════════════════════════════════

@router.post(
    "/courses/{course_id}/generate-units",
    response_model=GenerateUnitsResponse,
    summary="AI 生成课时切分",
)
async def generate_units(
    course_id:   int,
    body:        GenerateUnitsRequest,
    db:          Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    触发 AI 课时切分，将课程教材内容智能分割为结构化学习单元。

    - `material_ids` 为空时使用该课程下全部已就绪教材
    - `overwrite=true` 删除现有草稿后重新生成
    - 需要用户在设置页配置 API Key
    - 大教材（> 60K token）会自动截断并在 warnings 中告知
    """
    course = _get_course_for_user(course_id, current_user, db)

    return await generate_learning_units(
        db=db,
        course=course,
        user=current_user,
        material_ids=body.material_ids,
        target_unit_count=body.target_unit_count,
        overwrite=body.overwrite,
    )


# ══════════════════════════════════════════════════════════════
#  学习单元 CRUD
# ══════════════════════════════════════════════════════════════

@router.get(
    "/courses/{course_id}/units",
    response_model=LearningUnitsListResponse,
    summary="获取课程学习单元列表",
)
def list_units(
    course_id:    int,
    status_filter: Optional[str] = Query(None, alias="status"),
    db:           Session = Depends(get_db),
    current_user  = Depends(get_current_user),
):
    """
    列出课程下的学习单元，按 unit_index 升序排列。
    `status` 查询参数可过滤：draft | ready | archived
    """
    _get_course_for_user(course_id, current_user, db)

    query = (
        db.query(LearningUnit)
        .filter(LearningUnit.course_id == course_id)
    )
    if status_filter:
        query = query.filter(LearningUnit.status == status_filter)

    units = query.order_by(LearningUnit.unit_index).all()
    return LearningUnitsListResponse(units=units, total=len(units))


@router.patch(
    "/courses/{course_id}/units/{unit_id}",
    response_model=LearningUnitResponse,
    summary="编辑学习单元",
)
def update_unit(
    course_id:   int,
    unit_id:     int,
    body:        LearningUnitUpdate,
    db:          Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """部分更新学习单元（所有字段可选）。"""
    _get_course_for_user(course_id, current_user, db)
    unit = _get_unit(unit_id, course_id, db)

    update_data = body.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(unit, field, value)

    db.commit()
    db.refresh(unit)
    return unit


@router.patch(
    "/courses/{course_id}/units/{unit_id}/status",
    response_model=LearningUnitResponse,
    summary="修改学习单元状态",
)
def update_unit_status(
    course_id:   int,
    unit_id:     int,
    new_status:  str = Query(..., alias="status"),
    db:          Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    快捷修改单元状态：draft → ready（发布）| ready → archived（归档）
    """
    from backend.models.learning_unit import UNIT_STATUSES
    if new_status not in {"draft", "ready", "archived"}:
        raise HTTPException(status_code=422, detail=f"无效状态值 '{new_status}'。")

    _get_course_for_user(course_id, current_user, db)
    unit = _get_unit(unit_id, course_id, db)
    unit.status = new_status
    db.commit()
    db.refresh(unit)
    return unit


@router.delete(
    "/courses/{course_id}/units/{unit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除学习单元",
)
def delete_unit(
    course_id:   int,
    unit_id:     int,
    db:          Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    _get_course_for_user(course_id, current_user, db)
    unit = _get_unit(unit_id, course_id, db)
    db.delete(unit)
    db.commit()
