# Lesson Progress 单源化 — Seam A2 实施指导

> **版本**：v1.0.5 · rev.1  
> **日期**：2026-06-29  
> **别名**：Seam A2 / B2b `lesson-progress cleanup`  
> **上级文档**：[pr0_collaboration_gate.md](./pr0_collaboration_gate.md) · [boundary_diff_inventory.md](./boundary_diff_inventory.md) §4  
> **前置 seam**：Seam A（ProgressFacade，已合并）· Seam B（archive 拆分，进行中/已 PR）

---

## 1. 定位

Seam A 完成了 **concept 掌握度 / FSRS 调度** 的主存储迁移，以及 **archive `/progress*` 写路径** 对 `ProgressTracking` 新 INSERT 的运行时阻断。

Seam A **没有**完成 **lesson 章节进度（lesson pointer）** 的单源化。当前系统里：

| 层 | 主表（目标 canonical） | 实际状态 |
|----|------------------------|----------|
| lesson 章节进度 | `CourseProgress` | 与 `course.meta` **双源读写** |
| concept 掌握度 | `ConceptMastery` | 主写较一致 |
| review 调度 | `FSRSState` | 主写较一致 |
| compat 旧面 | `ProgressTracking` | 写被 flag 挡住；读仍在多处 |

**Seam A2 的唯一目标**：把 Seam A 未完成的「lesson pointer 单源化」做完整。  
**不是** Seam C（profile/report 边界）或 Seam D（前端 store 拆分）的替代品。

---

## 2. 问题证据（Observed · HARD）

以下路径在 `main`（含 Seam A）上可核对。

### 2.1 读路径：CourseProgress 优先，无则回退 meta

`backend/services/teaching_planner.py`

- `_get_current_index()` · L71–80  
- `_get_completed()` · L82–91  

### 2.2 写路径 A：手动 / API 推进 → CourseProgress

- `advance_lesson()` · L227–231  
- `set_lesson()` · L272–275  

### 2.3 写路径 B：对话自动推进 → 仅 course.meta

`backend/services/mastery_tracker.py`

- `update_from_memories()` 判定当前课节 · L120–122（裸读 `course.meta`）  
- `_try_auto_advance()` · L195–217（只写 `course.meta`）

### 2.4 运行时后果（BEHAVIOR 级风险）

当某课程 **已有 `CourseProgress` 行** 时：

1. `teaching_planner.get_progress()` **读 CourseProgress**  
2. 自动推进 **判定** 仍用 `course.meta["current_lesson_index"]`  
3. 自动推进 **写入** 只改 `course.meta`  

→ 手动推进与对话自动推进可能 **互不可见**；这是当前 **最实质的行为不一致**，优先级高于 compat 读面美化。

### 2.5 次要债务（本 seam 分轮处理）

| ID | 现象 | 位置 | 轮次 |
|----|------|------|------|
| D1 | lesson PT INSERT 仍在，靠 `skip_progress_tracking_writes()` 短路 | `teaching_planner._record_lesson_progress()` L290–331 | **A2-4** |
| D2 | archive GET `/progress` 只读 PT，非 canonical | `progress_facade.list_compat_progress_rows()` L87–104 | **延后**（A2-5 可选） |
| D3 | 业务代码直接读 PT（lesson 相关） | `worlds.py` L265 等 | **A2-3** |
| D4 | 存档/恢复链路直接读 PT，必须显式判定是否承载 lesson 进度语义 | `save.py` L184+ | **A2-3b**（A2-3 PR 内先完成判定并记录结论；若涉及 lesson 展示/恢复则并入 A2-3，不得延后） |

---

## 3. 优先级判断（人已裁决 · 固定）

| 顺序 | 项 | 结论 |
|------|-----|------|
| **P0** | CourseProgress ↔ course.meta 双源 | **必须单独做主任务**（A2-1 + A2-2） |
| P1 | worlds 等旧 PT 读取迁移 | **紧跟 P0**（A2-3），否则新单源会被旧读法稀释 |
| P2 | archive GET `/progress` canonical 化 | **延后**；compat 设计问题，非最危险运行时 bug |
| P3 | 删除 `_record_lesson_progress` PT INSERT | **最后**（A2-4）；过早删除会损害回退与 compat |

**禁止**：在 A2-1 未验收前，顺手改 archive compat 语义、删表、或并入 Seam C/D。

---

## 4. 目标架构（Proposed）

### 4.1 唯一 lesson pointer 语义

