# 02 学习画像 — 详细设计

> **版本**：v1.0.4  
> **日期**：2026-06-20  
> **状态**：已落地（维度聚合与掌握度主路径可用，数据契约与课程进度双源待收敛）  
> **上级文档**：[四大系统闭环架构设计 — 总览](WholeDesign.md)  
> **关联文档**：[01 记忆系统](01_memory_system.md)

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

学习画像系统将离散的学习信号（记忆事实、情感、对话偏好、掌握度事件）**聚合为可度量、可驱动教学与成就的学习者模型**。它是记忆系统与教学系统之间的「建模层」，输出结构化分数与统计，供策略规则、成就条件、前端展示消费。

理论依据：`docs/learning_memory_theory.md`（ITS 覆盖/扰动模型、MSKT 元认知四维度、BKT/FSRS 知识追踪）。

### 1.2 双层架构

| 层级 | 存储 | 作用域 | 是否注入 Prompt |
|------|------|--------|----------------|
| **世界内画像** | `learner_profiles.profile` JSON | per `(user_id, world_id)` | **是**（策略/偏好/元认知/误解模块） |
| **跨世界画像** | `user_profiles.profile` JSON | per `user_id` | **否**（仅展示/报表/Seed Memory 来源） |
| **概念掌握度** | `concept_mastery` + `fsrs_states` 表 | per `(user_id, concept_id)` 跨世界 | 间接（`mastery_level` 待接入教学 context） |
| **课程进度** | `course_progress` + `progress_trackings` | per course / topic | 属教学系统，画像系统读写交界 |

**角色区分**（与游戏层解耦）：

- `Character.type=traveler`：游戏叙事角色（玩家化身）
- `LearnerProfile`：学习追踪层（记录认知状态），通过 `Session.learner_profile_id` 关联

### 1.3 系统边界

| 范围内 | 范围外 |
|--------|--------|
| `ProfileAggregator` 维度聚合 | `MemoryFact` 写入（属记忆系统） |
| `DynamicAnalyzer.update_learner_profile` 情感/偏好轻量更新 | LLM 情感分类本身 |
| `MasteryTracker` + `ConceptMastery` + FSRS | `LessonPlan` 章节 DAG 管理 |
| `UserProfile` 跨世界聚合 | 叙事规则匹配 |
| `profile_dimension_defs` 规则表 | `strategy_rules` 内容（属教学 L2，消费画像输出） |

### 1.4 核心设计约束

