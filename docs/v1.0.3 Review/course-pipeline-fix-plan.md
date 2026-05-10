# 课程管线修复方案：打通 AI 生成 → 存储 → 消费全链路

> 创建日期: 2026-05-04
> 状态: 待实施（所有讨论已决议）

## 1. 问题描述

### 1.1 现状

AI 生成课程后，所有数据塞在 `Course.meta` 这一个 JSON 字段里，导致：

| 问题 | 说明 |
|------|------|
| 数据混杂 | `meta` 同时存了 AI 生成内容、用户表单偏好、教学进度三类完全不同的数据 |
| 已有表未使用 | `LessonPlan` 表已建好但 0 行数据，AI 生成的 lessons 塞进 JSON |
| 不可查询 | 无法 SQL 查询"某节课的概念"或"某概念在哪些课程中出现" |
| 更新粒度粗 | 更新一节课需要读、改、写回整个 JSON blob |
| 孤岛数据 | AI 生成的 `concept_map` 几乎没被下游系统使用 |

### 1.2 数据流（当前 — 断裂）

```
CourseGenerator → textbook.py 存入 meta JSON
  ↓ (断裂：LessonPlan 表空着)
TeachingPlanner ← 读 meta JSON (绕过 LessonPlan)
prompt_builder  ← 读 meta JSON (绕过 LessonPlan)
learning_engine ← 完全不引用课程内容
```

### 1.3 数据流（目标 — 接通）

```
CourseGenerator → textbook.py 写入 LessonPlan 表 + course.description
  ↓
TeachingPlanner ← 读 LessonPlan 表 ✓
prompt_builder  ← 读 context["lessons"] (调用方传入) ✓
learning_engine ← 未来可引用 concept_map 做个性化路径
```

---

## 2. 修复步骤

### 第 1 步：升级 `LessonPlan` 模型 + 设计进度存储

#### 2.1.1 涉及文件

| 文件 | 改动 |
|------|------|
| `backend/models/models.py` L236-244 | 重写 `LessonPlan` 类 |
| `backend/models/models.py` L215-232 | `Course` 类 meta 注释更新 |
| `backend/alembic/versions/` | 新建 migration 文件 |

#### 2.1.2 当前 `LessonPlan`（需替换）

```python
# backend/models/models.py:236
class LessonPlan(Base):
    __tablename__ = "lesson_plans"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    content = Column(Text, nullable=False)        # 只有这一个字段
    created_at = Column(DateTime, default=_utcnow)
```

#### 2.1.3 新 `LessonPlan`

```python
class LessonPlan(Base):
    """课程章节（DAG 节点）"""
    __tablename__ = "lesson_plans"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    order_index = Column(Integer, nullable=False, default=0)   # 拓扑排序序号
    concepts = Column(JSON, nullable=True, default=list)        # ["概念1", "概念2"]
    prerequisites = Column(JSON, nullable=True, default=list)   # [lesson_id, ...] DAG 边
    content = Column(Text, nullable=True)                       # 教师笔记
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    course = orm_relationship("Course", back_populates="lesson_plans")
```

#### 2.1.4 进度存储设计

当前进度存储在 `course.meta["current_lesson_index"]` 和 `course.meta["completed_lessons"]`。

**方案**：新增 `CourseProgress` 表（每个用户每门课一行）：

```python
class CourseProgress(Base):
    """课程学习进度（用户级别）"""
    __tablename__ = "course_progress"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    current_lesson_id = Column(Integer, ForeignKey("lesson_plans.id"), nullable=True)
    completed_lesson_ids = Column(JSON, nullable=True, default=list)  # [lesson_id, ...]
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # unique constraint: 每用户每课程只有一行
    __table_args__ = (
        UniqueConstraint("course_id", "user_id", name="uq_course_progress_user"),
    )
```

#### 2.1.5 操作

1. 修改 `backend/models/models.py` — 重写 `LessonPlan`，新增 `CourseProgress`
2. 运行 `alembic revision --autogenerate -m "upgrade_lesson_plan_add_course_progress"`
3. 运行 `alembic upgrade head`

> **讨论区** ✅ 已决议
>
> - `content` 字段 → 保留（owner: 需要）
> - `updated_at` → 添加（可编辑 title/description/concepts/content）
> - 图结构 → lessons 是 DAG 节点，prerequisites 是边（owner 提议）
> - concept_map 保留在 `course.meta["concept_map"]` 辅助 prompt_builder
> - 进度数据 → 本次一起迁移，新增 `CourseProgress` 表（owner: 是）