**Canonical 存储**：`CourseProgress(current_lesson_index, completed_lesson_ids)`  
**兼容只读**：`course.meta["current_lesson_index"]` / `["completed_lessons"]` — 仅在 **无 CourseProgress 行** 时读写；有行后 meta 不再作为写入目标。

```text
                    ┌─────────────────────────────────────┐
                    │         teaching_planner              │
                    │  _get_current_index / _get_completed │  ← 唯一读入口
                    │  _set_lesson_progress (新增)         │  ← 唯一写入口
                    │  advance_lesson / set_lesson         │
                    └──────────────┬──────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
     textbook advance API    mastery_tracker      progress_facade
     set_lesson API          auto-advance         get_lesson_progress()
              │                    │
              └──────── 均委托 teaching_planner ──┘

CourseProgress 表 ── canonical
course.meta      ── legacy fallback（只读/回填，不再作为主写）
ProgressTracking lesson 行 ── A2-4 前仍受 flag 保护；A2-4 后结构删除 INSERT
```

### 4.2 新增/调整的 API（Python 层 · 非 HTTP）

在 `TeachingPlanner` 内抽取（名称可微调，职责不可拆）：

```python
def _get_current_index(self, db, course, user_id) -> int: ...      # 已有
def _get_completed(self, db, course, user_id) -> list[int]: ...     # 已有

def _set_lesson_progress(
    self,
    db: Session,
    course: Course,
    user_id: int,
    *,
    current_index: int,
    completed_ids: list[int] | None = None,  # None = 不覆盖 completed
) -> None:
    """唯一 lesson pointer 写入口。
    - 有 CourseProgress 行 → 写表
    - 无行 → 写 course.meta（legacy fallback only）
    - A2 阶段不引入新的可选分支；CourseProgress 创建策略见 §5.2 固定规则
    """

def advance_lesson(self, db, course, user_id: int | None = None) -> dict:
    """已有逻辑迁入 _set_lesson_progress；签名补 user_id 若需要。"""

def try_auto_advance_if_mastered(
    self,
    db: Session,
    course: Course,
    user_id: int,
) -> tuple[bool, int | None]:
    """唯一 auto-advance 事务入口。
    TeachingPlanner 拥有完整边界：
    - 读取当前 lesson index / completed
    - 读取当前 lesson 的 concepts（经 _get_lessons()）
    - 判定是否已 mastered
    - 决定是否推进并落库

    mastery_tracker 只负责提供“有哪些 concept 刚被更新”，
    不再保留 lesson pointer 判定/推进的一半职责。
    """
```

`mastery_tracker.update_from_memories()` **不得**再直接读/写 `course.meta` 的 lesson pointer 字段。

---

## 5. 分轮实施

每轮 = **一个 PR** = 单一主题。必须回答门禁四问并附 HARD + BEHAVIOR + ROLLBACK。

### A2-1 · 唯一写入口（P0 · 必须先做）

**目标**：自动推进与手动推进写入同一数据源。

**改什么**

- `teaching_planner` 新增 `_set_lesson_progress()`  
- `advance_lesson()` / `set_lesson()` 改为调用 `_set_lesson_progress()`  
- `mastery_tracker._try_auto_advance()` **删除**或改为薄包装，调用 `teaching_planner.try_auto_advance_if_mastered()`  
- `mastery_tracker.update_from_memories()` 用 `teaching_planner._get_current_index()` + `_get_lessons()` 取当前课节与 concepts，**禁止**裸读 `course.meta["current_lesson_index"]`

**不改什么**

- HTTP path / 响应 schema  
- archive `/progress*` compat 语义  
- `ConceptMastery` / `FSRSState` 写入逻辑  
- 删 `_record_lesson_progress` PT 分支  

**BEHAVIOR 验收（必新增）**

1. **双源回归**：seed 课程 **有 CourseProgress 行** + `course.meta` 故意设为不同 index → 对话触发 auto-advance 后 → `GET /api/courses/{id}/progress` 的 `current_index` **随 CourseProgress 变化**，且 meta 旧值 **不被读者采用**。  
2. **手动 vs 自动一致**：同一课程先 `POST .../advance` 再模拟 memory 触发 auto-advance → 两次结果在 `get_progress()` 中单调一致。  
3. **legacy 无 CP 行**：无 CourseProgress 时行为与现网兼容（仍可通过 meta 读写）。  
4. 现有 `test_progress_facade.py`、`test_mastery_tracker.py` 全绿。

**HARD 证据**

