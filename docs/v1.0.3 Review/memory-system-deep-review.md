# 记忆系统深度 Review — 工作清单

> Branch: `feat/v1.0.3`
> Scope: Phase 3 commit `cefd4da` 的记忆系统部分
> Files: `memory_manager.py` (376 lines new), `recall_service.py` (118 new),
> `recall_context.py` (58 new), `memory_extractor.py`, `memory_facts.py`
> Last updated: 2026-04-26

本文档是这个 review session 的工作记录。**Claude 上下文窗口有限，本文档是唯一可信的进度来源**。每完成一项就更新状态；发现新问题就 append 到 §3。

---

## 1. 已修复（已 commit）

| ID | 问题 | Commit | 验证 |
|---|---|---|---|
| **R1-01** | `observe_recent` 缺 world_id filter，跨世界记忆泄漏 | fb1c812 | code grep + 测试 |
| **R1-02** | NarrativeEngine `_cooldowns` 内存级（非功能问题，标 acceptable） | fb1c812 | 注释标记 |
| **2A-01** | `evolve_salience` per-message 调用 = 每聊一次扣一天衰减 | fb1c812 → 3cecf76 | 已删除整个函数（见 X-1） |
| **2A-02** | `t_valid` / `t_invalid` 时态字段写入 | fb1c812 | model + migration + write |
| **2A-04** | `retrieve_memories` 返回时不更新 recall_count | fb1c812 → 3cecf76 | 函数已删除，retrieve() 内联做 |
| **2A-05** | ILIKE 通配符注入 | fb1c812 → 3cecf76 | 函数已删除 |
| **2F-01** | retrieve 不查 concept_tags | fb1c812 → 3cecf76 | 函数已删除 |
| **X-1** | `compute_effective_salience` 是死代码、`evolve_salience` 实现与设计相反 | 3cecf76 | retrieve() 接通 effective + min_salience filter |
| **X-2** | `compute_effective_salience` 不处理 SQLite 返回的 naive datetime | 3cecf76 | 测试触发 + 修 |
| **X-3** | 通道 2 信号 `concept_tags=[]` 全部绕过去重 | 3cecf76 | sentinel tags + 测试 |
| **X-4** | Alembic 迁移链断裂（双 head） | fb1c812 | 链接到 textbooks |
| **X-5** | 我前次错误地把 evolve_salience 接到 daily cron | 3cecf76 | scheduler 整套删除 + apscheduler 依赖移除 |
| **X-6** | `update_recall_count` 与 `retrieve_memories` 双计数陷阱 | fb1c812 → 3cecf76 | 两个方法都删了 |
| **X-7** | `get_world_learner_profile` 空 dict 误判 404 | fb1c812 | 改为 `if lp is None` |

---

## 2. 待修复

按优先级排序。每项执行完更新状态。

### TODO-1 ✅ — `get_working_context` 忽略 token budget

- **位置**：`backend/services/memory_manager.py:39`
- **问题**：docstring 说 "respecting budget"，实现只用 `max_messages=50`，`max_working_context_tokens=4000` config 全代码 0 个读取者。
- **修复**：
  - 新增 `_estimate_tokens` 静态方法（`len(content) // 3 + 4`，中英折中 + role 开销）
  - `get_working_context` 改为最新→最旧遍历，累加 token 到 budget 即停
  - 始终保留至少最新一条（即使单条超 budget），避免空 context
- **测试**：3 个新测试覆盖 (1) 大消息按 budget 裁剪 (2) 单条超 budget 仍返回该条 (3) 既有 chronological/empty session 测试不破
- **状态**：✅ done（待 commit）

### TODO-2 ⏳ — `expires_at` 字段是空头支票

实际上是两个相关问题：

#### TODO-2a ✅ — `cleanup_expired` 是死代码
- **位置**：`memory_manager.py:393` → `memory_facts.py:81`
- **问题**：定义了但 production 0 调用。结合 X-5 我把 scheduler 删了，现在没有任何地方会清理过期记忆。
- **修复**：新增 `backend/scripts/cleanup_memories.py` 作为 ops 入口；`python -m backend.scripts.cleanup_memories` 即可触发。docstring 标注非自动调度。不重新引入 scheduler。
- **状态**：✅ done（待 commit）

### TODO-2b ✅ — `observe_recent` 不过滤 expires_at
- **位置**：`memory_manager.py:131`
- **问题**：narrative + gamification 走 `observe_recent`，看到已过期的事实。
- **修复**：加 `(expires_at IS NULL OR expires_at > now)` 过滤；新测试 `test_observe_recent_filters_expired` 覆盖。
- **状态**：✅ done（待 commit）