---

### 第 2 步：改写课程生成流程（`textbook.py`）

#### 2.2.1 涉及文件

| 文件 | 行号 | 改动 |
|------|------|------|
| `backend/api/routes/textbook.py` | L715-740 | `generate_course_from_textbooks` 生成后写入逻辑 |
| `backend/api/routes/textbook.py` | L582-620 | `clear_generated_content` 清空逻辑 |
| `backend/api/routes/textbook.py` | L648-653 | 409 检查逻辑（检测 meta.generated_lessons → 改为检测 LessonPlan 行） |

#### 2.2.2 `generate_course_from_textbooks`（L715-740）具体改动

**当前代码**：
```python
# L715-740: 全部塞进 meta JSON
course.meta["generated_overview"] = result.get("overview", "")
course.meta["generated_lessons"] = [l.model_dump() for l in result.get("lessons", [])]
course.meta["concept_map"] = result.get("concept_map")
flag_modified(course, "meta")
```

**替换为**：
```python
from backend.models.models import LessonPlan

# 1. overview → course.description
if result.get("overview"):
    course.description = result["overview"]

# 2. 删除旧 LessonPlan 行（支持重新生成）
db.query(LessonPlan).filter(LessonPlan.course_id == course_id).delete()

# 3. lessons → LessonPlan 行
for lesson in result.get("lessons", []):
    db_lesson = LessonPlan(
        course_id=course_id,
        title=lesson.title,
        description=lesson.description,
        order_index=lesson.order,
        concepts=lesson.concepts,
        prerequisites=lesson.prerequisites,  # 暂存 title 列表，后续可解析为 id
    )
    db.add(db_lesson)

# 4. concept_map → 保留在 meta
course.meta["concept_map"] = result.get("concept_map")

# 5. 清理 meta 中旧的 generated 字段
course.meta.pop("generated_lessons", None)
course.meta.pop("generated_overview", None)
flag_modified(course, "meta")
```

#### 2.2.3 `clear_generated_content`（L582-620）具体改动

**当前代码**：从 `course.meta` 中删除 generated_overview/generated_lessons/current_lesson_index/completed_lessons

**替换为**：
```python
# 删除 LessonPlan 行
db.query(LessonPlan).filter(LessonPlan.course_id == course_id).delete()

# 清理 meta
for key in ["generated_overview", "generated_lessons", "concept_map",
            "current_lesson_index", "completed_lessons"]:
    course.meta.pop(key, None)
flag_modified(course, "meta")
```

#### 2.2.4 409 检查（L648-653）改动

**当前**：`if existing_meta.get("generated_lessons")`
**替换为**：`if db.query(LessonPlan).filter(LessonPlan.course_id == course_id).count() > 0`

> **讨论区** ✅ 已决议
>
> - 重新生成 → 删除旧 LessonPlan 行重新写入（owner: 不需要保留）
> - overview → 写入 `course.description`（owner: 不单独存，用户可二次编辑覆盖）
> - concept_map → 保留在 meta（DAG 主结构由 LessonPlan 承载）

---

### 第 3 步：改写 `TeachingPlanner` 读取源 + 进度迁移

#### 2.3.1 涉及文件

| 文件 | 行号 | 改动 |
|------|------|------|
| `backend/services/teaching_planner.py` | L29-48 | `get_current_lesson` — 改签名加 `db`，改读 LessonPlan |
| `backend/services/teaching_planner.py` | L51-120 | `get_progress` — 改读 LessonPlan + CourseProgress |
| `backend/services/teaching_planner.py` | L117-158 | `advance_lesson` — 改写 CourseProgress 而非 meta |
| `backend/services/teaching_planner.py` | L160-188 | `set_lesson` — 同上 |
| `backend/services/teaching_planner.py` | L189-230 | `_record_lesson_progress` — 改读 LessonPlan |
| `backend/api/routes/textbook.py` | L768-769 | `get_progress` 调用方（已是 `teaching_planner.get_progress(db, course)` 无需改） |
| `backend/api/routes/textbook.py` | L782-783 | `advance_lesson` 调用方（已传 `db`，无需改） |
| `backend/api/routes/textbook.py` | L823-824 | `set_lesson` 调用方（已传 `db`，无需改） |

#### 2.3.2 方法签名变更

```python
# 当前
def get_current_lesson(self, course: Course) -> dict | None:

# 改为
def get_current_lesson(self, db: Session, course: Course) -> dict | None:
```