- `grep` 确认 `mastery_tracker.py` 无 `course.meta["current_lesson_index"]` 赋值（允许读 `generated_lessons` 若仍存 meta，见 §5.2）。  

**回退**：revert A2-1 PR；`USE_PROGRESS_FACADE` 不受影响。

---

### A2-2 · 唯一读/判定入口（P0 · 可与 A2-1 同 PR，若改动面可控）

若 A2-1 已包含全部读统一，A2-2 可合并为同一 PR。若拆分：

**目标**：所有「当前在第几课」「完成了哪些课」的判定，均经 `teaching_planner` 读方法。

**改什么**

- `mastery_tracker` 内所有 lesson index / completed 判定走 planner  
- `prompt_builder/modules/course_content.py` 若 duplicated 读 meta，改为委托 planner（**仅 lesson pointer 字段**）

**BEHAVIOR 验收**

- 与 A2-1 测试合并；额外：`test_course_content_integration` 中有 CourseProgress 时用例通过。

---

### A2-3 · 停止 lesson 相关旧 PT 读取（P1）

**目标**：新代码路径不再依赖 `ProgressTracking` 表达 lesson 进度。

**改什么（按优先级）**

| 文件 | 现状 | 改为 |
|------|------|------|
| `api/routes/worlds.py` L265 | PT `mastery_level/100` 当课程 progress | `progress_facade.get_lesson_progress()` 的 `progress_pct` 或 `CourseProgress` |
| `services/prompt_builder/...` | 若读 PT | canonical 读 |
| `api/routes/save.py` L184+ | 直接读 PT；需先判定是否影响 lesson 展示/恢复 | 若承载 lesson 进度语义，则本轮改为 canonical 读；若不承载，A2-3 PR 中写明证据与结论后方可留到 A2-3b |

**不改什么**

- `save.py` 若整体仍序列化 PT（mixed topic），可暂不做 **全量** 存档迁移；但 A2-3 必须明确其是否影响 lesson 展示/恢复，禁止“不判断直接延后”  
- 不删 `ProgressTracking` 表  

**BEHAVIOR 验收**

- 世界列表 API 返回的 `courses[].progress` 与 `GET /courses/{id}/progress` 的 `progress_pct` **一致**（容差 ±0.01）  
- 无 CourseProgress、仅有 legacy meta 时仍有合理 fallback  

**HARD 证据**

- `rg "ProgressTracking" backend/api/routes/worlds.py` → 0 匹配（或仅剩注释）

---

### A2-4 · 结构删除 lesson PT INSERT（P3 · 最后）

**前置**：A2-1～A2-3 稳定 ≥1 轮 CI；前端 Archive 页仍可用或已弃用（人裁决）。

**改什么**

- 删除 `teaching_planner._record_lesson_progress()` 内 `ProgressTracking` INSERT/UPDATE 分支  
- 删除或内联 `skip_progress_tracking_writes()` 对该路径的 guard（因路径已不存在）  
- 更新 `test_progress_facade.test_rollback_flag_restores_progress_tracking_insert`：rollback 仅覆盖 **archive compat POST**，不再覆盖 lesson INSERT  

**不改什么**

- archive compat 对 **concept**  topic 的 PT 读/有条件写（直至 Archive 页退役）  
- `USE_PROGRESS_FACADE=false` 对 archive POST 的回退能力  

**BEHAVIOR 验收**

- `advance_lesson` / auto-advance 后 PT 行数仍不变  
- `grep ProgressTracking(` in `teaching_planner.py` → 0  

**回退**：revert A2-4；或短期恢复 `_record_lesson_progress` 函数（不含 INSERT 的空 stub 不可接受，须完整回退）。

---

### A2-5 · archive GET compat 增强（P2 · 可选 · 独立 PR）

**默认不做**，除非 Owner 明确要求 Archive 页与 canonical 对齐。

**选项 A**：`list_compat_progress_rows()` 合并 `ConceptMastery` 合成视图  
**选项 B**：文档 + 响应头明确「非 canonical」；前端引导至 `/courses/{id}/progress`  

不在 A2-1～A2-4 中夹带。

---

## 5.2 关于 `course.meta["generated_lessons"]`

Lesson **内容**（标题、concepts 列表）与 lesson **指针**（index）分离：

| 字段 | A2 阶段策略 |
|------|-------------|
| `current_lesson_index` / `completed_lessons` | 写入收敛到 `_set_lesson_progress`；有 CP 行后停止写 meta |
| `generated_lessons` | **本轮可保留在 meta**；长期应已在 `LessonPlan` 表（`teaching_planner._get_lessons` 已双源）。auto-advance 判 concepts 时必须用 `_get_lessons()`，**禁止**只读 meta |