1. **零 LLM 聚合**：[`profile_aggregator.py:31`](../../backend/services/profile_aggregator.py#L31)；编排 [`learning_engine.py:258-264`](../../backend/services/learning_engine.py#L258-L264)。
2. **数据驱动维度**：模型 [`models.py:462`](../../backend/models/models.py#L462)；聚合循环 [`profile_aggregator.py:63-74`](../../backend/services/profile_aggregator.py#L63-L74)。
3. **幻觉防护**：[`profile_aggregator.py:108`](../../backend/services/profile_aggregator.py#L108)；阈值 [`config.py:70`](../../backend/core/config.py#L70)。
4. **Merge Write**：[`profile_aggregator.py:74-95`](../../backend/services/profile_aggregator.py#L74-L95) 仅覆盖列出的键。
5. **跨世界掌握度**：[`models.py:319`](../../backend/models/models.py#L319)、[`models.py:338`](../../backend/models/models.py#L338)；更新 [`mastery_tracker.py:56`](../../backend/services/mastery_tracker.py#L56)。

### 1.5 实现进度量化

| 模块 | 代码行数 | 测试 | 稳定性 |
|------|---------|------|--------|
| [`profile_aggregator.py`](../../backend/services/profile_aggregator.py) | 282 | test_profile_aggregator | B |
| `user_profile.py` | 470 | `test_user_profile.py`（~17 cases） | B |
| `mastery_tracker.py` | 361 | `test_mastery_tracker.py`（~30 cases） | A |
| `spaced_repetition.py` | 93 | `test_fsrs.py`（8 cases） | A |
| Prompt 模块（preference/metacognition/misconception/episode） | 254 | `test_prompt_builder.py` | B |
| **合计** | **~1,460** | — | **B（~75%）** |

---

## 2. 架构总览

```
MemoryFact ──────────────────────────────┐
                                         ▼
DynamicAnalyzer ──► LearnerProfile       ProfileAggregator ──► dimension_scores
  (affect/preferences)   .profile JSON         ▲                    strengths/weaknesses
                                         │                    learning_stats
Channel-1 facts ──► MasteryTracker ──────┼──► ConceptMastery
                    │                    │         FSRSState
                    └─ auto_advance ─────┘
                                         │
LearnerProfile (per world) ──► UserProfile (cross-world, 展示 only)
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
            StrategyModule      GamificationEngine      前端 CoursePage
            PreferenceModule      (dimension_crossing)   MemoryFactsDrawer
            MetacognitionModule   (stat_threshold ⚠️)
```

### 2.1 主编排时序（`learning_engine.process_message`）

| 步骤 | 动作 | 写入目标 |
|------|------|---------|
| 11 | [`dynamic_analyzer.py`](../../backend/services/dynamic_analyzer.py) [`learning_engine.py:205-212`](../../backend/services/learning_engine.py#L205-L212) | — |
| 14 | `update_learner_profile` | `LearnerProfile.affect` / `preferences` / `metacognition.self_confidence` |
| 15 | [`profile_aggregator.py:31`](../../backend/services/profile_aggregator.py#L31) [`learning_engine.py:258-264`](../../backend/services/learning_engine.py#L258-L264) | dimension_scores 等 |
| 16 | `update_user_profile_after_chat` | `UserProfile.raw_worlds[world_id]` + `aggregated` |
| 17.6 | [`mastery_tracker.py:56`](../../backend/services/mastery_tracker.py#L56) [`learning_engine.py:284-290`](../../backend/services/learning_engine.py#L284-L290) | ConceptMastery / FSRS / course.meta |

**会话结束**（`POST /sessions/{id}/end`）：

| 动作 | 写入目标 |
|------|---------|
| `LearnerProfile.session_count++` | 世界内会话计数 |
| `update_user_profile_after_session_end` | `UserProfile` 增量 `total_sessions` |

---

## 3. 数据模型

### 3.1 `learner_profiles` 表

```sql
id          INTEGER PK
user_id     INTEGER FK → users.id
world_id    INTEGER FK → worlds.id  -- CASCADE
profile     JSON NOT NULL default {}
created_at  DATETIME
updated_at  DATETIME
```

**无唯一约束在模型层显式声明**，业务约定 `(user_id, world_id)` 唯一；由 `archive` CRUD 与 `DynamicAnalyzer` 懒创建保证。

### 3.2 `LearnerProfile.profile` JSON 契约

| 字段 | 写入方 | 类型 | 用途 |
|------|--------|------|------|
| `dimension_scores` | ProfileAggregator | `dict[str, float]` | 0–1 维度分数，键对齐 `profile_dimension_defs.key` |
| `dimension_snapshots` | ProfileAggregator | `dict[str, {prev, updated_at}]` | 维度变化审计 |
| `strengths` | ProfileAggregator | `list[str]` | 分数 ≥ `strength_threshold`（0.7）的维度 key |
| `weaknesses` | ProfileAggregator | `list[str]` | 分数 ≤ `weakness_threshold`（0.4）的维度 key |
| `learning_stats` | ProfileAggregator | `dict` | 见 §3.3 |
| `affect` | DynamicAnalyzer | `dict` | `last_emotion`, `count_{emotion}` |
| `preferences` | DynamicAnalyzer | `dict` | `example_first`, `step_by_step` 等布尔或嵌套对象 |
| `metacognition` | DynamicAnalyzer（轻量）/ 未来 LLM | `dict` | MSKT 四维度或 `self_confidence` |
| `misconceptions` | **未自动写入** | `dict[id → object]` | Prompt `MisconceptionModule` 读取 |
| `episodes` | **未自动写入** | `list[dict]` | Prompt `EpisodeModule` 读取 |
| `session_count` | `end_session` API | `int` | 世界内完成会话数 |

**硬编码风险**：`misconceptions` / `episodes` 结构在 Prompt 模块中约定，但**主路径无写入器**，模块长期为空。

### 3.3 `learning_stats` 双源契约（重要）

| 来源 | 字段 | 说明 |
|------|------|------|
| `ProfileAggregator._compute_learning_stats` | `concepts_mastered`, `concepts_struggling` | MemoryFact 行数统计（跨 world，按 character） |
| **缺失** | `total_sessions` | **未由聚合器写入** |
| `LearnerProfile.session_count` | 世界内计数 | 仅 `end_session` 时 +1 |
| `UserProfile.aggregated.learning_stats` | `total_sessions` 等 | 跨世界汇总，依赖 `raw_worlds[].session_count` |

**断裂点（P0）**：`GamificationEngine` 在 `process_message` 中读取 `LearnerProfile.learning_stats.total_sessions`，但聚合器从不写入该字段 → 里程碑成就（`first_step` 等）在生产 chat 路径不触发。`end_session` 更新的 `session_count` 亦未同步进 `learning_stats`。

### 3.4 `user_profiles` 表

```sql
id          INTEGER PK
user_id     INTEGER FK UNIQUE
profile     JSON  -- { raw_worlds: {world_id: {...}}, aggregated: {...} }
computed_at DATETIME
```

**设计原则**（`user_profile.py` 注释）：跨世界特征**仅用于展示**，不注入教学 Prompt。

`aggregated` 核心字段：

| 字段 | 计算函数 |
|------|---------|
| `metacognition_trend` | `compute_metacognition_trend` — 需 ≥2 世界才得 `improving/stable` |
| `preference_stability` | `compute_preference_stability` — 跨世界偏好一致率 |
| `learning_stats` | `compute_learning_stats` — `total_sessions` / `average_mastery` / `worlds_explored` |

缓存策略：`get_user_profile` 在 `computed_at` 超过 **24 小时**时重新聚合。

### 3.5 `profile_dimension_defs` 规则表（L2）

| 列 | 说明 |
|----|------|
| `key` | 唯一维度标识，被 `strategy_rules.dimension_key` 引用 |
| `display_name` | 前端展示名 |
| `category` | `cognitive` / `metacognitive` / `affective` |
| `source_fact_types` | 参与聚合的 MemoryFact 类型列表 |
| `aggregation_method` | 见 §4 |
| `aggregation_params` | 方法参数 JSON |
| `value_range` | 默认 `{"min":0,"max":1}` |
| `enabled` | 开关 |

**种子数据（5 维）** — migration `2026_04_25_profile_dims`：

| key | display_name | category | method |
|-----|-------------|----------|--------|
| `abstract_thinking` | 抽象思维 | cognitive | `ratio` |
| `problem_solving` | 问题解决 | cognitive | `conversion_rate` |
| `self_monitoring` | 自我监控 | metacognitive | `keyword_extract` |
| `learning_resilience` | 学习韧性 | affective | `conversion_rate` |
| `engagement` | 学习投入 | affective | `emotion_balance` |

### 3.6 `concept_mastery` 表

```sql
UNIQUE (user_id, concept_id)
mastery_level   INTEGER 0-100
last_review     DATETIME
next_review     DATETIME nullable
```

权威跨世界掌握度数值；与 `ProgressTracking`（课程级、带 `topic_type`）并存，新逻辑以本表为准（TR-A1）。

### 3.7 `fsrs_states` 表

```sql
UNIQUE (user_id, concept_id)
world_id     nullable  -- 首次记录诊断用，不参与键
card_data    JSON      -- py-fsrs Card.to_dict() 权威载荷
difficulty, stability, last_review, next_review, reps  -- SQL 便利列
```

---

## 4. 维度聚合引擎（ProfileAggregator）

### 4.1 入口

```python
profile_aggregator.aggregate(
    db, character_id=sage_id, world_id=world_id, user_id=user_id
) -> dict | None
```

**前置条件**：存在 `LearnerProfile(user_id, world_id)` 行；存在 `enabled=True` 的 `ProfileDimensionDef` 行。否则返回 `None`。

### 4.2 聚合方法一览

| method | 公式 / 逻辑 | 种子维度 |
|--------|------------|---------|
| `ratio` | `count(positive_types) / count(total_types)` | abstract_thinking |
| `conversion_rate` | `count(to_type) / (count(from_type)+count(to_type))` | problem_solving, learning_resilience |
| `count` | `min(count / max_expected, 1.0)` | （无种子，可扩展） |
| `keyword_extract` | 近期 fact `content` 中关键词命中密度 ×10 封顶 | self_monitoring |
| `emotion_balance` | `sum(positive count_*) / sum(all count_*)` 读 `profile.affect` | engagement |

### 4.3 跨世界聚合语义（TR-C1）

所有基于 MemoryFact 的聚合方法 **不按 `world_id` 过滤**，仅按 `character_id`（Sage）统计。

| 设计意图 | 副作用 |
|---------|--------|
| 同一 Sage 在多世界对学生的认知应一致 | 与记忆检索的 world 过滤不一致 |
| 减少冷启动噪声 | Channel-2 哨兵事实计入分母，可能稀释 ratio |

**建议（v1.0.5）**：聚合 SQL 增加 `concept_tags NOT LIKE '%__channel2_%'` 过滤，或按 `world_id` 可配置切换。

### 4.4 幻觉防护

`min_facts = learning_system.profile.hallucination_guard_min_facts`（默认 **3**）。

事实数不足时，该维度**不出现在** `dimension_scores`（非置 0）。导致：

- 新用户前若干轮 `StrategyModule` 无策略注入；
- `dimension_crossing` 成就需等分数首次出现。

### 4.5 strengths / weaknesses

```python
strengths  = [k for k, v in scores.items() if v >= strength_threshold]   # 0.7
weaknesses = [k for k, v in scores.items() if v <= weakness_threshold]   # 0.4
```

---

## 5. 轻量画像更新（DynamicAnalyzer）

`update_learner_profile(user_id, world_id, interaction, db)` 在每轮 chat **先于**聚合器执行。

| 输入 | 写入 |
|------|------|
| `emotion_type` | `affect.last_emotion`, `affect.count_{emotion}++` |
| 消息含「例子/example」 | `preferences.example_first = True` |
| 消息含「步骤/step」 | `preferences.step_by_step = True` |
| `confidence` | `metacognition.self_confidence` |

**硬编码风险**：偏好关键词「例子」「步骤」写死在 `dynamic_analyzer.py`，与 Channel-2 `preference_keywords` 部分重叠但未统一。

**与 engagement 维度时序**：同轮内先写 `affect` 再聚合，`emotion_balance` 可读到本轮情感；首轮无历史时 `engagement` 仍可能因 `min_facts` 未达标而缺失。

---

## 6. 掌握度追踪（MasteryTracker + FSRS）

### 6.1 输入与过滤

```python
mastery_tracker.update_from_memories(
    db, memories=recent_facts,  # Channel-1 ExtractedMemory 列表
    course_id, world_id, user_id,
)
```

| 规则 | 说明 |
|------|------|
| 仅 Channel-1 | `learning_engine` 故意不传 Channel-2 事实（TODO-T8） |
| `delta_map` | `concept_mastered` +25, `concept_struggle` -15, 其他 0 |
| 无 `concept_tags` | 跳过 |
| 哨兵 tag `__channel2_*` | 若误入列表，会错误更新掌握度 — 依赖上游过滤 |

### 6.2 掌握度演算

| 场景 | 行为 |
|------|------|
| 已有 `ConceptMastery` 行 | `mastery_level = clamp(old + delta, 0, 100)` |
| 新建 | 初始 `50 + delta` |
| 薄弱判定 | `< weak_threshold`（40）→ `weak_concepts` |
| 章节掌握 | 当前课全部概念平均 ≥ `auto_advance_threshold`（70）→ 自动推进 |

### 6.3 自动推进（双源风险）

| 路径 | 数据源 | 状态 |
|------|--------|------|
| `MasteryTracker._try_auto_advance` | `course.meta.generated_lessons` + `current_lesson_index` | **旧路径**，与新 `LessonPlan`/`CourseProgress` 并行 |
| `TeachingPlanner` | `lesson_plans` + `course_progress` 表 | 教学系统权威，掌握度推进**未完全迁移** |

**改造目标**：自动推进改读 `CourseProgress` + `LessonPlan.concepts`，废弃 `course.meta` 写回。

### 6.4 FSRS 调度

`spaced_repetition.review(card_data, rating_int)` 封装 py-fsrs：

| 信号 | rating | 含义 |
|------|--------|------|
| `concept_mastered` | 3 (Good) | 正常复习间隔 |
| `concept_struggle` | 1 (Again) | 缩短间隔，`reps` 归零 |

`card_data` 为权威状态；`MasteryTracker._schedule_review` 在每次掌握/困难信号时更新。

Scheduler 参数（**硬编码**）：`desired_retention=0.85`, `enable_fuzzing=True`。

---

## 7. 跨世界画像（UserProfile）

### 7.1 增量更新流程

```
update_user_profile_after_chat(user_id, world_id)
  → get_or_create_user_profile
  → 读取 LearnerProfile
  → update_single_world: raw_worlds[world_id] = learner_profile.profile
  → 重算 aggregated (metacognition_trend, preference_stability, learning_stats)
```

```
update_user_profile_after_session_end(user_id, world_id)
  → update_session_count: raw_worlds[world_id].session_count++
  → aggregated.learning_stats.total_sessions++
```

### 7.2 MSKT 元认知趋势

维度：`planning`, `monitoring`, `regulating`, `reflecting`（`MSKT_DIMENSIONS` 硬编码）。

| 条件 | trend 值 |
|------|---------|
| 仅 1 个世界有数据 | `unknown` |
| ≥2 世界，末位值 > 首位值 | `improving` |
| 否则 | `stable` |

值域：`weak` / `moderate` / `strong` → 归一化 1/2/3 比较。

### 7.3 偏好稳定性

特征：`visual_examples`, `analogy_based`, `step_by_step`, `pace`（`PREFERENCE_TRAITS` 硬编码）。

布尔偏好：跨世界一致率 ≥ 70% 标为 `stable`。

---

## 8. 下游消费

### 8.1 教学系统（Prompt 注入）

| 模块 | 读取字段 | 优先级 |
|------|---------|--------|
| `StrategyModule` | `dimension_scores` + DB `strategy_rules` | 25 |
| `PreferenceModule` | `preferences` | 50 |
| `MetacognitionModule` | `metacognition` MSKT | 80 |
| `MisconceptionModule` | `misconceptions` | 30 |
| `EpisodeModule` | `episodes` | 40 |

**注意**：`dimension_scores` 驱动「怎么教」；`UserProfile` **不**进入 PromptBuilder。

### 8.2 叙事 / 成就

| 消费方 | 读取 | 问题 |
|--------|------|------|
| `GamificationEngine` | `dimension_scores`, `learning_stats` | `total_sessions` 缺失 |
| `AchievementDef` `dimension_crossing` | `dimension_scores[key] >= threshold` | 无「跨越事件」，仅当前值 |
| Seed Memory | `learning_stats`, `preference_stability`, `metacognition_trend` | 依赖 UserProfile/LearnerProfile 字段齐全 |

### 8.3 前端

| 路由 | 组件 |
|------|------|
| `GET /api/archive/worlds/{world_id}/learner_profile` | `CoursePage`, `MemoryFactsDrawer`, `Learning.vue` |
| `GET /api/learning/user/profile` | 全局画像展示 |
| `GET /api/textbooks/courses/{id}/mastery` | 课程掌握度概览 |

---

## 9. 接口契约

### 9.1 内部服务 API

#### `ProfileAggregator.aggregate(...) → dict | None`

见 §4.1。返回合并后的 `profile` dict；`None` 表示无 LearnerProfile 或无维度定义。

#### `update_user_profile_after_chat(db, user_id, world_id) → None`

每轮 chat 后调用；commit 在函数内。

#### `update_user_profile_after_session_end(db, user_id, world_id) → None`

会话结束时调用；递增 `session_count`。

#### `get_user_profile(db, user_id) → dict`

返回 `{ user_id, computed_at, metacognition_trend, preference_stability, learning_stats }`。

#### `mastery_tracker.update_from_memories(...) → dict`

```json
{
  "updated_concepts": ["recursion"],
  "auto_advanced": false,
  "new_lesson_index": null
}
```

#### `mastery_tracker.get_course_mastery(db, course_id, user_id) → dict`

```json
{
  "overall_mastery": 72.5,
  "concepts": {"recursion": 85, "loop": 40},
  "weak_concepts": ["loop"],
  "mastered_count": 1,
  "total_tracked": 2
}
```

---

### 9.2 HTTP API

#### `GET /api/archive/worlds/{world_id}/learner_profile`

**响应**（前端直用，无包装）：

```json
{
  "dimension_scores": {
    "abstract_thinking": 0.7,
    "engagement": 0.8
  },
  "strengths": ["abstract_thinking", "engagement"],
  "weaknesses": [],
  "learning_stats": {
    "concepts_mastered": 12,
    "concepts_struggling": 3
  },
  "last_updated": null
}
```

| 错误 | 条件 |
|------|------|
| 404 | 该世界无 LearnerProfile 行 |

#### `POST /api/archive/learner_profile` / `GET` / `PUT`

档案 CRUD；创建时 `profile` 默认为 `{}`。生产主路径多为 `DynamicAnalyzer` 懒创建。

#### `GET /api/learning/user/profile`

跨世界聚合画像；24h 懒刷新。

#### `POST /api/learning/user/profile/refresh`

| Body | 说明 |
|------|------|
| `{ "force": true }` | 清除 `computed_at` 强制重算 |

#### `POST /api/learning/sessions/{session_id}/end`

副作用：`session_count++`，`UserProfile.total_sessions++`（不经 chat 路径的成就仍依赖此接口）。

#### `GET /api/textbooks/courses/{course_id}/mastery`

返回 `CourseMasteryResponse`（`mastery_tracker.get_course_mastery`）。

#### `GET /api/report/mastery-trends` / `GET /api/report/worlds/{world_id}/mastery-trends`

报表服务；**当前仍部分基于 MemoryFact 而非 ConceptMastery**（与掌握度表语义不一致，见 §16）。

---

## 10. 可调参数

### 10.1 L1：`config.py` → `learning_system.profile`

| 键 | 默认 | 影响 |
|----|------|------|
| `hallucination_guard_min_facts` | 3 | 维度最低事实数 |
| `strength_threshold` | 0.7 | strengths 分类 |
| `weakness_threshold` | 0.4 | weaknesses 分类 |

### 10.2 L1：`learning_system.mastery`

| 键 | 默认 | 影响 |
|----|------|------|
| `delta_map.concept_mastered` | +25 | 掌握度增幅 |
| `delta_map.concept_struggle` | -15 | 掌握度降幅 |
| `min` / `max` | 0 / 100 | 钳位 |
| `auto_advance_threshold` | 70 | 章节自动推进 |
| `weak_threshold` | 40 | 薄弱概念 |
| `lesson_started_initial` | 20 | 预留 |

### 10.3 L2：`profile_dimension_defs`

新增维度无需改代码（若 `aggregation_method` 已实现）。未知 method 打 warning 并跳过。

### 10.4 L3：运行时 JSON

`LearnerProfile.profile`、`ConceptMastery` 行、`FSRSState.card_data` 为实例状态。

---

## 11. 与记忆系统的链路

### 11.1 记忆 → 画像（主链路）

```
MemoryFact
  → ProfileAggregator (dimension_scores, learning_stats)
  → MasteryTracker (ConceptMastery)  [仅 concept_* 类型 + tags]
  → UserProfile (经 LearnerProfile 镜像)
```

**耦合强度**：0.85（见总览）。瓶颈：幻觉防护导致冷启动无分数；`learning_stats` 契约不完整。

### 11.2 画像 → 记忆（反向）

Seed Memory 在会话 `start` 时从 `learner_profile` 读取 `learning_stats` / `preference_stability` 等写入 MemoryFact（见 [01 记忆系统 §6.5](01_memory_system.md)）。

---

## 12. 测试覆盖

| 文件 | 覆盖点 |
|------|--------|
| `test_profile_aggregator.py` | ratio, conversion_rate, hallucination guard, merge write, emotion_balance, learning_stats |
| `test_user_profile.py` | MSKT 趋势、偏好稳定性、跨世界 learning_stats |
| `test_mastery_tracker.py` | delta、auto_advance、FSRS、RealDB INSERT |
| `test_fsrs.py` | py-fsrs review 状态机 |
| `test_narrative_gamification.py` | dimension_crossing、stat_threshold（**mock stats，非生产路径**） |

**缺口**：`learning_stats.total_sessions` 生产契约；`LessonPlan` 与 auto_advance 集成；报表与 `ConceptMastery` 一致性。

---

## 13. 已知缺陷与改造路线图

| 优先级 | 项 | 说明 |
|--------|-----|------|
| **P0** | `learning_stats.total_sessions` | 聚合器写入或 chat 路径读 `session_count`；修复画像→成就 |
| **P0** | `gamification` 读源统一 | `process_message` 应用 `LearnerProfile.session_count` 或合并 UserProfile |
| P1 | 自动推进双源 | `MasteryTracker` 迁移至 `CourseProgress` + `LessonPlan` |
| P1 | `misconceptions` / `episodes` 写入器 | 闭环 Prompt 模块，或标注为 v2 |
| P1 | 报表 `report.py` | 掌握度趋势改读 `ConceptMastery` |
| P2 | 聚合 world 策略 | 可配置 per-world / cross-world |
| P2 | Channel-2 排除 | 聚合 SQL 过滤哨兵 tag |
| P2 | FSRS 参数外置 | `desired_retention` 等迁入 config |
| P3 | MSKT / PREFERENCE_TRAITS | 与 `profile_dimension_defs` 统一或 DB 化 |

---

## 14. 硬编码风险清单

| ID | 位置 | 内容 | 建议 |
|----|------|------|------|
| P-H1 | `user_profile.py:25-28` | `MSKT_DIMENSIONS`, `PREFERENCE_TRAITS` | 对齐 dimension_defs 或配置表 |
| P-H2 | `dynamic_analyzer.py:283-286` | 偏好关键词 | 合并至 `extraction.preference_keywords` |
| P-H3 | `metacognition.py:20` | MSKT 四维重复定义 | 单点引用 |
| P-H4 | `spaced_repetition.py:12-15` | FSRS Scheduler 常量 | 迁入 `learning_system.fsrs` |
| P-H5 | `mastery_tracker.py:169` | 新概念初始 50 分 | 可配置 `lesson_started_initial`（已存在于 config 未使用） |
| P-H6 | `report.py` | 趋势用 MemoryFact.salience 代替 mastery_level | 改读 ConceptMastery |

---

## 15. 与总览文档的交叉引用

| 总览链路 | 本系统责任 |
|---------|-----------|
| 记忆 → 画像 | §4 ProfileAggregator，§11.1 |
| 画像 → 教学 | §8.1 StrategyModule 消费 `dimension_scores` |
| 画像 → 成就 | §8.2（`total_sessions` 断裂） |
| 教学 → 学习 | `MasteryTracker` 反驱课程进度 §6.3 |
| 概念掌握跨世界 | §3.6 `concept_mastery` UNIQUE(user, concept) |

---

*文档基于 `profile_aggregator.py`、`user_profile.py`、`mastery_tracker.py`、`spaced_repetition.py`、`dynamic_analyzer.py`、相关模型与 API 路由及测试文件代码勘探生成，2026-06-20。*