**调用方搜索**：`grep -rn "get_current_lesson" backend/` 确认所有调用方传入 `db`。

#### 2.3.3 数据读取变更（7 处 `course.meta.get("generated_lessons")` 全部替换）

```python
# 当前（出现 7 次）
lessons = course.meta.get("generated_lessons", [])

# 替换为
from backend.models.models import LessonPlan
lesson_rows = db.query(LessonPlan).filter(
    LessonPlan.course_id == course.id
).order_by(LessonPlan.order_index).all()
lessons = [
    {"title": lp.title, "description": lp.description,
     "order": lp.order_index, "concepts": lp.concepts or [],
     "prerequisites": lp.prerequisites or []}
    for lp in lesson_rows
]
```

#### 2.3.4 进度读写变更

```python
# 当前（读写 course.meta）
current_idx = course.meta.get("current_lesson_index", 0)
completed = course.meta.get("completed_lessons", [])
course.meta["current_lesson_index"] = next_idx
course.meta["completed_lessons"] = sorted(completed)
flag_modified(course, "meta")

# 替换为（读写 CourseProgress 表）
from backend.models.models import CourseProgress
progress = db.query(CourseProgress).filter(
    CourseProgress.course_id == course.id,
    CourseProgress.user_id == user_id,  # 需要传入 user_id
).first()
if not progress:
    progress = CourseProgress(course_id=course.id, user_id=user_id)
    db.add(progress)
current_idx = ... # 从 progress.current_lesson_id 推算
completed = progress.completed_lesson_ids or []
progress.current_lesson_id = lesson_rows[next_idx].id
progress.completed_lesson_ids = sorted(completed_ids)
```

> **讨论区** ✅ 已决议
>
> - 进度数据 → 本次迁移到 `CourseProgress` 表
> - `get_current_lesson` → 添加 `db` 参数
> - 进度操作需要 `user_id`（方法签名可能需要额外参数）

---

### 第 4 步：改写 `prompt_builder/course_content.py`（方案 B）

#### 2.4.1 涉及文件

| 文件 | 行号 | 改动 |
|------|------|------|
| `backend/services/prompt_builder/modules/course_content.py` | L30-50 | `is_applicable` / `should_include` — 改检测 LessonPlan 行 |
| `backend/services/prompt_builder/modules/course_content.py` | L53-88 | `assemble` — 从 `context["lessons"]` 读取而非查 meta |
| `backend/services/learning_engine.py` | L150-168 | 构建 context dict — 新增 `lessons` key |
| `backend/services/prompt_builder/builder.py` | L87- | `PromptBuilder.build` — context 透传 |

#### 2.4.2 调用链

```
learning_engine.py (L150-168) 构建 context dict
  → {"db": db, "course_id": ..., "lessons": [...]}  ← 新增 lessons
    → PromptBuilder.build(context=context)
      → CourseContentModule.assemble(context)
        → lessons = context.get("lessons", [])  ← 不再自己查 DB
```

#### 2.4.3 `learning_engine.py` 改动（新增 lessons 到 context）

```python
# L150-168 当前
context = {
    "db": db,
    "world_id": session.world_id,
    "session_id": session.id,
    "course_id": session.course_id,
    ...
}

# 改为：在构建 context 前查好 lessons
from backend.models.models import LessonPlan
lesson_rows = db.query(LessonPlan).filter(
    LessonPlan.course_id == session.course_id
).order_by(LessonPlan.order_index).all()

lessons_data = [
    {"title": lp.title, "description": lp.description,
     "order": lp.order_index, "concepts": lp.concepts or []}
    for lp in lesson_rows
]

context = {
    "db": db,
    ...
    "lessons": lessons_data,  # 新增
}
```

#### 2.4.4 `course_content.py` 改动

```python
# L53-88 当前
def assemble(self, context: dict) -> str:
    db = context.get("db")
    course_id = context.get("course_id")
    course = db.query(Course).filter(Course.id == course_id).first()
    meta = course.meta
    lessons = meta.get("generated_lessons", [])    # 从 meta 读
    concept_map = meta.get("concept_map")

# 改为
def assemble(self, context: dict) -> str:
    db = context.get("db")
    course_id = context.get("course_id")
    course = db.query(Course).filter(Course.id == course_id).first()
    lessons = context.get("lessons", [])            # 从 context 读（调用方已查好）
    concept_map = (course.meta or {}).get("concept_map")  # concept_map 仍从 meta 读
```