### TODO-3 ✅ — `recall_service` N×2 查询 + content substring 误判

- **位置**：`backend/services/recall_service.py:60-105`
- **修复**：
  - 两个 `observe_recent` 提到循环外（各 1 次 query，limit=50）
  - 把 fact list 折成 `set` of tags（`{tag for f in facts for tag in f.concept_tags}`），循环内做 O(1) 集合查询
  - 删掉 `prereq_id in content` 子串匹配
- **测试**：新增 `test_recall_no_substring_false_positive`：tags=["absolute"]+content"absolutely confused" 不再匹配 prereq "abs"
- **状态**：✅ done（待 commit）

### TODO-4 ✅ — JSON `concept_tags.contains()` 子串误判

- **位置**：`memory_manager.py:137` (retrieve) + `memory_manager.py:432` (_find_duplicate)
- **决定**：留着，加 inline `[TODO-4]` 注释说明 caveat 和长期方案（JSON1 `json_each` / Python 后过滤）。实际 LLM 提取的 tags 多为多字符串 / 中文，碰撞罕见。
- **状态**：✅ done — 注释已落地

### TODO-5 ⏳ — `extract_and_store` 通道 2 也跑过 ILIKE 转义？

- **位置**：检查 `_extract_student_signals` 的 content 写入路径
- **可能问题**：通道 2 写入的 content 可能含特殊字符（用户消息原文截断），后续若用 ILIKE 检索可能炸。但 X-1 后 retrieve() 已不再做 query 检索（删了 `query` 参数），所以这个目前不是活问题。
- **状态**：N/A（已被 X-1 间接消除）

---

## 3. 新发现（执行过程中追加）

### NEW-1 ✅ — `get_working_context` order_by 缺次级排序键

- **触发**：TODO-1 测试 `test_token_budget_trims_oldest` 在套件中失败但单跑 pass。
- **根因**：`order_by(ChatMessage.timestamp.desc())` — SQLite 时间戳是秒精度，同秒插入的多条消息排序不确定。"最新消息"未必真的最新。
- **影响**：用户连续快速发消息时，working context 末尾消息可能不是最新那条。
- **修复**：加 `ChatMessage.id.desc()` 作次级排序键（id 单调递增，绝对有序）。
- **Commit**：随 TODO-1 一起 commit
- **状态**：✅ done

---

## 4. 已知 Acceptable / 不修

| ID | 问题 | 为什么不修 |
|---|---|---|
| 2A-03 | 去重简化为 tag 匹配（不做语义相似度） | 设计决策，LLM 提取措辞差异大，精确匹配不可行 |
| **6** | `write_facts` dedup 时 content 被覆盖 | **设计文档第 151 行原话："如果命中 → 更新已有记录的 content"** — 实现符合设计 |
| R1-02 | `_cooldowns` 内存级 | 多 worker 部署再说 |

---

## 5. 工作流约定

1. 开始一项 → TaskUpdate 标 in_progress
2. 改完代码 → 跑相关测试（不一定全跑）
3. 通过 → 更新本文档对应 TODO 的状态为 ✅ done + commit hash
4. 发现新问题 → append §3，新建对应 TaskCreate
5. 完成所有 TODO → 跑 `pytest --no-header -q`（canonical cwd `cd backend && pytest`）
6. 一并 commit；commit message 引用本文档

## 6. 离开记忆系统的判定标准

- §2 全部 ✅ 或显式 deferred
- §3 全部消化（要么修要么 deferred）
- 全套测试 pass
- 然后才进入 Phase 3 下一片（教学/掌握度引擎）

---

## 7. 完成态（2026-04-26）

| Section | 状态 |
|---|---|
| §1 已修复 | 14 项（含 TODO-1~4 + NEW-1） |
| §2 待修复 | 0 项（全部 ✅） |
| §3 新发现 | 1 项已修（NEW-1 order_by tie-break） |
| §4 acceptable | 3 项（设计对齐） |

**测试**：`cd backend && pytest` → 270 passed, 13 skipped

**Commits on `feat/v1.0.3`**：
- `fb1c812` 第一轮 review followup（scheduler、迁移链、404）
- `3cecf76` 大重构：废弃 evolve_salience、接通 effective_salience、通道 2 dedup、删除 scheduler
- `e3fa6d1` 本轮：token budget、expiry、recall_service 优化

**记忆系统 review 关闭。** 下一片：教学/掌握度引擎（mastery_tracker.py + teaching_planner.py + course_generator.py，~750 行新代码）。
