# 四大系统闭环架构设计 — 总览

> **版本**：v1.0.4  
> **日期**：2026-06-20  
> **状态**：设计中（四子系统文档已齐；**18 处断裂登记** B01–B18，v1.0.5 门禁 P0×5）  
> **详细设计**：[01 记忆系统](01_memory_system.md) | [02 学习画像](02_learner_profile.md) | [03 教学系统](03_teaching_system.md) | [04 叙事系统](04_narrative_system.md)

### 代码锚点引用规范

本文档中凡描述**已实现功能**的条目，均附可点击的源码锚点，便于 IDE / GitHub 一键跳转核实。

| 写法 | 示例 | 说明 |
|------|------|------|
| `[文件:行](../../path#L行)` | [`learning_engine.py:161`](../../backend/services/learning_engine.py#L161) | 单行 |
| `[文件:起-止](../../path#L起-L止)` | [`context:148-163`](../../backend/services/learning_engine.py#L148-L163) | 行范围 |
| 表内「源码」列 | 同上 | 断裂登记册、代码盘点等表格统一放此列 |

路径均相对于 `docs/v1.0.4/`；前端源码前缀 `../../frontend/src/`。

---

## 核心原则：数据驱动，不硬编码

### 设计思路

四大系统（记忆 / 学习画像 / 教学 / 叙事）之间的耦合，应通过**可查询、可版本化、可运营配置**的数据载体传递，而非在 Python 业务逻辑或 Prompt 模板中写死规则。具体落地为三层参数体系（见第 8 章）：

| 层级 | 载体 | 职责 |
|------|------|------|
| L1 | `config.py` → `learning_system` | 算法常量、衰减系数、阈值边界（改代码部署） |
| L2 | DB 规则表 | 业务语义规则（维度定义、教学策略、叙事触发、成就条件） |
| L3 | DB 运行时 JSON | 每用户/每世界/每会话的实例状态 |

**观察者模式**是闭环的架构约束：叙事系统**只读** MemoryFact / LearnerProfile / Relationship，不调用 LLM（[`narrative_engine.py:42`](../../backend/services/narrative_engine.py#L42)、[`gamification.py:24`](../../backend/services/gamification.py#L24)）；画像聚合器**只读** MemoryFact，零 API 成本（[`profile_aggregator.py:31`](../../backend/services/profile_aggregator.py#L31)）。教学引擎是唯一 LLM 调用入口（[`learning_engine.py:85`](../../backend/services/learning_engine.py#L85)），负责写入记忆并触发下游观察者。

### 落地约束

1. **新增教学策略** → 向 `strategy_rules` 插入一行，关联已有 `profile_dimension_defs.key`，禁止在 `StrategyModule` 内写 `if dimension == "xxx"`（策略读取：[`strategy.py:40-58`](../../backend/services/prompt_builder/modules/strategy.py#L40-L58)）。
2. **新增画像维度** → 向 `profile_dimension_defs` 插入一行并指定 `aggregation_method`，禁止在 `ProfileAggregator` 内硬编码维度名（聚合入口：[`profile_aggregator.py:31-74`](../../backend/services/profile_aggregator.py#L31-L74)）。
3. **新增叙事事件 / 成就** → 向 `narrative_trigger_rules` / `achievement_defs` 插入一行；若需新 `condition_type`，须同步扩展引擎 `_check_condition`，禁止静默失效（叙事：[`narrative_engine.py:145`](../../backend/services/narrative_engine.py#L145)；成就：[`gamification.py:130`](../../backend/services/gamification.py#L130)）。
4. **记忆类型扩展** → 同步更新 `config.py` 中 `salience_type_multiplier` 与 `mastery.delta_map`（[`config.py:85-107`](../../backend/core/config.py#L85-L107)），否则新类型不参与衰减与掌握度演算。
5. **跨世界语义** → `ConceptMastery` / `FSRSState` 以 `(user_id, concept_id)` 为键（[`models.py:319`](../../backend/models/models.py#L319)）；`MemoryFact` 检索按 `world_id` 过滤（[`memory_manager.py`](../../backend/services/memory_manager.py) retrieve 段）；画像聚合按 `(character_id)` 跨世界（[`profile_aggregator.py:128`](../../backend/services/profile_aggregator.py#L128) TR-C1 注释）——三者边界不可混用。

### 当前硬编码风险点（须标注跟踪）

| 位置 | 源码 | 硬编码内容 | 风险等级 | 改造方向 |
|------|------|-----------|---------|---------|
| `learning_engine.py` | [`:161`](../../backend/services/learning_engine.py#L161) | `mastery_level: 50` 固定值 | **高** | 从 `ConceptMastery` / `FSRSState` 计算当前课概念均值 |
| `learning_engine.py` | [`:148-163`](../../backend/services/learning_engine.py#L148-L163) | context 未注入 `current_topic` | **高** | 从 [`teaching_planner.py:99`](../../backend/services/teaching_planner.py#L99) `get_current_lesson()` 写入 context |
| 前后端契约 | 后端 [`:105-110`](../../backend/services/narrative_engine.py#L105-L110)、[`gamification.py:118-126`](../../backend/services/gamification.py#L118-L126)；前端 [`learning.ts:56-57`](../../frontend/src/app/stores/learning.ts#L56-L57)、[`Learning.vue:161`](../../frontend/src/courses/views/Learning.vue#L161) | `text`/`display_name` vs `description`/`name` | **高** | 字段对齐或 store 层适配 |
| `prompt_builder/builder.py` | [`:46-61`](../../backend/services/prompt_builder/builder.py#L46-L61) | `CourseIntentModule` 未列入 `MODULE_CONFIGS` | 中 | 模块定义见 [`course_intent.py:42`](../../backend/services/prompt_builder/modules/course_intent.py#L42) |
| `mastery_tracker.py` | [`:120-129`](../../backend/services/mastery_tracker.py#L120-L129)、[`teaching_planner.py:227-236`](../../backend/services/teaching_planner.py#L227-L236) | 自动推进写 `course.meta` 与 `CourseProgress` 双源 | 中 | 统一由 `TeachingPlanner` 写 `course_progress` 表 |
| `relationship.py` | [`:22-31`](../../backend/services/relationship.py#L22-L31) | 情感→关系维度 delta 表 | 中 | 迁入 `relationship_dimension_rules` 规则表 |
| `relationship.py` | [`:64-72`](../../backend/services/relationship.py#L64-L72) | 阶段阈值 0.20/0.45/0.65/0.85 | 中 | 迁入 DB 或 `config.py` 可配置段 |
| `dynamic_analyzer.py` | [`:17-26`](../../backend/services/dynamic_analyzer.py#L17-L26) | `EDUCATION_EMOTIONS` 8 类情感 taxonomy | 中 | 迁入 DB 情感定义表或 L1 配置 |
| `prompt_builder/builder.py` | [`:46-68`](../../backend/services/prompt_builder/builder.py#L46-L68) | `SceneConfig.MODULE_CONFIGS` 模块编排 | 中 | 短期可接受；长期可场景化配置表 |
| `learning.py` | [`:71-77`](../../backend/api/routes/learning.py#L71-L77) | `_GREETING_FALLBACKS` 五阶段问候语 | 低 | 优先读 `Character.greeting` / `WorldCharacter.world_greeting` |
| `user_profile.py` | [`:25-28`](../../backend/services/user_profile.py#L25-L28) | `MSKT_DIMENSIONS` / `PREFERENCE_TRAITS` | 低 | 与 `profile_dimension_defs` 对齐 |
| 设计文档 / CLAUDE.md | — | ChromaDB 向量记忆 | **架构债** | 当前仅 `MemoryFact` SQL 检索（[`memory_manager.py:45`](../../backend/services/memory_manager.py#L45)），无向量层 |

---

## 闭环总览

### 整体数据流（编排步骤 ↔ 源码）

| 步骤 | 功能 | 源码锚点 |
|------|------|---------|
| 入口 | HTTP chat | [`learning.py:543`](../../backend/api/routes/learning.py#L543) `send_message` → [`:576`](../../backend/api/routes/learning.py#L576) `process_message` |
| ① | PromptBuilder 组装 system_prompt | [`learning_engine.py:139-171`](../../backend/services/learning_engine.py#L139-L171) → [`builder.py`](../../backend/services/prompt_builder/builder.py) `build()` |
| ② | MemoryManager 工作记忆 | [`learning_engine.py:173-174`](../../backend/services/learning_engine.py#L173-L174) → [`memory_manager.py:45`](../../backend/services/memory_manager.py#L45) |
| ③ | LLM Adapter 生成回复 | [`learning_engine.py:179-192`](../../backend/services/learning_engine.py#L179-L192) |
| ④ | DynamicAnalyzer 情感 → affect | [`learning_engine.py:205-212`](../../backend/services/learning_engine.py#L205-L212) → [`dynamic_analyzer.py`](../../backend/services/dynamic_analyzer.py) |
| ⑤ | RelationshipService 更新 relationship | [`learning_engine.py:214-232`](../../backend/services/learning_engine.py#L214-L232) → [`relationship.py:11`](../../backend/services/relationship.py#L11) |
| ⑥ | extract_and_store → MemoryFact | [`learning_engine.py:234-244`](../../backend/services/learning_engine.py#L234-L244) → [`memory_manager.py:255`](../../backend/services/memory_manager.py#L255) |
| ⑦ | ProfileAggregator → dimension_scores | [`learning_engine.py:258-264`](../../backend/services/learning_engine.py#L258-L264) → [`profile_aggregator.py:31`](../../backend/services/profile_aggregator.py#L31) |
| ⑧ | UserProfile 跨世界聚合（不注入 Prompt） | [`learning_engine.py:266-268`](../../backend/services/learning_engine.py#L266-L268) → [`user_profile.py`](../../backend/services/user_profile.py) |
| ⑨ | MasteryTracker → ConceptMastery + 推进 | [`learning_engine.py:276-290`](../../backend/services/learning_engine.py#L276-L290) → [`mastery_tracker.py`](../../backend/services/mastery_tracker.py) |
| ⑩ | NarrativeEngine 叙事事件 | [`learning_engine.py:292-301`](../../backend/services/learning_engine.py#L292-L301) → [`narrative_engine.py:42`](../../backend/services/narrative_engine.py#L42) |
| ⑪ | GamificationEngine 成就解锁 | [`learning_engine.py:303-323`](../../backend/services/learning_engine.py#L303-L323) → [`gamification.py:24`](../../backend/services/gamification.py#L24) |
| 返回 | 前端消费 reply / events | [`learning_engine.py:331-342`](../../backend/services/learning_engine.py#L331-L342) → [`learning.ts:293-299`](../../frontend/src/app/stores/learning.ts#L293-L299) |

```
用户发言 → LearningEngine.process_message（见上表）→ 前端 Learning Store
```

### 四大系统流转逻辑

| 阶段 | 系统 | 输入 | 输出 | 触发时机 | 源码 |
|------|------|------|------|---------|------|
| 感知 | 记忆系统 | 用户消息 + LLM 回复 | `MemoryFact` 行 | 每轮对话后 | [`memory_manager.py:255`](../../backend/services/memory_manager.py#L255) |
| 建模 | 学习画像 | `MemoryFact` + `affect` | `dimension_scores` / strengths / weaknesses | 每轮（零 LLM） | [`profile_aggregator.py:31`](../../backend/services/profile_aggregator.py#L31) |
| 决策 | 教学系统 | 画像 + 记忆 + 课程 + 策略 | `system_prompt` | 每轮对话前 | [`builder.py:46-61`](../../backend/services/prompt_builder/builder.py#L46-L61) |
| 反馈 | 叙事系统 | MemoryFact + 关系 + 画像统计 | UI 事件 + 成就 | 每轮对话后 | [`narrative_engine.py:42`](../../backend/services/narrative_engine.py#L42)、[`gamification.py:24`](../../backend/services/gamification.py#L24) |

### 整体架构闭环逻辑图（文字描述）

```
                    ┌──────────────┐
                    │  用户 / 前端  │
                    └──────┬───────┘
                           │ HTTP POST /api/learning/.../chat
                           ▼
              ┌────────────────────────┐
              │     教学系统 (Hub)      │
              │  LearningEngine         │
              │  PromptBuilder (13模块) │
              │  TeachingPlanner        │
              │  CourseGenerator        │
              └─┬──────┬──────┬────┬───┘
                │读    │读    │写  │读
                ▼      ▼      ▼    ▼
         ┌──────────┐ ┌────────┐ ┌─────────────┐
         │记忆系统   │ │学习画像 │ │叙事系统      │
         │MemoryFact│ │Learner │ │NarrativeRule │
         │chat_msgs │ │Profile │ │Achievement  │
         └────▲─────┘ └───▲────┘ └──────▲──────┘
              │           │              │
              │    聚合    │    观察       │
              └───────────┴──────────────┘
                    闭环反馈弧
```

**闭环要义**：教学产出（对话）经记忆提取沉淀为事实；事实经聚合器变为可度量画像；画像经策略规则改变教学方式；教学过程中的概念信号反向更新掌握度与 FSRS，并触发叙事/成就反馈，部分叙事事件再写回记忆，形成二次闭环。

---

## 现有代码盘点

> 行数为 2026-06-20 仓库实测（`wc -l` 等价）；稳定性基于测试覆盖、生产路径验证、已知 TODO 综合评定。  
> 评级：**A** 稳定可依赖 · **B** 主路径可用有缺口 · **C** 部分实现/有断裂 · **D** 设计占位

| 系统 | 现有文件 | 行数 | 稳定性 | 本次改造目标 |
|------|---------|------|--------|-------------|
| **记忆系统** | [`memory_manager.py`](../../backend/services/memory_manager.py) | 449 | **A** | 保持单一入口；评估 ChromaDB 向量层是否纳入 v1.0.5 |
| | [`memory_facts.py`](../../backend/services/memory_facts.py) | 254 | A | 补齐 `t_invalid` 纠正链路的产品化 API |
| | [`memory_extractor.py`](../../backend/services/memory_extractor.py) | 235 | A | Channel-1 `<memory>` 标签契约文档化 |
| | [`recall_service.py`](../../backend/services/recall_service.py) | 124 | **C** | **接通 `current_topic` 注入**，解除 RecallContext 空转 |
| | [`modules/memory_facts.py`](../../backend/services/prompt_builder/modules/memory_facts.py) | 83 | A | 与 `retrieve()` salience 衰减联调验证 |
| | [`modules/recall_context.py`](../../backend/services/prompt_builder/modules/recall_context.py) | 58 | C | 依赖 recall_service 接线后升为 B |
| | [`modules/episode.py`](../../backend/services/prompt_builder/modules/episode.py) | 91 | B | 情景记忆模块，覆盖待补测试 |
| | [`archive.py`](../../backend/api/routes/archive.py)（记忆段） | ~400† | B | 存档恢复 MemoryFact ID 联调 |
| | [`save.py`](../../backend/api/routes/save.py) | 729 | B | 文件存档与 DB 快照一致性 |
| | 测试：`test_memory_manager.py` 等 3 文件 | ~25 cases | — | 补充 recall 集成测试 |
| | **小计** | **~1,294 服务 + 729 API** | **B+** | 打通概念关联；向量检索选型 |
| **学习画像** | [`profile_aggregator.py`](../../backend/services/profile_aggregator.py) | 282 | **B** | **`learning_stats` 补齐 `total_sessions`**，修复成就链路 |
| | [`user_profile.py`](../../backend/services/user_profile.py) | 470 | B | 跨世界聚合与 `dimension_scores` 字段对齐 |
| | [`mastery_tracker.py`](../../backend/services/mastery_tracker.py) | 361 | **A** | `ConceptMastery` 与 `ProgressTracking` 双写收敛 |
| | [`spaced_repetition.py`](../../backend/services/spaced_repetition.py) | 93 | A | FSRS `card_data` 权威源统一 |
| | [`models.py`](../../backend/models/models.py)（画像表） | ~120 | A | — |
| | [`report.py`](../../backend/api/routes/report.py) | 188 | B | 报表与实时画像一致性 |
| | 测试：`test_profile_aggregator.py` 等 4 文件 | ~62 cases | — | 增加 learning_stats 契约测试 |
| | **小计** | **~1,206 服务** | **B** | 画像→成就数据契约修复 |
| **教学系统** | [`learning_engine.py`](../../backend/services/learning_engine.py) | 375 | **B** | 去除 `mastery_level` 硬编码；注入 `current_topic` |
| | [`builder.py`](../../backend/services/prompt_builder/builder.py) | 387 | A | 模块编排可配置化（低优先级） |
| | [`prompt_builder/modules/`](../../backend/services/prompt_builder/modules/) | 675 | B | Strategy/CourseContent 与 DB 规则对齐 |
| | [`teaching_planner.py`](../../backend/services/teaching_planner.py) | 330 | A | `LessonPlan` 迁移收尾，废弃 `course.meta` 回退 |
| | [`course_generator.py`](../../backend/services/course_generator.py) | 243 | B | 教材→课程→`concept_map` 生成稳定性 |
| | [`dynamic_analyzer.py`](../../backend/services/dynamic_analyzer.py) | 301 | B | 情感 taxonomy 外置；LLM/关键词双通道已就绪 |
| | [`relationship.py`](../../backend/services/relationship.py) | 106 | B | 关系 delta / 阶段阈值数据化 |
| | [`llm/`](../../backend/services/llm/) | ~800 | A | 多 Provider 韧性已落地 |
| | [`learning.py`](../../backend/api/routes/learning.py) | 810 | A | Chat 契约含 narrative/achievement 字段 |
| | [`textbook.py`](../../backend/api/routes/textbook.py) + [`bookshelf.py`](../../backend/api/routes/bookshelf.py) | 1,332 | B | 书架→课程解耦流程稳定化 |
| | 测试：teaching 相关 ~10 文件 | ~150 cases | — | E2E 概念关联场景 |
| | **小计** | **~2,417 服务 + 2,479 API** | **B+** | 闭环编排补全两处断裂点 |
| **叙事系统** | [`narrative_engine.py`](../../backend/services/narrative_engine.py) | 234 | **B** | 实现 `time_gap`；冷却持久化（内存→DB） |
| | [`gamification.py`](../../backend/services/gamification.py) | 238 | B | 修复 `total_sessions` 统计源；`consecutive_days` 实现或下线种子 |
| | [`modules/narrative.py`](../../backend/services/prompt_builder/modules/narrative.py) | 96 | B | `course_narrative_plan` 契约与 v1.0.4 世界壳对齐 |
| | [`modules/world_setting.py`](../../backend/services/prompt_builder/modules/world_setting.py) | 56 | B | `World.description` 正式契约 |
| | [`achievements.py`](../../backend/api/routes/achievements.py) | 45 | B | 成就列表 API 与引擎状态同步 |
| | 测试：`test_narrative_gamification.py` | ~18 cases | — | 补生产路径 stat_threshold 集成测试 |
| | **小计** | **~624 服务 + 855 API** | **B-** | 修复画像→成就；叙事冷却持久化 |

† archive.py 行数含档案全功能，记忆相关为估算子集。

---

## 各系统摘要

### 系统一：记忆系统

**详细设计**：[01_memory_system.md](01_memory_system.md)

**定位**：学习对话的**长期事实存储与检索层**，替代早期 ChromaDB/Knowledge 方案，以 `MemoryFact` 关系表为权威源。

**核心能力**：
- **双通道提取**：Channel-1 [`memory_extractor.py:44-52`](../../backend/services/memory_extractor.py#L44-L52)；Channel-2 [`memory_manager.py:291-371`](../../backend/services/memory_manager.py#L291-L371)
- **检索**：[`memory_manager.py:94-147`](../../backend/services/memory_manager.py#L94-L147) `retrieve()`；衰减 [`:377`](../../backend/services/memory_manager.py#L377)
- **工作记忆**：[`memory_manager.py:45`](../../backend/services/memory_manager.py#L45)；上限 [`config.py:62-63`](../../backend/core/config.py#L62-L63)
- **去重**：[`memory_manager.py:205-243`](../../backend/services/memory_manager.py#L205-L243)；窗口 [`config.py:61`](../../backend/core/config.py#L61)
- **Seed Memory**：[`learning.py:514-523`](../../backend/api/routes/learning.py#L514-L523) → [`memory_facts.py:90`](../../backend/services/memory_facts.py#L90)

**当前实现进度**：**~85%**  
已落地 `MemoryManager` 统一入口、6 类 `fact_type`、Prompt 注入模块、存档联调。  
**关联断裂**：**B01/B11**（概念关联未接线/边类型）、**B09**（溯源 ID）、**B15**（Channel-2 分母）、**B18**（重复 Seed）。未落地：ChromaDB 向量语义检索、`t_invalid` 纠正 UI、定时 `cleanup_expired` 运维调度。

---

### 系统二：学习画像

**详细设计**：[02_learner_profile.md](02_learner_profile.md)

**定位**：将离散记忆事实**聚合为可度量、可驱动教学策略**的学习者模型；分**世界内**（`LearnerProfile`）与**跨世界展示**（`UserProfile`）两层。

**核心能力**：
- **维度聚合引擎**：[`profile_aggregator.py:31-74`](../../backend/services/profile_aggregator.py#L31-L74)；五种方法 [`:97-257`](../../backend/services/profile_aggregator.py#L97-L257)；种子 [`2026_04_25_add_profile_dimension_defs.py`](../../backend/alembic/versions/2026_04_25_add_profile_dimension_defs.py)
- **幻觉防护**：[`profile_aggregator.py:108`](../../backend/services/profile_aggregator.py#L108)；阈值 [`config.py:70`](../../backend/core/config.py#L70)
- **掌握度追踪**：[`mastery_tracker.py:56`](../../backend/services/mastery_tracker.py#L56)；delta [`config.py:95-97`](../../backend/core/config.py#L95-L97)
- **情感轨迹**：[`dynamic_analyzer.py`](../../backend/services/dynamic_analyzer.py) `update_learner_profile`；编排 [`learning_engine.py:246-256`](../../backend/services/learning_engine.py#L246-L256)

**当前实现进度**：**~75%**  
维度聚合与掌握度闭环已通。  
**关联断裂**：**B02**（`total_sessions` 缺失 → 成就不解锁）、**B03**（脚手架掌握度硬编码）、**B05**（成就展示字段）、**B13/B16/B17**（成就条件语义）。缺口：`UserProfile` 与 `dimension_scores` 字段命名未完全统一。

---

### 系统三：教学系统

**详细设计**：[03_teaching_system.md](03_teaching_system.md)

**定位**：**唯一 LLM 调用编排中枢**，将教师人格、课程结构、学习者画像、记忆上下文组装为动态 system prompt，执行苏格拉底式教学。

**核心能力**：
- **模块化 PromptBuilder**：[`builder.py:46-61`](../../backend/services/prompt_builder/builder.py#L46-L61) `MODULE_CONFIGS[LEARNING]`
- **课程感知**：[`course_content.py`](../../backend/services/prompt_builder/modules/course_content.py)；进度 [`teaching_planner.py:64-99`](../../backend/services/teaching_planner.py#L64-L99)
- **策略驱动**：[`strategy.py:40-58`](../../backend/services/prompt_builder/modules/strategy.py#L40-L58)
- **进度管理**：[`teaching_planner.py:227-236`](../../backend/services/teaching_planner.py#L227-L236)；阈值 [`config.py:105`](../../backend/core/config.py#L105)
- **课程生成**：[`course_generator.py`](../../backend/services/course_generator.py)；concept_map [`:52-57`](../../backend/services/course_generator.py#L52-L57)

**当前实现进度**：**~80%**  
主路径 `process_message` 20 步编排已完整。  
**关联断裂**：**B01/B03/B06/B10/B11/B12**（概念未注入、掌握度硬编码、tool 短路、课程意图未接线、concept_map 边类型、误解/情景无写入器）。部分问候语/表情映射仍硬编码。

---

### 系统四：叙事系统

**详细设计**：[04_narrative_system.md](04_narrative_system.md)

**定位**：**零 LLM 成本的沉浸式反馈层**，观察学习与关系信号，触发叙事 toast/modal 与成就解锁，可选写回 `event` 类记忆。

**核心能力**：
- **叙事触发引擎**：[`narrative_engine.py:176-215`](../../backend/services/narrative_engine.py#L176-L215)；种子 [`2026_04_25_add_narrative_and_achievements.py:20`](../../backend/alembic/versions/2026_04_25_add_narrative_and_achievements.py#L20)
- **成就引擎**：[`gamification.py:142-177`](../../backend/services/gamification.py#L142-L177)；种子 [`2026_04_25_add_narrative_and_achievements.py:75`](../../backend/alembic/versions/2026_04_25_add_narrative_and_achievements.py#L75)
- **Prompt 叙事注入**：[`narrative.py`](../../backend/services/prompt_builder/modules/narrative.py)
- **世界氛围**：[`world_setting.py`](../../backend/services/prompt_builder/modules/world_setting.py)
- **前端消费**：[`learning.ts:293-299`](../../frontend/src/app/stores/learning.ts#L293-L299)；展示 [`Learning.vue:161-171`](../../frontend/src/courses/views/Learning.vue#L161-L171)

**当前实现进度**：**~65%**  
引擎框架与前端消费已通。  
**关联断裂**：**B04/B05**（前后端字段 → toast 空白，**P0**）、**B08**（`time_gap` / `requires_prior_struggle` 未实现）、**B02/B13**（成就统计源）、**B14**（冷却仅存内存）、**B16/B17**（成就条件语义偏差）。

---

## 数据库表汇总

| 表名 | 所属系统 | 模型定义 | 用途 |
|------|---------|---------|------|
| `memory_facts` | 记忆 | [`models.py:108`](../../backend/models/models.py#L108) | 认知事实；6 类 fact_type；salience / 溯源 |
| `chat_messages` | 记忆 | [`models.py`](../../backend/models/models.py) ChatMessage | 工作记忆；`used_memory_ids` [`:431`](../../backend/models/models.py#L431) |
| `learner_profiles` | 学习画像 | [`models.py:215`](../../backend/models/models.py#L215) | dimension_scores / affect / preferences |
| `user_profiles` | 学习画像 | UserProfile 类 | 跨世界展示缓存（不注入 Prompt） |
| `profile_dimension_defs` | 学习画像 | [`models.py:462`](../../backend/models/models.py#L462) | L2 画像维度 + 聚合方法 |
| `concept_mastery` | 学习画像 | [`models.py:319`](../../backend/models/models.py#L319) | 跨世界 `(user_id, concept_id)` |
| `fsrs_states` | 学习画像 | FSRSState 类 | FSRS；`card_data` 权威载荷 |
| `progress_trackings` | 画像/教学 | ProgressTracking | 课程级 topic 进度 |
| `strategy_rules` | 教学 | [`models.py:448`](../../backend/models/models.py#L448) | 维度→教学指令三档 |
| `courses` | 教学 | Course | `meta` 存 concept_map / narrative_plan |
| `lesson_plans` | 教学 | LessonPlan | 章节 DAG |
| `course_progress` | 教学 | CourseProgress | current_lesson_index |
| `textbooks` / `textbook_library` | 教学 | Textbook 等 | 教材 extracted_text |
| `learning_plan_drafts` | 教学 | LearningPlanDraft | v1.0.4 非主路径 |
| `sessions` | 教学/叙事 | Session | relationship JSON |
| `characters` / `world_characters` | 教学/叙事 | Character 等 | traits / greeting |
| `worlds` | 叙事 | World | description / background_picture |
| `narrative_trigger_rules` | 叙事 | [`models.py:478`](../../backend/models/models.py#L478) | L2 叙事触发 |
| `achievement_defs` | 叙事 | [`models.py:500`](../../backend/models/models.py#L500) | L2 成就定义 |
| `achievements` | 叙事 | Achievement | 解锁记录 |
| `relationship_stages` | 叙事 | RelationshipStageRecord | 阶段审计 |
| `checkpoints` | 记忆/教学 | Checkpoint | 存档 state JSON |
| `users` | 基础设施 | User | 认证 + LLM 配置 |

---

## 闭环强度评估

### 链路逐条拆解

#### 1. 记忆 → 画像

| 维度 | 评估 |
|------|------|
| **耦合强度** | **强（0.85）** — [`learning_engine.py:258-264`](../../backend/services/learning_engine.py#L258-L264) 调用 [`profile_aggregator.py:31`](../../backend/services/profile_aggregator.py#L31) |
| **数据路径** | `MemoryFact` → `profile_dimension_defs` 规则 → `LearnerProfile.profile.dimension_scores / strengths / weaknesses / learning_stats` |
| **现存缺陷** | ① [`profile_aggregator.py:275-278`](../../backend/services/profile_aggregator.py#L275-L278) 缺 `total_sessions`（**B02**）；② affect 写入 [`learning_engine.py:246-256`](../../backend/services/learning_engine.py#L246-L256) 与聚合同轮；③ 跨世界注释 [`profile_aggregator.py:128`](../../backend/services/profile_aggregator.py#L128) vs 检索 [`memory_manager.py:125-128`](../../backend/services/memory_manager.py#L125-L128) |
| **优化方案** | 在 `_compute_learning_stats` 增加 `Session` COUNT；或从 `UserProfile` 增量字段回写；统一跨世界策略并在 `02_learner_profile.md` 定稿 |

#### 2. 画像 → 教学

| 维度 | 评估 |
|------|------|
| **耦合强度** | **中强（0.75）** — [`strategy.py:40-58`](../../backend/services/prompt_builder/modules/strategy.py#L40-L58)；[`preference.py`](../../backend/services/prompt_builder/modules/preference.py)、[`metacognition.py`](../../backend/services/prompt_builder/modules/metacognition.py) |
| **数据路径** | `LearnerProfile.profile.dimension_scores` → `strategy_rules` → Prompt「教学策略」段 |
| **现存缺陷** | ① 幻觉防护 [`profile_aggregator.py:108`](../../backend/services/profile_aggregator.py#L108)；② mid 种子 NULL 见 migration [`2026_04_25_add_strategy_rules.py`](../../backend/alembic/versions/2026_04_25_add_strategy_rules.py)；③ **B03** [`learning_engine.py:161`](../../backend/services/learning_engine.py#L161) |
| **优化方案** | 新用户降级策略：不足 min_facts 时使用 `strategy_rules` 默认档；`learning_engine` context 接入 `MasteryTracker` 实时值 |

#### 3. 教学 → 学习

| 维度 | 评估 |
|------|------|
| **耦合强度** | **强（0.80）** — [`learning_engine.py:179-232`](../../backend/services/learning_engine.py#L179-L232) → [`Learning.vue`](../../frontend/src/courses/views/Learning.vue) |
| **数据路径** | `PromptBuilder.build()` → LLM → `ChatResponse` → 前端 `learning.ts` |
| **现存缺陷** | ① `<tool>` 提前 return，步骤 11–19 全跳过（**断裂 B06**）；② 前端叙事/成就字段契约不一致，事件到达 UI 但**正文为空**（**断裂 B04/B05**）；③ `CourseIntentModule` 未接线（**断裂 B10**） |
| **优化方案** | 工具路径补观察者；`learning.ts` 增加字段适配；`CourseIntentModule` 加入 `MODULE_CONFIGS`；见 §闭环断裂点总览 |

#### 4. 学习 → 记忆

| 维度 | 评估 |
|------|------|
| **耦合强度** | **强（0.90）** — [`learning_engine.py:236`](../../backend/services/learning_engine.py#L236) → [`memory_manager.py:255`](../../backend/services/memory_manager.py#L255) |
| **数据路径** | 用户消息 + LLM 回复 → Channel-1/2 → `memory_facts` 表 |
| **现存缺陷** | ① Channel-2 [`memory_manager.py:320-364`](../../backend/services/memory_manager.py#L320-L364)；掌握度排除 [`learning_engine.py:277-283`](../../backend/services/learning_engine.py#L277-L283)；② **B09** [`:244`](../../backend/services/learning_engine.py#L244) |
| **优化方案** | 检索时过滤哨兵标签；修正 `used_memory_ids` 为 `MemoryManager.write_facts` 返回值 |

#### 5. 记忆 → 叙事

| 维度 | 评估 |
|------|------|
| **耦合强度** | **中（0.70）** — [`learning_engine.py:292-301`](../../backend/services/learning_engine.py#L292-L301)；条件 [`narrative_engine.py:176-215`](../../backend/services/narrative_engine.py#L176-L215) |
| **数据路径** | 本轮 `MemoryFact` + `Session.relationship.stage` → `narrative_trigger_rules` → `narrative_events[]` → 前端 toast/modal |
| **现存缺陷** | ① `time_gap` / `breakthrough.requires_prior_struggle` 未实现（**B08**，种子规则静默失效）；② 冷却内存字典（**B14**）；③ 即使引擎触发，前端因 **B04** 可能不展示 `text` |
| **优化方案** | 实现条件分支或下线种子；冷却持久化；前后端字段对齐 |

#### 6. 画像 → 成就

| 维度 | 评估 |
|------|------|
| **耦合强度** | **弱（0.55）** — [`gamification.py:24`](../../backend/services/gamification.py#L24) 已接线；**B02/B05** 数据契约断裂 |
| **数据路径** | `LearnerProfile.profile` → `learning_stats` + `dimension_scores` → `gamification_engine.check_achievements()` |
| **现存缺陷** | ① **`learning_stats` 无 `total_sessions`**（**B02**），`first_step`/`regular_visitor` chat 路径永不触发；② `late_night_session` 无写入器（**B13**），`night_owl` 永不可达；③ `dimension_crossing` 非跨越事件（**B16**）；④ 前端 **B05** 导致已解锁成就标题为空 |
| **优化方案** | 聚合器写入 `total_sessions` 或 chat 路径合并 `session_count`；实现/下线无效种子；成就响应字段适配 |

#### 7. 概念关联

| 维度 | 评估 |
|------|------|
| **耦合强度** | **弱（0.40）** — [`recall_service.py`](../../backend/services/recall_service.py)、[`recall_context.py`](../../backend/services/prompt_builder/modules/recall_context.py)；**B01** 未注入 `current_topic` |
| **数据路径** | `Course.meta.concept_map` DAG + `MemoryFact.concept_tags` → 前置复习提示 → Prompt「记忆召回上下文」 |
| **现存缺陷** | ① **`current_topic` 未注入**（**B01**），`RecallContextModule` 生产等效禁用；② `concept_map` 边类型 `prerequisite` vs `requires` 不一致（**B11**）；③ 无 `concept_map` 时链路自然为空（非 bug） |
| **优化方案** | `TeachingPlanner.get_current_lesson()` → `concepts[0]` 写入 context；`RecallService` 兼容两种 relation；E2E 测试 |

---

## 闭环断裂点总览（四子系统回写）

> 本节为 v1.0.4 勘探结论的**单一事实源**：凡影响闭环的代码/契约/数据断裂均登记于此。  
> 子文档细节见 [01](01_memory_system.md)–[04](04_narrative_system.md)；修复优先级以本节为准。

### 断裂点登记册

| ID | 断裂点 | 级别 | 影响链路 | 根因（源码） | 用户可见症状 | 修复动作 |
|----|--------|------|---------|-------------|-------------|---------|
| **B01** | `current_topic` 未注入主编排 | **P0** | 概念关联 | [`learning_engine.py:148-163`](../../backend/services/learning_engine.py#L148-L163) 缺字段；消费 [`recall_context.py:47`](../../backend/services/prompt_builder/modules/recall_context.py#L47) | 前置概念复习提示永不出现 | [`teaching_planner.py:99`](../../backend/services/teaching_planner.py#L99) → `context["current_topic"]` |
| **B02** | `learning_stats.total_sessions` 缺失 | **P0** | 画像→成就 | [`profile_aggregator.py:275-278`](../../backend/services/profile_aggregator.py#L275-L278)；成就读 [`gamification.py:142-147`](../../backend/services/gamification.py#L142-L147)；种子 [`migration:82`](../../backend/alembic/versions/2026_04_25_add_narrative_and_achievements.py#L82) | 里程碑成就不解锁 | 聚合器写入或合并 `session_count` |
| **B03** | `mastery_level` 硬编码 50 | **P0** | 画像→教学 | [`learning_engine.py:161`](../../backend/services/learning_engine.py#L161)；脚手架 [`builder.py:356`](../../backend/services/prompt_builder/builder.py#L356) | 脚手架与掌握度脱节 | 读 `ConceptMastery` 均值 |
| **B04** | 叙事事件前后端字段不一致 | **P0** | 教学→学习 / 记忆→叙事 | 后端 [`narrative_engine.py:105-110`](../../backend/services/narrative_engine.py#L105-L110) `text`；前端 [`learning.ts:56`](../../frontend/src/app/stores/learning.ts#L56) `description` | 叙事 toast 正文空白 | store 适配或统一 API |
| **B05** | 成就前后端字段不一致 | **P0** | 画像→成就 / 教学→学习 | 后端 [`gamification.py:118-126`](../../backend/services/gamification.py#L118-L126) `display_name`；前端 [`learning.ts:57`](../../frontend/src/app/stores/learning.ts#L57) `name` | 成就 toast 标题空白 | 同上 |
| **B06** | `<tool>` 响应提前 return | P1 | 学习→记忆等 | [`learning_engine.py:194-203`](../../backend/services/learning_engine.py#L194-L203) | 工具轮次无观察者更新 | 补轻量观察者或延后 return |
| **B07** | 章节自动推进双源 | P1 | 教学内部 | [`mastery_tracker.py:120-129`](../../backend/services/mastery_tracker.py#L120-L129) vs [`teaching_planner.py:227-236`](../../backend/services/teaching_planner.py#L227-L236) | 课程页进度不一致 | 统一走 `TeachingPlanner` |
| **B08** | 叙事种子条件未实现 | P1 | 记忆→叙事 | [`narrative_engine.py:217-219`](../../backend/services/narrative_engine.py#L217-L219) `time_gap`；种子 [`migration:41-44`](../../backend/alembic/versions/2026_04_25_add_narrative_and_achievements.py#L41-L44) `requires_prior_struggle` | welcome_back/breakthrough 不触发 | 实现条件或下线种子 |
| **B09** | `used_memory_ids` 存 fact_type | P1 | 学习→记忆 | [`learning_engine.py:244`](../../backend/services/learning_engine.py#L244) | 无法追溯记忆 ID | 用 `write_facts` 返回 id |
| **B10** | `CourseIntentModule` 未接线 | P1 | 画像→教学 | 未在 [`builder.py:46-61`](../../backend/services/prompt_builder/builder.py#L46-L61)；模块 [`course_intent.py:42`](../../backend/services/prompt_builder/modules/course_intent.py#L42) | 课程意图不进 Prompt | 加入 MODULE_CONFIGS |
| **B11** | `concept_map` 边类型不一致 | P1 | 概念关联 | 生成 [`course_generator.py:57`](../../backend/services/course_generator.py#L57) `prerequisite`；召回 [`recall_service.py:49-52`](../../backend/services/recall_service.py#L49-L52) `requires` | 前置边遍历为空 | 双类型兼容 |
| **B12** | `misconceptions` / `episodes` 无写入器 | P2 | 画像→教学 | 模块 [`misconception.py:45`](../../backend/services/prompt_builder/modules/misconception.py#L45)、[`episode.py:49`](../../backend/services/prompt_builder/modules/episode.py#L49)；主路径无 producer | Prompt 段恒为空 | LLM 提取或写入器 |
| **B13** | `late_night_session` 无统计 | P2 | 画像→成就 | 种子 [`migration:137-142`](../../backend/alembic/versions/2026_04_25_add_narrative_and_achievements.py#L137-L142)；无写入器 | night_owl 不可达 | 实现统计或下线 |
| **B14** | 叙事冷却仅存内存 | P2 | 记忆→叙事 | [`narrative_engine.py:40`](../../backend/services/narrative_engine.py#L40) `_cooldowns` | 重启后重复弹窗 | DB/Redis 持久化 |
| **B15** | Channel-2 污染画像分母 | P2 | 记忆→画像 | 哨兵 [`memory_manager.py:320-364`](../../backend/services/memory_manager.py#L320-L364)；聚合 [`profile_aggregator.py:128`](../../backend/services/profile_aggregator.py#L128) | 维度分数偏噪声 | 聚合排除 `__channel2_*` |
| **B16** | `dimension_crossing` 非跨越语义 | P2 | 画像→成就 | [`gamification.py:149-154`](../../backend/services/gamification.py#L149-L154) | 首次出分即解锁 | snapshot 比较 |
| **B17** | `fact_transition` 未校验 from | P2 | 画像→成就 | [`gamification.py:165-170`](../../backend/services/gamification.py#L165-L170) | learn_from_setback 误触发 | 查历史 struggle |
| **B18** | 每次 start 重复 Seed Memory | P2 | 学习→记忆 | [`learning.py:514-523`](../../backend/api/routes/learning.py#L514-L523) 无去重 | memory_facts 膨胀 | 仅首次 seed |

### 按链路聚合的断裂地图

```
记忆 ──► 画像     [B15 分母污染]                    强度 0.85，非阻断
画像 ──► 教学     [B03 掌握度] [B10 课程意图未注入]   强度 0.72↓
教学 ──► 学习     [B04/B05 前端契约] [B06 tool短路]   强度 0.68↓
学习 ──► 记忆     [B09 溯源] [B06] [B18]             强度 0.88，主路径可用
记忆 ──► 叙事     [B08 条件] [B14 冷却] [B04 展示]    强度 0.58↓
画像 ──► 成就     [B02 会话统计] [B13] [B05 展示]    强度 0.45↓
概念关联         [B01 未接线] [B11 边类型]            强度 0.35↓
```

### 修正后闭环完成率

| 指标 | 初稿 | 回写后 | 说明 |
|------|------|--------|------|
| **逻辑闭环完成率** | 72% | **68%** | 计入前端展示断裂（B04/B05）后，教学→学习与叙事/成就体验降级 |
| **主路径 chat 可用率** | — | **~85%** | 对话/记忆/维度聚合/部分叙事条件仍可用 |
| **P0 断裂数** | 2（文档初稿） | **5** | B01–B05，任一不修复则对应链路在生产不可验收 |
| **P1 断裂数** | — | **5** | B06–B11 |
| **P2 断裂数** | — | **7** | B12–B18 |

**强链路（仍可依赖）**：学习→记忆（0.88）、记忆→画像（0.85）。

**弱链路（需 P0 方可验收）**：概念关联（0.35）、画像→成就（0.45）、教学→学习 UI 反馈（0.68）。

### P0 修复最小闭环（建议 v1.0.5 门禁）

修复以下 5 项即可将**可验收完成率提升至 ~80%**，且互不阻塞：

1. **B01** + **B11**（同 PR）：`current_topic` 注入 + concept_map 边类型兼容  
2. **B02**：`learning_stats.total_sessions` 或成就检查读 `session_count`  
3. **B03**：`mastery_level` 读 `ConceptMastery`  
4. **B04** + **B05**（同 PR）：前端字段适配或 OpenAPI 统一  

### 架构兜底（断裂存在时仍可用）

| 机制 | 源码 | 掩盖的断裂 | 不掩盖 |
|------|------|-----------|--------|
| Channel-2 关键词记忆 | [`memory_manager.py:291-371`](../../backend/services/memory_manager.py#L291-L371) | LLM 未输出 `<memory>` | B01 |
| 情感关键词回退 | [`dynamic_analyzer.py`](../../backend/services/dynamic_analyzer.py) 关键词分支 | LLM 情感 API 失败 | B03 |
| Strategy/Narrative try/except | [`builder.py`](../../backend/services/prompt_builder/builder.py) 模块 build | 单模块异常 | B08 |
| 成就 SAVEPOINT | [`gamification.py:106`](../../backend/services/gamification.py#L106) | 并发重复解锁 | B02 |
| `course.meta` 向后兼容 | [`teaching_planner.py:79`](../../backend/services/teaching_planner.py#L79) | 无 LessonPlan 旧课 | B07 |

---

### 总结（链路强度速查）

| 指标 | 结论 |
|------|------|
| **闭环完成率** | **68%**（逻辑）；**~85%**（主路径 chat 可对话） |
| **P0 断裂** | 5 项：B01–B05（见 §闭环断裂点总览） |
| **强链路** | 学习→记忆（0.88）、记忆→画像（0.85） |
| **弱链路** | 概念关联（0.35）、画像→成就（0.45） |
| **性能上限** | 每轮 1–2 次 LLM；观察者 +15~30ms（SQLite） |
| **性能下限** | LLM 失败整轮 rollback；B01/B02/B04/B05 导致「有逻辑无体验」 |

---

## 可调参数集中管理

### 第 1 层：config.py（系统级行为参数）

**特点**：部署级常量，修改需重启服务；适合算法系数、全局阈值、不宜频繁变更的枚举。

**配置范围**（[`config.py:59-109`](../../backend/core/config.py#L59-L109) `Settings.learning_system`）：

| 分组 | 键 | 默认值 | 修改影响 |
|------|-----|--------|---------|
| `memory` | `dedup_window_hours` | 24 | 记忆去重窗口；过大则重复事实减少，过小则合并敏感 |
| | `max_working_context_tokens` | 4000 | LLM 工作记忆上限；影响长对话上下文保留 |
| | `max_working_context_messages` | 50 | 工作记忆条数上限 |
| | `salience_base_decay` | 0.1 | 记忆衰减基底；越大旧记忆消退越快 |
| | `salience_recall_factor` | 0.5 | 召回次数对衰减的抑制强度 |
| | `default_retrieve_limit` | 10 | 每轮注入 Prompt 的记忆条数 |
| | `observe_recent_limit` | 20 | 叙事/召回观察窗口 |
| `profile` | `hallucination_guard_min_facts` | 3 | 画像维度最低事实数；调高则更保守 |
| | `strength_threshold` / `weakness_threshold` | 0.7 / 0.4 | strengths/weaknesses 分类边界 |
| `extraction` | `channel2_enabled` | true | 关闭则仅 LLM 标签提取记忆 |
| | `confusion_keywords` 等 | 中文词表 | Channel-2 信号触发词；**可外置但当前在 L1** |
| `salience_type_multiplier` | 按 fact_type | concept_struggle=0（不衰减）等 | 控制各类型记忆遗忘曲线 |
| `mastery` | `delta_map` | mastered +25 / struggle -15 | 掌握度波动幅度 |
| | `auto_advance_threshold` | 70 | 章节自动推进阈值 |
| | `weak_threshold` | 40 | 薄弱概念判定 |

**硬编码风险**：`extraction.*_keywords` 仍在 L1，运营无法热更新；建议 v1.0.5 迁入 L2 关键词规则表。

---

### 第 2 层：DB 规则表（业务规则）

**特点**：运营可配置（SQL/Admin），新增行即可扩展能力，无需改代码。

| 表 | 业务规则 | 可配置维度 | 适用场景 |
|----|---------|-----------|---------|
| `profile_dimension_defs` | 画像维度名、聚合算法、源 fact_type | `aggregation_method` / `aggregation_params` / `enabled` | 新增「空间思维」等维度 |
| `strategy_rules` | 维度分数→教学话术 | `low/mid/high_instruction` / `scene` / `priority` | ZPD 个性化教学 |
| `narrative_trigger_rules` | 何时弹叙事 | `condition_type` / `condition_params` / `cooldown_minutes` / 模板 | 突破/困难连锁/回归欢迎 |
| `achievement_defs` | 何时解锁成就 | `condition_type` / `condition_params` / `rarity` / `hidden` | 成长激励体系 |
| `characters.traits` | 教师人格五维 | JSON `{strictness, pace, ...}` | 角色级教学风格 |

**种子数据状态**（migration `2026_04_25_*`）：5 维度 / 4 策略 / 5 叙事规则 / 8+ 成就 — 均已种子化。

**注意**：`condition_type` 必须在引擎中有对应分支，否则规则**静默失效**（已有 `TODO-N4` 警告日志）。

---

### 第 3 层：DB 运行时数据（可扩展）

**特点**：每用户/会话实例化，运行时频繁读写，是闭环的「状态机内存」。

| 存储 | 动态扩展能力 | 运行时变更逻辑 |
|------|-------------|---------------|
| `memory_facts` | 无限增长（需 cleanup） | 每轮对话 extract_and_store；叙事 writeback；dedup 合并 |
| `learner_profiles.profile` | JSON 自由扩展字段 | `DynamicAnalyzer` 写 affect；`ProfileAggregator` 写 dimension_scores；注意 merge write 保留异构字段 |
| `sessions.relationship` | 四维 + stage + history | 每轮 `RelationshipService.update_dimensions` |
| `concept_mastery` / `fsrs_states` | per-user 概念级 | `MasteryTracker.update_from_memories` |
| `course_progress` | per-user per-course | 手动/自动推进章节 |
| `course.meta` | concept_map / course_narrative_plan | 课程生成时写入；叙事模块读取 |
| `achievements` | 解锁记录追加 | 首次满足条件 INSERT，唯一约束幂等 |

---

## 实施依赖图

### 依赖拓扑（文字结构化）

```
[L0 基础设施]
  users / worlds / characters / courses / sessions
  alembic migrations (2026_04_06 base → 2026_06_20 head)
       │
       ├─强依赖─► [L1 记忆系统]
       │            memory_facts 表 + MemoryManager + MemoryExtractor
       │            │
       │            ├─强依赖─► [L2 学习画像]
       │            │            profile_dimension_defs (种子)
       │            │            ProfileAggregator
       │            │            │
       │            │            ├─强依赖─► [L3 教学策略]
       │            │            │            strategy_rules (种子)
       │            │            │            StrategyModule
       │            │            │
       │            │            └─弱依赖─► UserProfile 跨世界聚合
       │            │
       │            ├─强依赖─► [L4 掌握度 / FSRS]
       │            │            concept_mastery + fsrs_states
       │            │            MasteryTracker
       │            │            │
       │            │            └─强依赖─► TeachingPlanner 自动推进
       │            │
       │            └─强依赖─► [L5 叙事 / 成就]
       │                         narrative_trigger_rules + achievement_defs (种子)
       │                         NarrativeEngine + GamificationEngine
       │
       ├─强依赖─► [L6 教学编排]
       │            PromptBuilder (13 modules)
       │            LearningEngine.process_message
       │            │
       │            └─强依赖─► LLM Adapter (providers/manager)
       │
       ├─弱依赖─► [L7 课程生成]
       │            TextbookLibrary → CourseGenerator → LessonPlan + concept_map
       │            （无课程亦可对话，但概念关联/课程感知降级）
       │
       └─弱依赖─► [L8 前端]
                    learning.ts / Learning.vue / MemoryFactsDrawer
                    （依赖 Chat API 契约；**B04/B05 未修复则叙事/成就 UI 空白**）
```

### 强依赖 vs 弱依赖

| 关系 | 类型 | 说明 |
|------|------|------|
| 记忆 → 画像 | **强** | 无 MemoryFact 则 dimension_scores 永为空 |
| 画像 → 策略 | **强** | 无 dimension_scores 则 StrategyModule 跳过 |
| 记忆 → 叙事/成就 | **强** | 观察者输入依赖 recent_facts |
| 课程 → 概念关联 | **弱** | 无 concept_map 时 RecallService 返回空，主对话仍可用 |
| 课程 → 叙事 Prompt | **弱** | 无 course_narrative_plan 时 NarrativeModule 跳过 |
| UserProfile → 教学 | **无依赖** | 明确不注入 Prompt，仅展示 |
| 前端 → 叙事/成就展示 | **强（断裂）** | API 有数据但字段名不一致（B04/B05），toast 正文/标题为空 |
| ChromaDB → 记忆 | **无依赖** | 未实现，不阻塞当前发布 |

### 推荐开发先后顺序（v1.0.5 门禁 = §闭环断裂点 B01–B05）

| 顺序 | 断裂 ID | 修复包 | 预估 |
|------|---------|--------|------|
| 1 | B04 + B05 | 前后端 Chat 响应字段统一（叙事/成就 toast） | 0.5d |
| 2 | B02 | `learning_stats.total_sessions` 或成就读 `session_count` | 0.5d |
| 3 | B01 + B11 | `current_topic` 注入 + concept_map 边类型兼容 | 1d |
| 4 | B03 | `mastery_level` ← `ConceptMastery` | 0.5d |

**P1（闭环完整性，不阻塞发版）**：B06 tool 观察者 · B07 推进单源 · B08 叙事条件 · B09 used_memory_ids · B10 CourseIntent 接线

**P2（体验与数据质量）**：B12–B18（见登记册）

**已完成的文档项**：四子系统详细设计 01–04 已齐，不再阻塞架构评审。

---

## 待产品确认项（与断裂修复相关）

| # | 待确认项 | 关联断裂 | 默认建议 |
|---|---------|---------|---------|
| 1 | `total_sessions` 口径：Session 结束计数 vs chat 轮次 | B02 | 采用 `end_session` 的 `session_count`，chat 成就检查合并读取 |
| 2 | `concept_map` 节点 id 是否与 `LessonPlan.concepts` 字符串强制一致 | B01/B11 | 生成侧统一；召回侧 trim + 别名表 |
| 3 | 未实现叙事/成就种子是否下线 | B08/B13 | v1.0.5 前 migration `enabled=false` |
| 4 | v1.0.4 发布是否要求 B04/B05 前端修复 | B04/B05 | 若发版含成就/叙事 UI，列为门禁 |
| 5 | ChromaDB 是否继续延期 | 架构债 | 维持 SQL 检索，不阻塞本轮 |

---

## 断裂点修订记录

| 日期 | 变更 |
|------|------|
| 2026-06-20 | 初稿：7 链路评估，完成率 72%，P0×2 |
| 2026-06-20 | **四子系统回写**：新增 §闭环断裂点总览，登记 B01–B18；完成率修正为 68%（含 UI 契约）；新增 P0 B04/B05 |

---

*文档生成方式：基于四子系统详细设计（01–04）回写断裂点；**功能描述均附源码行号锚点**（见文首「代码锚点引用规范」）。代码勘探日期 2026-06-20。*
