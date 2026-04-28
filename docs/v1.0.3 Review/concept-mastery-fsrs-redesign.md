# 概念掌握度 + FSRSState 跨世界重设计

> Branch: `feat/v1.0.3`
> Triggered by: review feedback — 学习画像跨世界共享，但 ProgressTracking
> 把概念掌握度按 course 隔离、FSRSState 按 world 隔离，跟跨世界语义冲突。
> Last updated: 2026-04-27

本文档同前几片 review，是工作记录。**Claude 上下文窗口有限，本文档是唯一可信的进度来源**。

---

## 设计决定（来自用户拍板）

| 数据 | 当前作用域 | 目标作用域 |
|---|---|---|
| 概念掌握度 | per-(user, course) | **per-(user, concept) 完全跨世界**（不论 world / course，同名 concept 共享一行） |
| FSRSState | per-(world, concept)，user 隐式 | **per-(user, concept) 完全跨世界** |

**统一术语**：本文档下文出现"跨课程"也都是"跨世界"的简写——schema 上没有 course_id 也没有 world_id 参与 unique，这是最广作用域。

**FSRSState world_id 列**：保留为 nullable（diagnostic / 首次记录所在的世界），不参与 unique key。

**FSRSState 重复合并算法（决策 C 数学合并）**：
- `stability = max(stability_a, stability_b)`
- `difficulty = min(difficulty_a, difficulty_b)`
- `reps = reps_a + reps_b`
- `last_review = max(last_review_a, last_review_b)`
- `next_review = max(next_review_a, next_review_b)`
- `card_data`：取 stability 较高那一行的 card_data，但用上面 merge 后的值覆盖关键字段（state/step/card_id 保留更熟那行）

---

## A. ProgressTracking → 拆出 concept_mastery 表

### TR-A1 ✅ — 新建 `concept_mastery` 表
- `models.py` 新增 `ConceptMastery` 模型；UNIQUE(user_id, concept_id)；无 course_id / world_id
- 迁移 `2026_04_27_concept_mastery_split.py`（down_revision = 2026_04_27_fsrs_card_data）

### TR-A2 ✅ — Backfill：把 ProgressTracking 的 concept 行迁过去
- 同一迁移：`INSERT INTO concept_mastery (user_id, concept_id, ...) SELECT user_id, topic, MAX(...) ... GROUP BY user_id, topic`
- 接 `DELETE FROM progress_trackings WHERE topic_type='concept'`
- downgrade 反向回填（fallback：选用户第一个 course 作 course_id；lossy by design）

### TR-A3 ✅ — 改 mastery_tracker writes
- `_update_concept_mastery(db, *, concept, delta, user_id)` — 去掉 course_id/world_id
- 写入 ConceptMastery
- 调用方 `update_from_memories` 同步收紧

### TR-A4 ✅ — 改 reader + 测试
- `_check_lesson_mastered(db, user_id, concepts)` — 用 IN 一次查回，O(1) DB round-trip
- `get_course_mastery(db, course_id, user_id)` — 从 course.meta lesson concepts 拼出 list 去 ConceptMastery 查
- `textbook.py` 的 mastery endpoint 同步传 `current_user.id`
- **新增 cross-world 测试** `test_concept_mastery_is_cross_world`：math-world 学过的"递归"在 cs-world 的 get_course_mastery 也看得到（核心不变量）
- 旧 `get_course_mastery` mock 测试 → 转成 real-DB（mock 控制流太复杂）

---

## B. FSRSState → per-(user, concept)

### TR-B1 ⏳ — 加 user_id 列 + backfill
- 迁移 `2026_04_27_fsrs_per_user.py`
- `ALTER TABLE fsrs_states ADD COLUMN user_id INT`
- backfill：`UPDATE fsrs_states SET user_id = (SELECT user_id FROM worlds WHERE id = fsrs_states.world_id)`

### TR-B2 ⏳ — 合并重复行（决策 C 数学合并）
- 同迁移内：Python loop 找出重复 `(user_id, concept_id)` 组，应用合并算法，删多余行
- world_id 在合并时取 stability 较高那行的（diagnostic）

### TR-B3 ⏳ — 切换 UNIQUE 约束
- 删 `UNIQUE(world_id, concept_id)`
- 加 `UNIQUE(user_id, concept_id)`
- world_id 改 nullable

### TR-B4 ⏳ — 改 reader / writer
- `mastery_tracker._schedule_review`：filter 改 `(user_id, concept_id)`，签名加 `user_id` 参数
- `archive.py:1465 review_progress`：filter 改 `(current_user.id, concept_id)`
- learning_engine 调 mastery_tracker.update_from_memories 时本来已有 user_id

### TR-B5 ⏳ — 测试
- cross-world concept review state 共享：math-world 复习"递归" → cs-world 看到同一 stability
- 真 DB 测试 verify 决策 C 合并逻辑（构造两条冲突行，运行迁移函数，断言结果）

---

## 已知 Acceptable / 不修

| ID | 问题 | 为什么不修 |
|---|---|---|
| 旧 ProgressTracking lesson 行 | 仍然 per-course；teaching_planner 写 lesson 行不变 | lesson 进度本就是课程内概念，不跨 |
| `archive.py POST /progress` 手动创建 | 用户主动创建的进度 row 不动 | 用户意图不可推断 |
| `archive.py GET /progress?course_id=X` | 现在不返回 concept 行（拆走了） | API 兼容性问题 — 前端要新 endpoint `GET /concepts/mastery` 但本片只做后端 |

---

## C. 顺手修：profile_aggregator 还原跨世界（非 schema，纯逻辑）

### TR-C1 ✅ — 移除 profile_aggregator world_id filter
学习画像跨世界共享。早前 review followup 给 5 个聚合方法（_ratio / _count /
_conversion_rate / _keyword_extract / _compute_learning_stats）误加了 world_id
filter，按 R1-01 的"跨世界泄漏"逻辑套过去 — 但 R1-01 是为 `recall` 路径
（LLM-facing memory 注入）做的，不该套到画像聚合上。

修：5 个方法移除 world_id filter；`_keyword_extract` 调 `memory_manager.observe_recent`
传 `world_id=None`。signature 保留 wid 参数仅做调用方对齐。

---

## 离开本片的判定

- A1-A4, B1-B4 全 ✅
- 全套测试 pass
- 迁移在空 DB 跑通：`alembic upgrade head` 成功
- 真 DB 回归测试覆盖关键不变量（concept 跨课程 / FSRS 跨世界）
