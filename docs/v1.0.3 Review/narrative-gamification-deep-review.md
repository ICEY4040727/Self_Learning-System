# 叙事/成就引擎深度 Review — 工作清单

> Branch: `feat/v1.0.3`
> Scope: Phase 3 commit `cefd4da` 的叙事 + 成就子系统
> Files in scope:
> - `backend/services/narrative_engine.py` (185 new)
> - `backend/services/gamification.py` (211 new)
> - `backend/api/routes/achievements.py` (35 new)
> - `backend/services/prompt_builder/modules/narrative.py` (97 new)
> - `backend/tests/test_narrative_gamification.py` (324)
> - 集成点：`learning_engine.py:276` (narrative) + `:297` (achievements)
> - Models: `NarrativeTriggerRule`, `AchievementDef`, `Achievement` (UniqueConstraint user+char+key)
> Last updated: 2026-04-27

同 `memory-system-deep-review.md` 和 `teaching-system-deep-review.md`，本文档是工作记录。**Claude 上下文窗口有限，本文档是唯一可信的进度来源**。

---

## 1. 已修复（已 commit）

（暂无 — 本片刚开始）

---

## 2. 待修复 — 初轮扫描发现

按严重性排序。

### TODO-N1 ✅ — `/achievements/{user_id}/{character_id}` 完全没有 auth 🔴 **P0**

- **位置**：`backend/api/routes/achievements.py:23`
- **修复**：加 `current_user: User = Depends(get_current_user)`，user_id != current_user.id → 403
- **测试**：3 个新测试（`TestAchievementsRouteAuth`）— 401 unauth / 403 wrong user / 200 owner
- **状态**：✅ done（待 commit）

### TODO-N2 ✅ — `gamification.check_achievements` 用 `db.rollback()` 救场会清空整个事务 🔴 **P0**

- **位置**：`gamification.py:91`
- **修复**：每条 INSERT 用 `with db.begin_nested():` 包住。SAVEPOINT 让 IntegrityError 只回滚这一条，外层事务 + 之前的 mastery / narrative writeback / ChatMessage 都活着。同时 except 改成 `logger.info` 而非吞错。
- **测试**：2 个新测试 — `test_pre_existing_writes_survive_engine_call`（黑盒：canary 活下来）+ `test_savepoint_absorbs_unique_collision`（白盒：直接演示 SAVEPOINT 模式吞 IntegrityError 不破坏外层）
- **状态**：✅ done（待 commit）

### TODO-N3 ✅ — `narrative_engine` `fact_count_threshold` 缺 world_id filter 🔴 **P0/P1**

- **位置**：`narrative_engine.py:160`
- **修复**：world_id 已经在 check_triggers / _check_condition 链路里传，给 SQL 加 `(world_id == X) | (world_id IS NULL)` filter（与 observe_recent 语义一致）
- **测试**：2 个新测试 — `test_struggles_in_other_world_do_not_trigger`（隔离）+ `test_struggles_in_same_world_still_trigger`（防过紧）
- **状态**：✅ done（待 commit）

### TODO-N4 ✅ — 多个 condition_type 是死规则（模型列但 engine 不识别） 🟡 **P1**

- **位置**：`narrative_engine.py` + `gamification.py` 的 `_check_condition`
- **修复**：两处 `_check_condition` 末尾加 `else: logger.warning(...)`，让 ops 看见。`NarrativeTriggerRule.condition_type` 和 `AchievementDef.condition_type` 的 column 注释改成"实现的 / 历史列出但未实现"分类。
- **真正实现 time_gap / consecutive_days / profile_shift / session_event** 留作 backlog
- **状态**：✅ done（待 commit）

### TODO-N5 ✅ — `narrative_engine` writeback 绕过 `memory_manager.write_facts` 🟡 **P1**

- **位置**：`narrative_engine.py:93`
- **修复**：从 `db.add(MemoryFact(...))` 换成 `memory_manager.write_facts(db, character_id, world_id, [{...}])`。dedup / t_valid / 未来 ChromaDB 同步全部生效
- **状态**：✅ done（待 commit）

### TODO-N6 ✅ — `condition_params` 同时处理 str 和 dict — 实际是 schema drift 🟡 **P2**

