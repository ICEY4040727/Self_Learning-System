# 04 叙事系统 — 详细设计

> **版本**：v1.0.4  
> **日期**：2026-06-20  
> **状态**：已落地（观察者引擎可用，前后端契约与部分条件未实现）  
> **上级文档**：[四大系统闭环架构设计 — 总览](WholeDesign.md)  
> **关联文档**：[01 记忆系统](01_memory_system.md) | [02 学习画像](02_learner_profile.md) | [03 教学系统](03_teaching_system.md)

---

### 代码锚点引用规范

凡描述**已实现功能**的条目，均附可点击源码锚点（路径相对 `docs/v1.0.4/`）。

| 写法 | 示例 |
|------|------|
| `[文件:行](../../path#L行)` | [`memory_manager.py:255`](../../backend/services/memory_manager.py#L255) |
| `[文件:起-止](../../path#L起-L止)` | [`extract:255-371`](../../backend/services/memory_manager.py#L255-L371) |

---

## 1. 系统定位与边界

### 1.1 定位

叙事系统提供**零 LLM 成本的沉浸式反馈层**，包含两条互补能力：

| 子能力 | 职责 | 用户感知 |
|--------|------|---------|
| **叙事触发引擎**（`NarrativeEngine`） | 观察学习信号，触发即时 UI 事件（toast/modal） | 突破、困难连锁、关系进阶 |
| **成就引擎**（`GamificationEngine`） | 检测累计条件，持久化解锁记录 | 徽章、里程碑、隐藏成就 |
| **课程叙事注入**（`NarrativeModule`） | 将 `course_narrative_plan` 写入教学 Prompt | Sage 对话风格与历险设定一致 |

与 v1.0.4 产品收束对齐：**世界壳不生成剧情**；课程级 `course_narrative_plan` 约束教学语气；**运行时叙事事件**由规则表驱动，非 LLM 即兴编剧。

### 1.2 观察者模式约束

```
LearningEngine.process_message
        │（LLM 之后）
        ├─► narrative_engine.check_triggers()   只读 MemoryFact / relationship
        └─► gamification_engine.check_achievements()  只读 profile / facts / stats
```

| 允许 | 禁止 |
|------|------|
| 读 DB 规则表与运行时状态 | 调用 LLM |
| 写 `Achievement` 解锁行 | 修改 `Session.relationship`（属教学系统） |
| 可选写回 `MemoryFact`（`fact_type=event`） | 直接改 `LearnerProfile.dimension_scores` |

### 1.3 系统边界

| 范围内 | 范围外 |
|--------|--------|
| `narrative_trigger_rules` / `achievement_defs` L2 规则 | 世界创建向导 UI |
| `NarrativeEngine` / `GamificationEngine` | `RelationshipService` 维度演算 |
| `NarrativeModule` Prompt 注入 | 前端 Galgame 立绘资源 |
| `achievements` 解锁记录表 | 经验值/等级（`Character.level` 遗留字段） |
| `relationship_stages` 审计表（关系变化日志） | 关系 delta 计算 |

### 1.4 实现进度量化

| 模块 | 代码行数 | 测试 | 稳定性 |
|------|---------|------|--------|
| [`narrative_engine.py`](../../backend/services/narrative_engine.py) | 234 | test_narrative_gamification | B- |
| [`gamification.py`](../../backend/services/gamification.py) | 238 | 同上 | B- |
| `prompt_builder/modules/narrative.py` | 96 | `test_prompt_builder.py` | B |
| `prompt_builder/modules/world_setting.py` | 56 | 间接 | B |
| `api/routes/achievements.py` | 45 | 无专项 | B |
| **合计** | **~624 服务 + ~45 API** | — | **B-（~65%）** |

---

## 2. 架构总览

```
                    ┌─────────────────────┐
                    │   LearningEngine    │
                    │   (每轮 chat 后)     │
                    └──────────┬──────────┘
                               │
           recent_facts, stage, dimension_scores, learning_stats
                               │
              ┌────────────────┴────────────────┐
              ▼                                 ▼
    ┌──────────────────┐              ┌──────────────────┐
    │ NarrativeEngine  │              │ GamificationEngine│
    │ 读 narrative_    │              │ 读 achievement_   │
    │   trigger_rules  │              │   defs            │
    └────────┬─────────┘              └────────┬─────────┘
             │                                  │
             │ optional writeback               │ INSERT achievements
             ▼                                  ▼
      MemoryFact(event)                   achievements 表
             │                                  │
             └──────────────┬───────────────────┘
                            ▼
                   ChatResponse JSON
                   narrative_events[]
                   new_achievements[]
                            ▼
                   frontend learning.ts → Learning.vue toast
```

### 2.1 与「课程叙事 Prompt」的关系

| 类型 | 时机 | 机制 | 是否 LLM |
|------|------|------|---------|
| **静态叙事框架** | 每轮 build Prompt | [`narrative.py`](../../backend/services/prompt_builder/modules/narrative.py) 读 `course.meta` | 间接 |
| **动态叙事事件** | 每轮 chat 后 | [`narrative_engine.py:42`](../../backend/services/narrative_engine.py#L42) [`learning_engine.py:292-301`](../../backend/services/learning_engine.py#L292-L301) | 否 |
| **成就反馈** | 每轮 chat 后 | [`gamification.py:24`](../../backend/services/gamification.py#L24) [`learning_engine.py:314-323`](../../backend/services/learning_engine.py#L314-L323) | 否 |

---

## 3. 数据模型

### 3.1 `narrative_trigger_rules`（L2）

| 列 | 说明 |
|----|------|
| `trigger_type` | 唯一事件类型 key（如 `concept_mastered`） |
| `condition_type` | 引擎分支名（见 §4.1） |
| `condition_params` | JSON 参数（迁移种子为 TEXT 字符串，存在 schema drift） |
| `priority` | `high` / `medium` / `low` → 排序 |
| `cooldown_minutes` | 同用户+角色+trigger_type 冷却 |
| `writeback_memory` | 是否写 `MemoryFact` event |
| `event_template` | Python `format_map` 模板，如 `掌握了「{concept}」` |
| `prompt_template` | **预留**，当前引擎未使用 |
| `ui_template` | `toast` / `modal` / `badge`（前端应消费） |
| `enabled` | 开关 |

### 3.2 `achievement_defs`（L2）

| 列 | 说明 |
|----|------|
| `key` | 唯一成就 ID |
| `category` | milestone / growth / relationship / resilience / exploration / hidden |
| `condition_type` | 见 §5.1 |
| `condition_params` | JSON |
| `rarity` | common / rare / legendary |
| `hidden` | 解锁前是否对列表可见 |
| `enabled` | 开关 |

### 3.3 `achievements`（L3 运行时）

```sql
UNIQUE (user_id, character_id, achievement_key)
context JSON  -- 解锁时的统计快照
```

成就按 **(用户, Sage 角色)** 隔离，非 per-world。

### 3.4 `relationship_stages`（审计）

阶段记录：[`learning_engine.py:225-231`](../../backend/services/learning_engine.py#L225-L231)；叙事读参 [`narrative_engine.py:42-60`](../../backend/services/narrative_engine.py#L42-L60)。

### 3.5 课程叙事配置（L3）

存储于 `Course.meta.course_narrative_plan`（v1.0.4 语义，替代历史 `world_plan`）：

```json
{
  "world": { "name": "..." },
  "route_bible": { "main_arc": "...", "boundaries": ["..."] },
  "ai_generated": {
    "world_theme": "",
    "learner_role": "",
    "sage_role": "",
    "knowledge_metaphor": "",
    "progression_arc": ""
  }
}
```

`NarrativeModule` 解析上述字段注入【历险叙事】段。

---

## 4. 叙事触发引擎（NarrativeEngine）

### 4.1 已实现 `condition_type`

| condition_type | 逻辑 | 种子规则 |
|----------------|------|---------|
| `fact_created` | `recent_facts` 中存在指定 `fact_type` | `concept_mastered` |
| `fact_count_threshold` | 时间窗内 DB 计数 ≥ threshold | `struggle_cascade` |
| `relationship_stage_change` | `current_stage != prev_stage` | `stage_change` |
| `time_gap` | **未实现**（pass） | `welcome_back` ⚠️ |

**未实现（模型注释列举）**：`profile_shift`, `session_event` — 配置后静默 warning。

### 4.2 `fact_created` 细节

- 仅检查**本轮** `recent_facts`（Channel-1 提取结果对象列表）
- 参数 `requires_prior_struggle`（`breakthrough` 种子）**未在代码中处理** ⚠️

### 4.3 `fact_count_threshold` 细节

- 查询 `MemoryFact`：`character_id` + (`world_id` 匹配或 NULL) + `created_at >= now - window`
- 达阈值后从最近一条取 `concept_tags[0]` → 模板变量 `{concept}`

### 4.4 冷却机制

```python
_cooldowns: dict[(user_id, character_id, trigger_type), datetime]  # 类变量，进程内存
```

| 特性 | 影响 |
|------|------|
| 进程内有效 | 多 worker 各自冷却，可能重复触发 |
| 重启丢失 | 冷却重置，短时或重复弹窗 |
| 粒度 | per user + per sage + per trigger_type |

**改造方向**：`narrative_cooldowns` 表或 Redis。

### 4.5 记忆写回

当 `writeback_memory=True`：

```python
memory_manager.write_facts(..., [{
  "fact_type": "event",
  "content": f"叙事事件: {event_text}",
  "concept_tags": tags,
  "salience": 0.6,
}])
```

走记忆系统去重与 `t_valid` 逻辑（TODO-N5 已修复直连 `db.add`）。

### 4.6 输出事件契约（后端）

```json
{
  "type": "concept_mastered",
  "text": "你成功掌握了「递归」！",
  "ui_template": "toast",
  "priority": "high"
}
```

按 `priority` 排序后附加到 `ChatResponse.narrative_events`。

---

## 5. 成就引擎（GamificationEngine）

### 5.1 已实现 `condition_type`

| condition_type | 逻辑 | 种子示例 |
|----------------|------|---------|
| `stat_threshold` | `stats[stat] >= threshold` | `first_step`, `regular_visitor`, `knowledge_seeker` |
| `dimension_crossing` | `dimension_scores[dim] >= threshold` | `abstract_awakening` |
| `relationship_stage` | `index(current) >= index(target)` | `kindred_spirit` → friend |
| `fact_transition` | 本轮 `recent_facts` 含 `to` 类型 | `learn_from_setback` |
| `fact_count_threshold` | 本轮 fact 类型计数 | （无种子） |

**未实现**：`consecutive_days`（若种子存在则永不解锁）。

### 5.2 统计源 `stats` 断裂（P0）

`LearningEngine` 传入：

```python
learn_stats = lp.profile.get("learning_stats", {})
# 仅含 concepts_mastered, concepts_struggling — 无 total_sessions
```

| 成就 key | 需要 stat | 生产 chat 路径 |
|----------|-----------|---------------|
| `first_step` | `total_sessions >= 1` | **不触发** |
| `regular_visitor` | `total_sessions >= 10` | **不触发** |
| `knowledge_seeker` | `concepts_mastered >= 5` | **可触发** |
| `night_owl` | `late_night_session >= 1` | **无写入器，永不触发** |

`total_sessions` 在 `end_session` 写入 `LearnerProfile.session_count` 与 `UserProfile`，但 **chat 路径成就检查不读取**。

### 5.3 `dimension_crossing` 语义

当前实现为 **当前值 ≥ 阈值即触发**，非「从低于阈值跨越到高于阈值」的一次性事件。首次聚合出 0.6 分时即可解锁；重复解锁由 DB `UNIQUE` 约束阻止。

### 5.4 并发与事务

每个成就 `INSERT` 使用 `db.begin_nested()` SAVEPOINT；`UniqueConstraint` 冲突时跳过，**不 rollback 整轮** chat 事务（TODO-N2）。

### 5.5 输出契约（后端）

```json
{
  "key": "first_step",
  "display_name": "初入世界",
  "description": "完成第一次学习",
  "rarity": "common",
  "icon": "",
  "category": "milestone",
  "context": {"stat": "total_sessions", "value": 1, "threshold": 1}
}
```

---

## 6. 课程叙事 Prompt（NarrativeModule）

属教学系统 Prompt 栈，固定层 `always_include=True`，优先级 10。

| 读取字段 | Prompt 片段 |
|---------|------------|
| `world_theme` / `world.name` | 当前历险世界 |
| `learner_role` / `sage_role` | 角色扮演 |
| `knowledge_metaphor` | 知识比喻 |
| `progression_arc` / `main_arc` | 成长主线 |
| `boundaries` | 叙事边界（禁止话题） |

无 `course_narrative_plan` 时模块返回 `None`，不注入【历险叙事】。

**与 `WorldSettingModule` 分工**：

| 模块 | 数据源 | 内容 |
|------|--------|------|
| WorldSetting | `World.description` | 世界壳舞台 |
| Narrative | `Course.meta.course_narrative_plan` | 课程历险与角色分工 |

---

## 7. 闭环链路

### 7.1 记忆 → 叙事

| 维度 | 评估 |
|------|------|
| **强度** | 0.70 |
| **路径** | `recent_facts` + DB 窗内计数 → `narrative_trigger_rules` |
| **缺陷** | `time_gap` / `breakthrough` 参数未实现；冷却非持久 |
| **优化** | 补条件分支；冷却落库 |

### 7.2 画像 → 成就

| 维度 | 评估 |
|------|------|
| **强度** | 0.55 |
| **路径** | `dimension_scores` → `dimension_crossing`；`learning_stats` → `stat_threshold` |
| **缺陷** | `total_sessions` 缺失；`late_night_session` 无统计 |
| **优化** | 统一 stats 契约（见 [02 学习画像 §3.3](02_learner_profile.md)） |

### 7.3 叙事 → 记忆（二次闭环）

写回 `event` 类 MemoryFact → 下轮可被 `MemoryFactsModule` 检索 → 可能影响画像聚合（`event` 默认不参与 mastery delta）。

### 7.4 叙事 → 教学（Prompt）

`course_narrative_plan` → `NarrativeModule` → LLM 语气；与运行时 `narrative_events` **独立**。

---

## 8. 接口契约

### 8.1 内部服务

#### `narrative_engine.check_triggers(db, *, user_id, character_id, world_id, recent_facts, current_stage, prev_stage, context_vars=None) → list[dict]`

| 参数 | 说明 |
|------|------|
| `recent_facts` | 本轮 `ExtractedMemory` 或等效对象列表 |
| `context_vars` | 扩展模板变量；`time_gap` 需外部传入 `last_session_time`（当前未接） |

#### `gamification_engine.check_achievements(db, *, user_id, character_id, world_id, stats, dimension_scores, current_stage, recent_facts) → list[dict]`

#### `gamification_engine.get_achievements_status(db, *, user_id, character_id) → dict`

返回 `{unlocked, locked_visible, total_unlocked, total_available}`。

---

### 8.2 HTTP API

#### `GET /api/achievements/{user_id}/{character_id}`

| 鉴权 | `user_id` 必须等于 `current_user.id` |
| 响应 | `AchievementStatusResponse` |

#### Chat 响应内嵌字段（`POST /api/learning/courses/{id}/chat`）

见 [03 教学系统 §9.1](03_teaching_system.md)。

---

### 8.3 前后端契约断裂（P0）

| 后端字段 | 前端期望 | 影响 |
|---------|---------|------|
| `text` | `description` | 叙事 toast **正文为空** |
| `type` | `event_type` | 类型标签缺失 |
| `ui_template` | `scene` / 分支 UI | modal 与 toast 未区分 |
| `key` | `id` | 成就 ID 缺失 |
| `display_name` | `name` | 成就标题**为空** |

`learning.ts` 原样 push 后端对象，`Learning.vue` 绑定 `activeNarrative.description` / `activeAchievement.name` — **需对齐字段或增加适配层**。

---

## 9. 种子规则清单

### 9.1 叙事规则（5 条）

| trigger_type | condition | 冷却(min) | writeback | ui |
|--------------|-----------|-----------|-----------|-----|
| concept_mastered | fact_created | 5 | 否 | toast |
| struggle_cascade | fact_count 3/60min | 60 | **是** | modal |
| breakthrough | fact_created + prior_struggle | 30 | **是** | modal |
| stage_change | relationship_stage_change | 120 | 否 | toast |
| welcome_back | time_gap 3d | 1440 | 否 | toast |

后两条条件引擎**未完整实现**。

### 9.2 成就定义（7 条）

| key | category | condition | 生产可达性 |
|-----|----------|-----------|-----------|
| first_step | milestone | total_sessions≥1 | ❌ chat 路径 |
| regular_visitor | milestone | total_sessions≥10 | ❌ |
| knowledge_seeker | milestone | concepts_mastered≥5 | ✅ |
| abstract_awakening | growth | abstract_thinking≥0.5 | ✅（需维度聚合） |
| learn_from_setback | resilience | fact_transition | ⚠️ 未校验 from struggle |
| kindred_spirit | relationship | stage≥friend | ✅ |
| night_owl | hidden | late_night_session≥1 | ❌ 无 stat |

---

## 10. 可调参数

### 10.1 L2 规则表（推荐运营入口）

新增叙事/成就 = INSERT 一行；**必须**使用引擎已实现的 `condition_type`，否则仅打 warning。

### 10.2 L1 硬编码

| 项 | 位置 |
|----|------|
| 关系阶段顺序 | `RELATIONSHIP_STAGE_LABELS` / `_STAGE_ORDER` |
| 写回 salience 0.6 | `narrative_engine` |
| priority 排序映射 | high=0, medium=1, low=2 |

### 10.3 L3

`achievements` 解锁记录、`MemoryFact` event 写回、`_cooldowns` 内存态。

---

## 11. 前端消费

| 组件 | 行为 |
|------|------|
| `learning.ts` | chat 响应追加 `narrativeEvents` / `newAchievements` |
| `Learning.vue` | watch 长度 → toast 4s / 5s 自动消失 |
| `ui_template=modal` | **未单独实现** modal 组件分支 |

建议：根据 `ui_template` 分支；或统一 BFF 适配字段名。

---

## 12. 测试覆盖

`test_narrative_gamification.py` 覆盖：

- 各 `condition_type` 正向触发
- 冷却跳过
- 写回 MemoryFact
- 成就 SAVEPOINT 并发
- `get_achievements_status` 列表

**缺口**：生产路径 `learning_stats` 契约；前后端字段映射；`time_gap`；`breakthrough`；多 worker 冷却。

---

## 13. 已知缺陷与改造路线图

| 优先级 | 项 |
|--------|-----|
| **P0** | 修复前后端 `narrative_events` / `new_achievements` 字段映射 |
| **P0** | `learning_stats.total_sessions` 接入成就检查 |
| P1 | 实现 `time_gap`、`breakthrough.requires_prior_struggle` |
| P1 | 冷却持久化 |
| P1 | 实现 `late_night_session` 统计或下线 `night_owl` 种子 |
| P2 | `prompt_template` 列利用或删除 |
| P2 | `dimension_crossing` 改为真正「跨越」检测 |
| P2 | `fact_transition` 校验 `from` 历史 struggle |
| P3 | 叙事事件 WebSocket 推送（当前仅 chat 轮询） |

---

## 14. 硬编码风险清单

| ID | 内容 | 建议 |
|----|------|------|
| N-H1 | 冷却内存 dict | DB/Redis |
| N-H2 | condition_type 无注册表校验 | 管理后台 + 启动时校验种子 |
| N-H3 | migration TEXT vs model JSON drift | 统一 Alembic 列类型 |
| N-H4 | `RELATIONSHIP_STAGE_LABELS` 与叙事模板中文案未联动 | 模板用 `{new_stage}` 变量 |
| N-H5 | 前端 toast 固定 4s/5s | 可配置或按 priority |

---

## 15. 与总览文档交叉引用

| 总览链路 | 本系统责任 |
|---------|-----------|
| 记忆 → 叙事 | §7.1 |
| 画像 → 成就 | §7.2 |
| 教学 → 叙事 | `LearningEngine` 步骤 18–19 |
| 叙事 Prompt | §6 `NarrativeModule` |

---

*文档基于 `narrative_engine.py`、`gamification.py`、`prompt_builder/modules/narrative.py`、迁移种子、`api/routes/achievements.py`、前端 `learning.ts` / `Learning.vue` 代码勘探生成，2026-06-20。*

### 【叙事系统设计核心公理 · 用于AI辅助设计的Prompt】
请你基于以下**不可突破的核心定义与底层原则**，辅助我完成这套叙事系统的方案设计、细节推演与落地拆解，所有设计不得偏离以下底层框架。

---

#### 一、系统核心本质定义
本系统是**「结构化设定约束下的寄生式LLM叙事生成引擎」**，核心本质：
用硬规则锁死叙事边界与决策底线，用LLM完成设定间的逻辑推导、人设还原与自然语言表达，完全复用主业务LLM调用实现零额外成本，同时规避「纯规则模板套路感强」和「纯LLM生成不可控」两种极端方案的缺陷。

#### 二、不可动摇的5条底层设计公理
所有设计必须严格遵守，不得突破：
1.  **零额外LLM成本公理**：叙事系统无独立LLM调用，100%寄生在主教学对话的LLM请求中，通过自定义标签并行输出叙事结果，不增加API调用次数，仅增加极少量token开销。
2.  **规则主权公理**：LLM永不拥有叙事决策权，仅承担「设定联动推导 + 文本润色」职能；事件触发的合法性、节奏控制权完全在后端规则侧，LLM输出必须经过规则校验才可生效。
3.  **全结构化输入公理**：所有世界观、角色、用户画像数据必须以结构化/量化形式注入Prompt，禁止投喂大段自由文本设定，从输入侧杜绝LLM语义偏差与设定篡改。
4.  **三重防护公理**：所有LLM叙事输出必须经过「前置输入约束→中置格式强制→后置规则校验」三层过滤，异常输出直接丢弃并降级到纯规则兜底，保证主流程零故障。
5.  **数据驱动公理**：所有约束规则、设定参数、事件类型全部存储于数据库，通过新增配置行扩展能力，禁止在业务代码中硬编码叙事逻辑。

#### 三、核心解决的矛盾
设计必须针对性解决以下问题，不得回到两种旧方案老路：
- 解决纯规则引擎的缺陷：设定仅做标签匹配、无法产生人设与世界观的化学反应、模板套路感强、规则开发维护成本高
- 解决纯LLM生成的缺陷：叙事不可控、易突破设定、提前触发结局、调用成本高、输出不稳定
- 适配现有「记忆-学习画像-教学-叙事」四大系统闭环架构，不打破观察者模式与「教学系统为唯一LLM入口」的约束

#### 四、最简核心数据流链路
所有模块设计必须围绕这条链路展开，不得新增冗余节点：
1.  **输入侧**：从现有记忆、学习画像、教学三大系统读取结构化状态数据——世界观铁则、角色心智参数、用户学习/情感/关系状态、本轮对话事实
2.  **注入侧**：将上述数据按「铁则层→状态层→事实层→格式层」的优先级组装为Prompt片段，注入主教学System Prompt
3.  **生成侧**：LLM在生成教学回复的同时，按强制标签格式输出叙事事件判断与内容
4.  **校验侧**：后端解析标签结果，执行「阶段锁校验→世界观合规校验→冷却状态校验」三道规则
5.  **输出侧**：校验通过则向前端输出叙事事件，失败则回退纯规则引擎兜底；同时可选将事件写回记忆系统形成二次闭环

#### 五、硬性架构约束
必须兼容现有技术体系，不得推翻重构：
- 服从四大系统的观察者模式：叙事系统只读上游数据，不反向修改教学、画像、记忆的核心逻辑
- 兼容现有数据库表结构，仅可扩展字段，不可推翻重构
- 叙事事件的前端消费契约保持不变，不侵入前端逻辑
- 所有新增能力必须可灰度、可降级、可开关

#### 六、最终设计目标
所有细节设计都要服务于这几个结果：
1.  叙事具备设定联动性：角色性格、世界观规则、用户行为轨迹会共同影响事件内容，产生“化学反应”，而非简单标签匹配
2.  无明显模板套路感：同类型事件的表达、细节、语气随用户状态动态变化
3.  叙事节奏完全可控：通过阶段锁、冷却机制避免提前触发结局，防止高能剧情透支
4.  稳定性优先：LLM异常时无感降级，主教学流程不受任何影响