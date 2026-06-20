"""Textbook-first learning plan draft APIs."""

from __future__ import annotations

from typing import Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from backend.api.routes.auth import get_current_user
from backend.db.database import get_db
from backend.models.models import (
    Course,
    CourseProgress,
    LessonPlan,
    LearningPlanDraft,
    Textbook,
    TextbookLibrary,
    User,
    World,
)
from backend.services.learning_plan_drafts import persist_draft, build_learning_plan_blueprint

router = APIRouter()


class LearningPlanDraftCreateRequest(BaseModel):
    material_ids: list[int] = Field(default_factory=list)
    goal: str = Field(..., min_length=4, max_length=500)
    course_form: dict[str, Any] | None = None


class LearningPlanDraftUpdateRequest(BaseModel):
    goal: str | None = None
    course_form: dict[str, Any] | None = None
    material_ids: list[int] | None = None


class LearningPlanDraftCommitRequest(BaseModel):
    course_name: str | None = None
    description: str | None = None
    target_level: str | None = None
    world_name: str | None = None
    world_description: str | None = None
    commit_world: bool = True


class LearningPlanDraftResponse(BaseModel):
    id: int
    user_id: int
    material_ids: list[int]
    goal: str
    course_form: dict[str, Any] | None = None
    material_analysis: dict[str, Any] | None = None
    knowledge_blueprint: dict[str, Any] | None = None
    course_blueprint: dict[str, Any] | None = None
    course_narrative_plan: dict[str, Any] | None = Field(default=None, validation_alias="world_plan")
    character_plan: dict[str, Any] | None = None
    stage: str
    committed_world_id: int | None = None
    committed_course_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class LearningPlanDraftCommitResponse(BaseModel):
    draft_id: int
    world_id: int
    course_id: int
    lesson_count: int
    linked_textbook_count: int


def _get_draft_for_user(db: Session, draft_id: int, user_id: int) -> LearningPlanDraft:
    draft = db.query(LearningPlanDraft).filter(
        LearningPlanDraft.id == draft_id,
        LearningPlanDraft.user_id == user_id,
    ).first()
    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")
    return draft


def _resolve_library_items(db: Session, user_id: int, material_ids: list[int]) -> list[TextbookLibrary]:
    if not material_ids:
        raise HTTPException(status_code=400, detail="至少需要选择一个教材")
    items = db.query(TextbookLibrary).filter(
        TextbookLibrary.user_id == user_id,
        TextbookLibrary.id.in_(material_ids),
    ).order_by(TextbookLibrary.created_at.asc()).all()
    found_ids = {item.id for item in items}
    missing = [mid for mid in material_ids if mid not in found_ids]
    if missing:
        raise HTTPException(status_code=404, detail=f"教材不存在: {missing[0]}")
    unusable = [item.filename for item in items if not item.is_usable]
    if unusable:
        raise HTTPException(status_code=400, detail=f"教材不可用: {', '.join(unusable[:3])}")
    return items