固定规则（A2 rev.2 起）：
- `CourseProgress` 的创建策略不再开放为“可选 lazy-create”。
- 已有课程生成链路继续在教材生成/课程初始化阶段创建 `CourseProgress`。
- A2-1/A2-2 仅允许保留“无 CourseProgress 时回退写 meta”的兼容行为，不新增新的 lazy-create 分支。
- 若后续要消除 fallback 窗口，需单独立项并附迁移/回填方案，而不是在 A2 实施中临场决定。

---

## 6. 与 Seam 路线图关系

```text
Seam A   ProgressFacade（concept/review 止写 PT）     ✅ 已合并
Seam B   archive.py 拆分                              🔄 PR #256
Seam A2  lesson pointer 单源化（本文档）               ⬅ 下一步
Seam C   learner-trait / user-profile / report        ⏸ A2-1 验收后再开
Seam D   live-dialogue 前端 store                     ⏸ 同上
```

**门禁**：进入 Seam C 前，A2-1 的 BEHAVIOR 验收必须通过（或 Owner 显式豁免并记录风险）。

---

## 7. 建议 Issue / 分支命名

```text
Issue 标题: refactor(v1.0.5): Seam A2 — lesson pointer 单源化
分支:
  feat/lesson-progress-a2-1   # 写+读统一
  feat/lesson-progress-a2-3   # worlds 旧读清理
  feat/lesson-progress-a2-4   # 删 PT INSERT
```

每个 PR 描述使用 [pr0_collaboration_gate.md §8](./pr0_collaboration_gate.md) 模板。

---

## 8. PR 检查清单（复制用）

```md
## Seam
A2-x: lesson pointer …

## 不改什么
- [ ] HTTP path / schema
- [ ] archive compat（若本轮未声明）
- [ ] ConceptMastery / FSRSState 主链路

## 本次改动
…

## HARD 证据
- [ ] rg / 结构断言
- [ ] collect_boundary_stats（若动 routes）

## BEHAVIOR 证据
- [ ] pytest …（列出具体用例名）
- [ ] 双源回归用例（A2-1 必含）

## 回退方案
revert PR #…

## 是否影响下一个 seam
A2-x 完成后才开 Seam C / A2-x+1
```

---

## 9. 测试文件规划

| 轮次 | 建议新增/扩展 |
|------|----------------|
| A2-1 | `backend/tests/test_lesson_pointer_single_source.py`（双源回归核心） |
| A2-1 | 扩展 `test_mastery_tracker.py`：CourseProgress 存在时的 auto-advance 集成 |
| A2-1 | 扩展 `test_learning_sessions.py` 或 `learning.py` 相关用例：学习会话入口读取的 lesson index 与课程页 canonical 进度一致 |
| A2-3 | `test_archive.py` 或 `test_worlds.py`：world 列表 progress 与 canonical 一致 |
| A2-4 | 更新 `test_progress_facade.py` rollback 用例范围 |

**禁止**：仅改结构、无行为断言即标「完成」。

---

## 10. 一句话执行约束

**先让 `teaching_planner` 成为 lesson pointer 的唯一读写真相，再清旧 PT 依赖，最后才删 INSERT 分支；compat 读面美化不挡 P0。**

---

## 附录 A — 相关源码索引

| 用途 | 路径 |
|------|------|
| lesson 读/写（改） | `backend/services/teaching_planner.py` |
| auto-advance（改） | `backend/services/mastery_tracker.py` |
| canonical 读 facade | `backend/services/progress_facade.py` |
| worlds 旧读（A2-3） | `backend/api/routes/worlds.py` |
| 存档 PT（A2-3b） | `backend/api/routes/save.py` |
| Seam A 测试 | `backend/tests/test_progress_facade.py` |
| 掌握度测试 | `backend/tests/test_mastery_tracker.py` |

## 附录 B — Seam A 未完成项对照

| Seam A 合同（§4.2） | A2 承接 |
|---------------------|---------|
| `get_lesson_progress` → planner | 已满足；A2 强化 planner 内部一致性 |
| 禁止新 PT INSERT（运行时） | A2-4 升级为结构不可能 |
| archive GET 与 canonical 课节指针一致 | **未满足**（D2）；降至 A2-5 可选 |
| `CourseProgress` 为 lesson 权威 | **未满足**（§2.4）；A2-1 核心 |
