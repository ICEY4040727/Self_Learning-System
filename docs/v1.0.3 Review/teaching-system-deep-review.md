# 教学/掌握度引擎深度 Review — 工作清单

> Branch: `feat/v1.0.3`
> Scope: Phase 3 commit `cefd4da` 的教学子系统（mastery + planner + generator）
> Files in scope:
> - `backend/services/mastery_tracker.py` (302 new lines)
> - `backend/services/teaching_planner.py` (213 new lines)
> - `backend/services/course_generator.py` (231 new lines)
> - `backend/services/prompt_builder/modules/course_content.py` (154 new)
> - `backend/services/prompt_builder/modules/strategy.py` (85 new)
> - `backend/tests/test_mastery_tracker.py` (304)
> - `backend/tests/test_teaching_system.py` (243, RecallService 部分已审)
> - `backend/tests/test_textbook_course_gen.py` (275)
> - 集成点：`learning_engine.py:260` + `api/routes/textbook.py`
> Last updated: 2026-04-26

本文档同 `memory-system-deep-review.md` 是 review session 的工作记录。**Claude 上下文窗口有限，本文档是唯一可信的进度来源**。每完成一项就更新状态；发现新问题就 append 到 §3。

---

## 1. 已修复（已 commit）

（暂无 — 本片刚开始 review）

---

## 2. 待修复 — 初轮扫描发现

按严重性排序。每项执行完更新状态。

### TODO-T1 ✅ — `_update_concept_mastery` 不写 user_id，prod 必炸 🔴 **P0**

- **位置**：`mastery_tracker.py:138`
- **修复**：
  - `update_from_memories` + `_update_concept_mastery` 都加 `user_id` 必传参数
  - `learning_engine.py:266` 调用方补传 `session.user_id`
  - 查询 ProgressTracking 时也按 `user_id` 过滤（多用户共享课程时正确隔离）
- **测试**：新增 `TestMasteryTrackerRealDB` 类（2 个真 DB 测试）+ 8 处 mock 测试补 `user_id=1`。Class docstring 提示后续 INSERT 路径必须真 DB 测试，避免再踩 mock 盲区。
- **状态**：✅ done（待 commit）

### TODO-T2 ✅ — `concept_struggle` 不调度 FSRS 复习 🔴 **P1**

- **位置**：`mastery_tracker.py:111`
- **修复**：
  - struggle 也调用 `_schedule_review`，传 `signal="concept_struggle"`
  - `_schedule_review` 加 `signal` 参数：mastered = stability *= 1.5（标准 SRS 增长）；struggle = reps 重置为 0、stability /= 2 (≥1.0)、明天再练
  - 首次 struggle 起始 stability = 0.5，首次 mastered = 1.0
- **测试**：2 个新 real-DB 测试 — struggle 触发 FSRS 且 reps=0/stability<1；struggle→mastered 序列正确恢复
- **状态**：✅ done（待 commit）

### TODO-T3 ✅ — `ProgressTracking.topic` 列承担两个语义空间 🟡 **P1**

- **位置**：`mastery_tracker.py` + `teaching_planner.py` + `models/models.py`
- **修复**：
  - 新迁移 `2026_04_26_add_progress_tracking_topic_type.py` — 加 `topic_type` 列（默认 'concept'，与历史 mastery_tracker 行兼容） + 复合索引
  - Model 加 `topic_type = Column(String(20), nullable=False, default="concept")`
  - `mastery_tracker._update_concept_mastery` 写入 + 查询时 filter `topic_type='concept'`
  - `mastery_tracker._check_lesson_mastered` filter concept
  - `mastery_tracker.get_course_mastery` filter concept
  - `teaching_planner._record_lesson_progress` 写入 + 查询时 filter `topic_type='lesson'`
- **测试**：新增 `test_topic_type_isolates_concept_from_lesson` — 课程标题"递归"+ 概念"递归"共存，2 行 + 类型分离 + 概览只统计 concept
- **状态**：✅ done（待 commit）

### TODO-T4 ✅ — `course_generator` 静默回退到"入门"假课 🟡 **P1**

- **位置**：`course_generator.py:222`
- **修复**：empty lessons → `raise ValueError("LLM 未生成有效章节 — 请检查教材内容或重试课程生成")`，吞错变报错
- **测试**：替换 `test_validate_result_minimal` 为 `test_validate_result_empty_raises`，断言 ValueError 抛出
- **状态**：✅ done（待 commit）