> **讨论区** ✅ 已决议
>
> - 方案 B（owner 确认）：调用方查好 lessons 传入 context，prompt_builder 不直接查 DB
> - concept_map 继续从 `course.meta` 读取

---

### 第 5 步：添加 Lesson API 端点

#### 2.5.1 涉及文件

| 文件 | 改动 |
|------|------|
| `backend/api/routes/courses.py` | **新建** — Lesson CRUD 端点 |
| `backend/main.py` L87 后 | 新增 `app.include_router(courses.router, prefix="/api", tags=["courses"])` |
| `backend/api/routes/__init__.py` | 如有 router 注册需更新 |

#### 2.5.2 新建 `backend/api/routes/courses.py`

```python
"""Lesson & Course Progress API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.core.security import get_current_user
from backend.models.models import LessonPlan, CourseProgress, Course, User

router = APIRouter()

# ── Pydantic Schemas ──

class LessonResponse(BaseModel):
    id: int
    title: str
    description: str | None
    order_index: int
    concepts: list[str]
    prerequisites: list  # id 列表或 title 列表
    content: str | None
    class Config:
        from_attributes = True

class LessonUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    concepts: list[str] | None = None
    content: str | None = None

class ProgressResponse(BaseModel):
    current_lesson: LessonResponse | None
    completed_lesson_ids: list[int]
    total_lessons: int
    progress_pct: float

# ── Endpoints ──

@router.get("/courses/{course_id}/lessons")
def list_lessons(course_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """返回课程的所有 lesson（按 order_index 排序）"""
    # auth check: course belongs to user's world
    _auth_course(course_id, db, current_user)
    rows = db.query(LessonPlan).filter(
        LessonPlan.course_id == course_id
    ).order_by(LessonPlan.order_index).all()
    return rows

@router.get("/courses/{course_id}/lessons/{lesson_id}")
def get_lesson(course_id: int, lesson_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """返回单个 lesson 详情"""
    _auth_course(course_id, db, current_user)
    lesson = db.query(LessonPlan).filter(
        LessonPlan.id == lesson_id, LessonPlan.course_id == course_id
    ).first()
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    return lesson

@router.put("/courses/{course_id}/lessons/{lesson_id}")
def update_lesson(course_id: int, lesson_id: int, req: LessonUpdateRequest,
                  db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """编辑单个 lesson"""
    _auth_course(course_id, db, current_user)
    lesson = db.query(LessonPlan).filter(
        LessonPlan.id == lesson_id, LessonPlan.course_id == course_id
    ).first()
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    if req.title is not None: lesson.title = req.title
    if req.description is not None: lesson.description = req.description
    if req.concepts is not None: lesson.concepts = req.concepts
    if req.content is not None: lesson.content = req.content
    db.commit()
    db.refresh(lesson)
    return lesson

@router.get("/courses/{course_id}/progress")
def get_course_progress(course_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """获取课程教学进度"""
    from backend.services.teaching_planner import teaching_planner
    course = _auth_course(course_id, db, current_user)
    return teaching_planner.get_progress(db, course, current_user.id)

def _auth_course(course_id, db, current_user):
    course = db.query(Course).join(World, ...).filter(...).first()
    if not course:
        raise HTTPException(404, "Course not found")
    return course
```

#### 2.5.3 `main.py` 注册

```python
# backend/main.py L88 后新增
from backend.api.routes import courses
app.include_router(courses.router, prefix="/api", tags=["courses"])
```

> **讨论区** ✅ 已决议
>
> - API 位置 → 新建 `courses.py`（archive.py 已太大）
> - PUT 编辑 lesson → 做
> - 批量重排 → 先不做

---

### 第 6 步：前端 CoursePage 接入 + UI 升级

#### 2.6.1 涉及文件

| 文件 | 改动 |
|------|------|
| `frontend/src/api/course.ts` | 新增 `getLessons()`, `getLesson()`, `updateLesson()` |
| `frontend/src/views/CoursePage.vue` L397-400 | 改从 API 加载 lessons 而非 `course.meta.generated_lessons` |
| `frontend/src/views/CoursePage.vue` | UI 升级：lesson 列表/折叠面板/概念标签/进度指示 |
| `frontend/src/components/CreateCourseModal.vue` L472,545,572 | 生成后不再存本地 ref，改为刷新课程数据 |

#### 2.6.2 `frontend/src/api/course.ts` 新增

