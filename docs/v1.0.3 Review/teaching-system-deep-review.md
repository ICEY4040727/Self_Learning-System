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

### TODO-T5 ⏳ — `set_lesson` 后退也加 mastery 🟡 **P2**

- **位置**：`teaching_planner.py:154-181` + `_record_lesson_progress`
- **问题**：手动设 lesson_index=2 时也调 `_record_lesson_progress`，把第 3 课的 mastery 加 20。如果用户从第 5 课跳回第 1 课"复习一下"，**第 1 课的 mastery 又涨 20**。复习 ≠ 学完。
- **修法**：`_record_lesson_progress` 只在 `advance_lesson` 路径调用，`set_lesson` 不写 mastery；或者只对**首次到达**的 lesson 写。
- **状态**：pending

### TODO-T6 ⏳ — `advance_lesson` 在末课静默 no-op 🟡 **P2**

- **位置**：`teaching_planner.py:133-136`
- **问题**：
  ```python
  next_idx = current_idx + 1
  if next_idx >= len(lessons):
      next_idx = len(lessons) - 1  # 保持在最后一课
  ```
  推到最后一课后再调 `advance_lesson`，next_idx 不变。前端调用方收不到"课程已完成"信号。
- **修法**：在最后一课时返回 `{"completed": True, ...}` 字段；前端可以据此显示祝贺/结业页面。
- **状态**：pending

### TODO-T7 ⏳ — 自定 FSRS 实现 vs `fsrs>=6.3.0` 依赖 🟡 **P2**

- **位置**：`mastery_tracker.py:223-249` + `requirements.txt:12 fsrs>=6.3.0`
- **问题**：`_schedule_review` 自己实现 stability 几何增长 `stability * 1.5`，cap 365。同时 `requirements.txt` 列了 fsrs 库（标准 SuperMemo/Anki 算法）。
  - 自定算法没有 difficulty 自适应，不同概念衰减一样
  - cap 365 后再 mastered 不影响下次复习时间，**13 次完美复习后永远固化在 365 天间隔**
- **修法**：`from fsrs import Scheduler` 直接用库；或者 explicit 注释"故意不用，因为 X"。
- **状态**：pending

### TODO-T8 ⏳ — 通道 2 信号不进入掌握度 🟢 **P3**

- **位置**：`learning_engine.py:262` 传给 mastery_tracker 的 `recent_facts = result.memories`，仅来自通道 1（LLM `<memory>` 标签）。
- **问题**：通道 2（"我不懂" → struggle）现已有 sentinel tag `__channel2_confusion__`，但 `mastery_tracker` 看不到。
  - **争议点**：可能是设计选择（LLM 信号更可信）。如果是有意，得在 docstring 写明。
- **状态**：pending（先等用户决定）

### TODO-T9 ⏳ — `MASTERY_DELTA_MAP` 等魔术数字硬编码 🟢 **P3**

- **位置**：`mastery_tracker.py:30-44`
- **问题**：`{"concept_mastered": 25, "concept_struggle": -15}`、`AUTO_ADVANCE_THRESHOLD = 70`、`MIN/MAX_MASTERY = 0/100`、`weak < 40`、`mastered_count >= 70`。
- **修法**：移到 `core/config.py` 的 `learning_system` dict，与 salience 那批一致。
- **状态**：pending

### TODO-T10 ⏳ — `CourseContentModule.is_applicable` 太宽 🟢 **P3**

- **位置**：`course_content.py:30-36`
- **问题**：只要 `course_id` 存在就 applicable，但 `assemble` 在课程没 meta 时返回 `""`。模块每次 prompt 构建都被无谓调用。
- **修法**：`is_applicable` 改为 `course_id is not None and Course.meta exists`。需要 db query — 取舍：是否值得为省一次 prompt 段落付一次 query。
- **状态**：pending

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

## 7. 完成态

（执行过程中填充）