### TODO-T5 ✅ — `set_lesson` 后退也加 mastery 🟡 **P2**

- **位置**：`teaching_planner._record_lesson_progress`
- **修复**：方法只 INSERT "started" 行（mastery=20），existing 路径仅刷新 `last_review`，**不再 += 20**。lesson 实际掌握度由 mastery_tracker 通过 concept 信号推动；本函数只负责"开始"标记。
- **测试**：新增 `test_record_progress_does_not_bump_existing_mastery`
- **状态**：✅ done（待 commit）

### TODO-T6 ✅ — `advance_lesson` 在末课静默 no-op 🟡 **P2**

- **位置**：`teaching_planner.advance_lesson` + `get_progress`
- **修复**：`get_progress` 增加 `course_completed: bool` 字段（`done >= total`）。`advance_lesson` 末课调用时 current_index clamp 到末课但 completed_lessons 添加完后 `course_completed=True` 自然为 True。前端可据此显示结业页。
- **测试**：`test_course_completed_signal` (推到末课后 = True) + `test_course_not_completed_mid_course` (中途 = False)
- **状态**：✅ done（待 commit）

### TODO-T7 ✅ — 自定 FSRS 实现 vs `fsrs>=6.3.0` 依赖 🟡 **P2**

- **发现**：项目里**已经有 `backend/services/spaced_repetition.py`** 是 fsrs 库的正确封装（被 archive.py 用着）。mastery_tracker 是在已有正确实现旁边重新发明了一个错的轮子。
- **修复**：`_schedule_review` 改为调用 `spaced_repetition.review` — Rating.Good (3) for mastered，Rating.Again (1) for struggle
- **顺手修了 schema 缺陷**：FSRSState 之前只存 difficulty/stability/last_review/next_review/reps 这几个字段，但 `Card.from_dict` 需要 card_id/state/step。所以无论 mastery_tracker 还是 archive.py，**之前每次 review 都因为字段不全而退化为"首次 review"**——FSRS 的进度从来没真正累积过。新增 `card_data JSON` 列存完整 Card.to_dict()。新迁移 `2026_04_27_add_fsrs_card_data.py`
- **测试**：3 个新测试 — struggle 触发 FSRS、struggle interval < mastered interval、连续 mastered → reps=3 + state 累积
- **状态**：✅ done（待 commit）

### TODO-T8 ✅ — 通道 2 信号不进入掌握度 🟢 **P3**

- **决定**：保留现状（通道 2 不进 mastery），明示为有意设计
- **修复**：`learning_engine.py:259` 加 `[TODO-T8]` 注释块说明：通道 2 是单关键词 heuristic，让其影响 ±15/+25 mastery 会让分数反映情绪而非理解；LLM 提取的通道 1 是唯一可信源
- **状态**：✅ done（待 commit）

### TODO-T9 ✅ — `MASTERY_DELTA_MAP` 等魔术数字硬编码 🟢 **P3**

- **修复**：`config.py learning_system["mastery"]` 新 dict — `delta_map`、`min`/`max`、`auto_advance_threshold`、`weak_threshold`、`lesson_started_initial`。`mastery_tracker` 的模块级常量改成从 config 读（保留 `MASTERY_DELTA_MAP` 等名称用于向后兼容旧 import）。`teaching_planner._record_lesson_progress` 也用 config 的 `lesson_started_initial`
- **状态**：✅ done（待 commit）

### TODO-T10 ✅ — `CourseContentModule.is_applicable` 太宽 🟢 **P3**

- **发现**：framework 实际只看 `should_include`，不看 `is_applicable`（is_applicable 只是模块自己加的辅助方法）
- **修复**：把检查搬到 `should_include` — db + course_id + Course exists + Course.meta 含 generated_overview 或 generated_lessons 才返回 True。assemble() 不变（保留作为 defensive fallback）
- **测试**：4 个新 should_include 测试覆盖 no-db / no-course / empty-meta / has-content 四种分支；删旧的 `test_should_include_always_true`
- **状态**：✅ done（待 commit）

---

## 3. 新发现（执行过程中追加）

### NEW-T1 ✅ — `_schedule_review` 同会话内重复触发会撞 UNIQUE 🔴 **P1**