- **真相**：审下来发现两个分支**都不是死代码**：
  - 模型 `condition_params = Column(JSON)` → 测试（用 model 的 create_all）和 PG 生产返回 dict
  - 迁移 `2026_04_25_add_narrative_and_achievements.py:158/191` 创建的是 **TEXT** 列，并 INSERT JSON 字符串 → SQLite 生产返回 str
- **修复**：两处加详细注释说明 schema drift；保留两条解析分支
- **真正修复 schema**（迁移把 TEXT → JSON + 数据迁移）留作后续 issue（迁移有真实生产数据风险，单独评估）
- **状态**：✅ done（已注释，schema 修复 deferred）

### TODO-N7 ✅ — `get_achievements_status` O(N×M) 扫描 🟢 **P2**

- **位置**：`gamification.py:185`
- **修复**：循环外建 `unlocked_by_key = {a.achievement_key: a for a in unlocked}`，循环内 O(1) lookup
- **状态**：✅ done（待 commit）

### TODO-N8 ✅ — `get_achievements_status` 没有 user 隔离校验 🟢 **P2**

- **审完结论**：grep `get_achievements_status` 全 backend 只有一处 caller — 已被 N1 修过的路由。无其它 API 入口暴露此方法
- **状态**：✅ done — N1 已覆盖，无遗漏暴露面

### TODO-N9 ✅ — `event_template` 占位符替换不安全 🟢 **P3**

- **位置**：`narrative_engine.py:_safe_format`
- **修复**：新增 `_SafeDict` (missing key 返回字面 `{key}`) + `_safe_format()` helper 走 `str.format_map`。一次替换，缺 key 不崩，val 含 `{x}` 不递归。malformed 模板捕获 ValueError/IndexError 兜底原文返回
- **状态**：✅ done（待 commit）

---

## 3. 新发现（执行过程中追加）

> 在做 TODO-N1 ~ N9 时如果发现新问题，append 到下面。

（暂无）

---

## 4. 已知 Acceptable / 不修

| ID | 问题 | 为什么不修 |
|---|---|---|
| R1-02 | `_cooldowns` 内存级 dict | 已在前轮标 acceptable；多 worker 部署再说 |
| Priority 默认 | priority 不在 map 里默认 medium | 容错合理 |

---

## 5. 工作流约定

1. 开始一项 → TaskUpdate 标 in_progress
2. 改完代码 → 跑相关测试（`test_narrative_gamification.py` 是 real-DB，靠谱）
3. 通过 → 更新本文档对应 TODO 的状态为 ✅ done + commit hash
4. 发现新问题 → append §3，新建 TaskCreate
5. **特别警告**：N2 那条事务回滚问题 = 沉默的数据丢失，必须单独写 real-DB 回归测试覆盖（"前面 mastery 改动 + 后面 achievement 重复 INSERT" 场景）

## 6. 离开本片的判定标准

- §2 P0 + P1 全部 ✅ 或显式 deferred
- §3 全部消化
- 全套测试 pass（`cd backend && pytest`）
- 然后才进入 Phase 3 下一片（教材子系统：`api/routes/textbook.py` 449 行新代码）

---

## 7. 完成态（2026-04-27）

| Section | 状态 |
|---|---|
| §1 已修复 | 9 项（N1-N9 全 ✅） |
| §2 待修复 | 0 |
| §3 新发现 | 0 |
| §4 acceptable | 2 项（R1-02 内存冷却、priority 默认） |

**测试**：`cd backend && pytest` → 287 passed, 13 skipped
**Alembic**：仍 single head (`2026_04_27_fsrs_card_data`), single base

**Commits on `feat/v1.0.3`**：
- `e0ca2ba` N1-N5（auth, savepoint, world_id, dead rules, writeback）
- 本轮（待 commit）N6-N9（schema drift doc, O(N+M), N1 follow-up confirmation, safe format）

**两个意外发现**：
- N6 不是死代码而是 schema drift — 迁移建 TEXT、模型说 JSON。两条 parse 分支真的都需要。真正修迁移有数据风险，单独 issue
- N4 实施时清楚看到：4 种 condition_type（time_gap / consecutive_days / profile_shift / session_event）在模型 docstring 列了但 engine 没实现，没有任何 lint 抓得到这种 dead-rule 陷阱

**叙事/成就 review 关闭。** 下一片：教材子系统（`api/routes/textbook.py` 449 行新代码 + 教材表迁移 + course_generator 集成）— 是 cefd4da 里**最大的单文件**。