@router.post("/learning-plans/drafts", response_model=LearningPlanDraftResponse)
def create_learning_plan_draft(
    req: LearningPlanDraftCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    library_items = _resolve_library_items(db, current_user.id, req.material_ids)
    draft = LearningPlanDraft(user_id=current_user.id, goal=req.goal)
    persist_draft(
        draft,
        user_id=current_user.id,
        goal=req.goal,
        course_form=req.course_form or {},
        library_items=library_items,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


@router.get("/learning-plans/drafts/{draft_id}", response_model=LearningPlanDraftResponse)
def get_learning_plan_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_draft_for_user(db, draft_id, current_user.id)


@router.put("/learning-plans/drafts/{draft_id}", response_model=LearningPlanDraftResponse)
def update_learning_plan_draft(
    draft_id: int,
    req: LearningPlanDraftUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    draft = _get_draft_for_user(db, draft_id, current_user.id)
    goal = req.goal or draft.goal
    course_form = req.course_form if req.course_form is not None else (draft.course_form or {})
    material_ids = req.material_ids if req.material_ids is not None else list(draft.material_ids or [])
    library_items = _resolve_library_items(db, current_user.id, material_ids)
    persist_draft(
        draft,
        user_id=current_user.id,
        goal=goal,
        course_form=course_form,
        library_items=library_items,
    )
    db.commit()
    db.refresh(draft)
    return draft


@router.post("/learning-plans/drafts/{draft_id}/regenerate", response_model=LearningPlanDraftResponse)
def regenerate_learning_plan_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    draft = _get_draft_for_user(db, draft_id, current_user.id)
    library_items = _resolve_library_items(db, current_user.id, list(draft.material_ids or []))
    persist_draft(
        draft,
        user_id=current_user.id,
        goal=draft.goal,
        course_form=draft.course_form or {},
        library_items=library_items,
    )
    db.commit()
    db.refresh(draft)
    return draft


@router.post("/learning-plans/drafts/{draft_id}/commit", response_model=LearningPlanDraftCommitResponse)
def commit_learning_plan_draft(
    draft_id: int,
    req: LearningPlanDraftCommitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    draft = _get_draft_for_user(db, draft_id, current_user.id)
    if draft.committed_course_id:
        return LearningPlanDraftCommitResponse(
            draft_id=draft.id,
            world_id=draft.committed_world_id or 0,
            course_id=draft.committed_course_id,
            lesson_count=db.query(LessonPlan).filter(LessonPlan.course_id == draft.committed_course_id).count(),
            linked_textbook_count=db.query(Textbook).filter(Textbook.course_id == draft.committed_course_id).count(),
        )

    library_items = _resolve_library_items(db, current_user.id, list(draft.material_ids or []))
    if draft.material_analysis and draft.knowledge_blueprint and draft.course_blueprint and draft.world_plan:
        blueprint = {
            "material_analysis": draft.material_analysis,
            "knowledge_blueprint": draft.knowledge_blueprint,
            "course_blueprint": draft.course_blueprint,
            "course_narrative_plan": draft.world_plan,
            "character_plan": draft.character_plan or {},
        }
    else:
        blueprint = build_learning_plan_blueprint(
            draft=draft,
            library_items=library_items,
            goal=draft.goal,
            course_form=draft.course_form or {},
        )

    course_narrative_plan = blueprint.get("course_narrative_plan") or {}
    world_name = req.world_name or (course_narrative_plan["world"]["name"] if course_narrative_plan else f"{blueprint['course_blueprint']['course_title']}学习世界")
    world_description = req.world_description or f"围绕《{blueprint['material_analysis']['title']}》构建的学习容器。"

    world = World(
        user_id=current_user.id,
        name=world_name,
        description=world_description,
    )
    db.add(world)
    db.flush()

    course_title = req.course_name or blueprint["course_blueprint"]["course_title"]
    course = Course(
        world_id=world.id,
        name=course_title,
        description=req.description or draft.goal,
        target_level=req.target_level or "understand",
        meta={
            "setup_flow": "textbook_first_v1",
            "draft_id": draft.id,
            "material_ids": list(draft.material_ids or []),
            "material_analysis": blueprint["material_analysis"],
            "knowledge_blueprint": blueprint["knowledge_blueprint"],
            "course_blueprint": blueprint["course_blueprint"],
            "course_narrative_plan": course_narrative_plan,
            "character_plan": blueprint["character_plan"],
            "stage": "course_committed",
        },
    )
    db.add(course)
    db.flush()

    linked_count = 0
    for item in library_items:
        textbook = Textbook(
            course_id=course.id,
            user_id=current_user.id,
            library_id=item.id,
            filename=item.filename,
            file_path=item.file_path,
            file_size=item.file_size,
            content_type=item.content_type,
            extracted_text=item.extracted_text,
            page_count=item.page_count,
            status="extracted",
            owns_file=False,
        )
        db.add(textbook)
        linked_count += 1

    for unit in blueprint["course_blueprint"]["units"]:
        db.add(
            LessonPlan(
                course_id=course.id,
                title=unit["title"],
                description=unit["description"],
                order_index=unit["order_index"],
                concepts=unit["concepts"],
                prerequisites=unit["prerequisites"],
                content="",
            ),
        )

    db.add(
        CourseProgress(
            course_id=course.id,
            user_id=current_user.id,
            current_lesson_index=0,
            completed_lesson_ids=[],
        ),
    )

    draft.stage = "course_committed"
    draft.committed_world_id = world.id
    draft.committed_course_id = course.id
    db.commit()

    return LearningPlanDraftCommitResponse(
        draft_id=draft.id,
        world_id=world.id,
        course_id=course.id,
        lesson_count=len(blueprint["course_blueprint"]["units"]),
        linked_textbook_count=linked_count,
    )


@router.put("/learning-plans/drafts/{draft_id}/world", response_model=LearningPlanDraftResponse)
def update_learning_plan_world(
    draft_id: int,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    draft = _get_draft_for_user(db, draft_id, current_user.id)
    draft.world_plan = {
        **(draft.world_plan or {}),
        **payload,
    }

    if draft.committed_world_id:
        world = db.query(World).filter(
            World.id == draft.committed_world_id,
            World.user_id == current_user.id,
        ).first()
        if not world:
            raise HTTPException(status_code=404, detail="世界不存在")
        world_section = draft.world_plan.get("world", {})
        if world_section.get("name"):
            world.name = world_section["name"]
        if world_section.get("premise") or world_section.get("description"):
            world.description = world_section.get("description") or world_section.get("premise")
        if draft.committed_course_id:
            course = db.query(Course).filter(
                Course.id == draft.committed_course_id,
                Course.world_id == world.id,
            ).first()
            if course:
                meta = dict(course.meta or {})
                meta["course_narrative_plan"] = draft.world_plan
                course.meta = meta

    db.commit()
    db.refresh(draft)
    return draft