- **触发**：TODO-T1 的 `test_update_existing_tracking_keyed_by_user` 真 DB 调两次同概念 → `sqlite3.IntegrityError: UNIQUE constraint failed: fsrs_states.world_id, fsrs_states.concept_id`
- **根因**：`autoflush=False` (conftest + 生产 SessionLocal) 让第二次 SELECT 看不到第一次 pending INSERT，重复 add → UNIQUE 撞车
- **修复**：`_schedule_review` 在 SELECT 前 `db.flush()`，强制让前面的 pending INSERT 落地
- **影响验证**：T1 的 `test_update_existing_tracking_keyed_by_user` 通过 = 同 session 多次调用同概念不再撞车
- **状态**：✅ done（随 T1 一起 commit）

---

## 4. 已知 Acceptable / 不修

| ID | 问题 | 为什么不修 |
|---|---|---|
| 21 | `course_generator` 用 `llm.manager.get_adapter`，其它服务用 `llm.adapter.get_llm_adapter` | 两套都存在且各自工作。统一是大动 LLM 层，超出本片 review 范围 |
| 30 | `StrategyModule` 三档（<0.4/<=0.7/>0.7）硬编码 | 与 strategy_rules 表的 low/mid/high 行映射，是隐式契约。改的话要同步动表结构 |
| LLM | `course_generator` `temperature=0.3, max_tokens=4096` 硬编码 | 课程生成场景固定，这两个值是经验值，移配置不增价值 |

---

## 5. 工作流约定

1. 开始一项 → TaskUpdate 标 in_progress
2. 改完代码 → 跑相关测试
3. 通过 → 更新本文档对应 TODO 的状态为 ✅ done + commit hash
4. 发现新问题 → append §3，新建对应 TaskCreate
5. **特别警告**：本片 mastery_tracker 测试**重度 mock**，写新测试要尽量用真 DB（`db_session` fixture），避免 T1 类陷阱重演

## 6. 离开教学系统的判定标准

- §2 P0 + P1 全部 ✅ 或显式 deferred 并说明
- §2 P2/P3 选做
- §3 全部消化
- 全套测试 pass（canonical cwd `cd backend && pytest`）
- 然后才进入 Phase 3 下一片（叙事/成就引擎）

---

## 7. 完成态（2026-04-27）

| Section | 状态 |
|---|---|
| §1 已修复 | 11 项（T1-T10 + NEW-T1） |
| §2 待修复 | 0（全部 ✅） |
| §3 新发现 | 1 项已修（NEW-T1 autoflush race） |
| §4 acceptable | 3 项 |

**测试**：`cd backend && pytest` → 280 passed, 13 skipped
**Alembic**：single head (`2026_04_27_fsrs_card_data`), single base

**Commits on `feat/v1.0.3`**：
- `28a9fe0` T1+T2+NEW-T1（user_id, struggle FSRS, autoflush race）
- `0e5476b` T3+T4（topic_type 列, no silent course fallback）
- 本轮（待 commit）T5-T10（lesson mastery, completed signal, fsrs lib + card_data, channel-2 doc, config, course_content gating）

**两个意外发现**：
- T7 实施时发现 `spaced_repetition.py` 早就存在 — `mastery_tracker._schedule_review` 在已有正确实现旁边写错了一个轮子
- T7 顺带发现 FSRSState 缺 card_id/state/step 字段，**之前 archive.py 也用错了相同的 cherry-pick 模式**，导致每次 review 都退化为首次 review — 本轮一并修了

**教学系统 review 关闭。** 下一片：叙事/成就引擎（`narrative_engine.py` 185 + `gamification.py` 211 + 路由 + 325 行测试）。

---

## 8. 后记 — 被 cross-world 重设计部分覆盖（2026-04-28）

`docs/v1.0.3 Review/concept-mastery-fsrs-redesign.md` 实施后：

- **T1** user_id NOT NULL 修复仍然正确，但作用面缩小：concept 行已搬到独立 `concept_mastery` 表，原修复现在主要保护 ProgressTracking 的 lesson 行
- **T3** topic_type 区分 concept/lesson 原本是缓解措施 — concept 拆表后两类数据物理隔离，topic_type 列对仅剩的 lesson 行不再起判别作用（保留无害，删除需另做迁移，留待未来 cleanup）
- **T7** FSRSState card_data 列继续有效；但 UNIQUE 约束已从 (world_id, concept_id) 切换到 (user_id, concept_id)（重设计 B 部分）

`mastery_tracker._schedule_review` 签名加了 user_id 参数；`get_course_mastery` 改为接收 user_id；旧 mock 测试转换成 real-DB 跨世界回归测试。代码层面相关改动详见 redesign doc。