```typescript
/** 获取课程 lesson 列表 */
getLessons: (courseId: number) =>
  client.get(`/courses/${courseId}/lessons`).then(res => res.data),

/** 获取单个 lesson */
getLesson: (courseId: number, lessonId: number) =>
  client.get(`/courses/${courseId}/lessons/${lessonId}`).then(res => res.data),

/** 编辑 lesson */
updateLesson: (courseId: number, lessonId: number, data: {
  title?: string; description?: string; concepts?: string[]; content?: string
}) =>
  client.put(`/courses/${courseId}/lessons/${lessonId}`, data).then(res => res.data),
```

#### 2.6.3 `CoursePage.vue` 改动

```typescript
// L397-400 当前
const lessons = course.value?.meta?.generated_lessons

// 改为：onMounted 时从 API 加载
const lessons = ref([])
async function loadLessons() {
  lessons.value = await courseApi.getLessons(courseId)
}
```

#### 2.6.4 `CreateCourseModal.vue` 改动

```typescript
// L472 当前：生成后 result 存在本地 ref
const generatedResult = ref<{ overview: string; lessons: any[]; concept_map?: any } | null>(null)

// L545/572 当前：把 result 存到 generatedResult
// 改为：生成成功后调用 courseApi.getLessons(courseId) 获取 lessons
// 同时 courseApi.get(courseId) 刷新课程数据（description 已被后端更新）
```

> **讨论区** ✅ 已决议
>
> - UI → 本次升级
> - CreateCourseModal → 数据源统一从后端 API 获取

---

## 3. 实施顺序与依赖关系

```
第 1 步（模型升级 + CourseProgress 表）
  ↓
第 2 步（生成流程改写） ← 依赖第 1 步
  ↓
第 3 步（TeachingPlanner + 进度迁移） ← 依赖第 1、2 步
  ↓
第 4 步（prompt_builder） ← 依赖第 2 步（可与第 3 步并行）
  ↓
第 5 步（API 端点） ← 依赖第 1 步（可与第 2-4 步并行）
  ↓
第 6 步（前端接入 + UI 升级） ← 依赖第 5 步
```

---

## 4. 风险与注意事项

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 已有课程数据迁移 | Course 2 有 generated_lessons 需迁移 | 一次性迁移脚本 |
| meta 字段清理 | 删除 generated_lessons 后旧代码报错 | 第 2-4 步同一次发布 |
| TeachingPlanner 签名变更 | `get_current_lesson` 需加 `db` + `user_id` | grep 所有调用方 |
| 进度存储迁移 | current_lesson_index 迁到 CourseProgress | 第 3 步一起做 |
| 前后端不同步 | 前端读 meta.generated_lessons 为空 | 第 6 步与后端同步 |

---

## 5. 数据迁移计划

### 5.1 迁移脚本 `scripts/migrate_lessons_to_db.py`

```python
"""一次性迁移：course.meta → LessonPlan 表 + CourseProgress 表"""
import json
from backend.db.database import SessionLocal
from backend.models.models import Course, LessonPlan, CourseProgress, User
from sqlalchemy.orm.attributes import flag_modified

def migrate():
    db = SessionLocal()
    courses = db.query(Course).all()
    for course in courses:
        meta = course.meta or {}
        lessons_data = meta.pop("generated_lessons", None)
        if not lessons_data:
            continue

        # 1. lessons → LessonPlan 行
        for lesson in lessons_data:
            db.add(LessonPlan(
                course_id=course.id,
                title=lesson["title"],
                description=lesson.get("description"),
                order_index=lesson.get("order", 0),
                concepts=lesson.get("concepts", []),
                prerequisites=lesson.get("prerequisites", []),
            ))

        # 2. overview → course.description
        overview = meta.pop("generated_overview", None)
        if overview and not course.description:
            course.description = overview

        # 3. 进度 → CourseProgress（如果有）
        user_id = ...  # 从 world.user_id 获取
        current_idx = meta.pop("current_lesson_index", 0)
        completed = meta.pop("completed_lessons", [])
        if current_idx or completed:
            db.add(CourseProgress(
                course_id=course.id,
                user_id=user_id,
                current_lesson_index=current_idx,
                completed_lesson_ids=completed,
            ))

        flag_modified(course, "meta")
    db.commit()

if __name__ == "__main__":
    migrate()
```

### 5.2 迁移讨论

> - 迁移脚本形式 → 独立 `scripts/migrate_lessons_to_db.py`（方便手动运行和调试）
> - 迁移前 → 备份数据库 `cp data/socratic_learning.db data/socratic_learning.db.bak`
> - alembic migration 只负责 DDL（表结构变更），数据迁移用脚本

