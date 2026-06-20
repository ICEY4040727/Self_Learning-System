# 03 教学系统 — 详细设计

> **版本**：v1.0.4  
> **日期**：2026-06-20  
> **状态**：已落地（主编排与 Prompt 模块化可用，课程进度双源与部分模块未接线）  
> **上级文档**：[四大系统闭环架构设计 — 总览](WholeDesign.md)  
> **关联文档**：[01 记忆系统](01_memory_system.md) | [02 学习画像](02_learner_profile.md)

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

教学系统是平台的**唯一 LLM 教学调用编排中枢**：将教师人格、课程结构、学习者画像、记忆上下文、关系与情感状态组装为动态 system prompt，执行苏格拉底式多轮对话，并在每轮结束后驱动记忆写入、画像更新、掌握度演算与叙事/成就观察者。

核心方法论：**不直接灌输答案**，通过问题链引导；课程结构来自教材 AI 生成，授课过程由 Prompt 模块注入章节与概念图。

### 1.2 系统边界

| 范围内 | 范围外 |
|--------|--------|
| `LearningEngine.process_message` 主编排 | `MemoryFact` 存储实现（记忆系统） |
| `PromptBuilder` 静态层 + 动态层 | `ProfileAggregator` 维度算法（画像系统） |
| `CourseGenerator` 教材→课程结构 | 叙事触发 / 成就解锁（叙事系统） |
| `TeachingPlanner` 章节进度 CRUD | 前端 Galgame UI 渲染 |
| `RelationshipService` / `DynamicAnalyzer` 教学态输入 | 用户 LLM 配置审计（独立子系统） |
| 学习会话 API（start / chat / end） | 世界壳创建向导（v1.0.4 独立文档） |

### 1.3 角色与层级

| 概念 | 存储 | 教学中的用途 |
|------|------|-------------|
| **Sage** (`Character.type=sage`) | `characters` + `world_characters` | AI 教师人格、LLM 设置、记忆 `character_id` |
| **Traveler** (`Character.type=traveler`) | 同上 | 游戏化身；注入静态层「学习者身份」 |
| **LearnerProfile** | `learner_profiles` | 学习追踪；策略/偏好/元认知模块数据源 |
| **Session** | `sessions` | 单次学习会话；`relationship` JSON 载体 |

### 1.4 核心设计约束

1. **单编排入口**：[`learning_engine.py:85`](../../backend/services/learning_engine.py#L85) → [`:179-192`](../../backend/services/learning_engine.py#L179-L192)。
2. **数据驱动策略**：[`strategy.py:40-58`](../../backend/services/prompt_builder/modules/strategy.py#L40-L58)；规则 [`models.py:448`](../../backend/models/models.py#L448)。
3. **课程感知**：[`course_content.py`](../../backend/services/prompt_builder/modules/course_content.py)；[`teaching_planner.py:99`](../../backend/services/teaching_planner.py#L99)。
4. **观察者后置**：步骤 13–19 [`learning_engine.py:234-323`](../../backend/services/learning_engine.py#L234-L323)；工具短路 [`:194-203`](../../backend/services/learning_engine.py#L194-L203)。
5. **LLM 配置优先级**：`Character.llm_settings` 覆盖 `User` 默认 → `get_effective_character_llm_config`。

### 1.5 实现进度量化

| 模块 | 代码行数 | 测试 | 稳定性 |
|------|---------|------|--------|
| [`learning_engine.py`](../../backend/services/learning_engine.py) | 375 | test_learning_sessions | B |
| `prompt_builder/builder.py` + modules/contexts | ~1,100 | `test_prompt_builder.py`（38 cases） | B |
| `teaching_planner.py` | 330 | `test_course_content_integration.py` | A |
| `course_generator.py` | 243 | `test_textbook_course_gen.py`（37 cases） | B |
| `dynamic_analyzer.py` + `relationship.py` | 407 | 间接覆盖 | B |
| `api/routes/learning.py` | 810 | `test_learning_sessions.py` | A |
| `api/routes/textbook.py`（教学相关段） | ~400 | `test_textbook_*` | B |
| **合计** | **~2,417 服务 + ~1,200 API** | — | **B+（~80%）** |

---

## 2. 架构总览

```
教材上传 ──► OCR/提取 ──► CourseGenerator ──► LessonPlan + course.meta
                                                      │
用户 ──► POST /start ──► Session + Seed Memory       │
         │                                              │
         ▼                                              ▼
    POST /chat ──► LearningEngine.process_message
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
   PromptBuilder   MemoryManager    LLM Adapter
   (静态+动态)      (工作记忆)      (多 Provider)
         │              │              │
         └──────────────┴──────────────┘
                        │
         ┌──────────────┼──────────────┬──────────────┐
         ▼              ▼              ▼              ▼
    记忆写入      画像聚合       掌握度/FSRS     叙事/成就
```

### 2.1 教学生命周期

| 阶段 | 触发 | 关键服务 |
|------|------|---------|
| 课程结构生成 | `POST .../courses/{id}/generate` | `CourseGenerator` → `LessonPlan` 行 |
| 开始会话 | `POST .../courses/{id}/start` | 创建 `Session`，Seed Memory，动态/静态 greeting |
| 多轮对话 | `POST .../courses/{id}/chat` | `LearningEngine` 全链路 |
| 进度推进 | 掌握度自动 / `POST .../advance` | `MasteryTracker` / `TeachingPlanner` |
| 结束会话 | `POST .../sessions/{id}/end` | `session_count++`，UserProfile 更新 |

---

## 3. 主编排：LearningEngine

### 3.1 `process_message` 二十步流水线

| 步 | 动作 | 读/写 | 源码 |
|----|------|-------|------|
| 1 | 加载 `Session` | 读 | [`learning_engine.py:100-103`](../../backend/services/learning_engine.py#L100-L103) |
| 2–5 | 加载 Sage / LearnerProfile / Traveler | 读 | [`:105-126`](../../backend/services/learning_engine.py#L105-L126) |
| 6 | 上条用户消息 `emotion_analysis` → `prev_emotion` | 读 | [`:128-137`](../../backend/services/learning_engine.py#L128-L137) |
| 7 | `PromptBuilder.build()` | 读 DB | [`:166-171`](../../backend/services/learning_engine.py#L166-L171) |
| 8 | `memory_manager.get_working_context()` | 读 `chat_messages` | [`:173-174`](../../backend/services/learning_engine.py#L173-L174) |
| 9 | `llm_adapter.chat()` | **LLM** | [`:186-192`](../../backend/services/learning_engine.py#L186-L192) |
| 10 | `parse_tool_request()` | **提前 return** | [`:194-203`](../../backend/services/learning_engine.py#L194-L203) |
| 11 | `analyze_emotion()` | LLM/关键词 | [`:205-212`](../../backend/services/learning_engine.py#L205-L212) |
| 12 | `relationship.update_dimensions()` | 写 relationship | [`:214-232`](../../backend/services/learning_engine.py#L214-L232) |
| 13 | `memory_manager.extract_and_store()` | 写 MemoryFact | [`:236-244`](../../backend/services/learning_engine.py#L236-L244) |
| 14 | `update_learner_profile()` | 写 LearnerProfile | [`:246-256`](../../backend/services/learning_engine.py#L246-L256) |
| 15 | `profile_aggregator.aggregate()` | 写 dimension_scores | [`:258-264`](../../backend/services/learning_engine.py#L258-L264) |
| 16 | `update_user_profile_after_chat()` | 写 UserProfile | [`:266-268`](../../backend/services/learning_engine.py#L266-L268) |
| 17 | `db.flush()` | — | [`:270-271`](../../backend/services/learning_engine.py#L270-L271) |
| 17.6 | `mastery_tracker.update_from_memories()` | 写掌握度/FSRS | [`:284-290`](../../backend/services/learning_engine.py#L284-L290) |
| 18 | `narrative_engine.check_triggers()` | 读+可选写 | [`:292-301`](../../backend/services/learning_engine.py#L292-L301) |
| 19 | `gamification_engine.check_achievements()` | 写 achievements | [`:314-323`](../../backend/services/learning_engine.py#L314-L323) |
| 20 | `strip_memory_tags` + 组装响应 | 返回前端 | [`:325-342`](../../backend/services/learning_engine.py#L325-L342) |

### 3.2 Context 字典契约

`process_message` 第 7 步构建的 `context`：

| 键 | 类型 | 来源 | 消费模块 |
|----|------|------|---------|
| `db` | Session | 参数 | 几乎所有模块 |
| `world_id` | int | session | WorldSetting, 记忆检索 |
| `session_id` | int | session | 预留 |
| `course_id` | int | session | CourseContent, Narrative, Recall |
| `character_id` | int | sage_character_id | MemoryFacts |
| `relationship` | dict | session | RelationshipContext |
| `learner_profile` | LearnerProfile | session | Strategy, Preference, … |
| `prev_emotion` | dict | 上条用户消息 | ScaffoldContext, Affect |
| `mastery_level` | int | **硬编码** [`learning_engine.py:161`](../../backend/services/learning_engine.py#L161) | [`builder.py:356`](../../backend/services/prompt_builder/builder.py#L356) ScaffoldContext |
| `user_message` | str | 当前输入 | 预留记忆检索扩展 |
| **缺失** | `current_topic` | — | RecallContext **空转** ⚠️ |
| **缺失** | `scene` | 默认未设 | StrategyModule 用默认 `learning` |

### 3.3 异常与事务

- 任一步骤未捕获异常 → 整轮 `db.rollback()`，返回 `type: error`。
- `ChatMessage` 持久化在 **API 层**（`learning.py` `send_message`），不在引擎内；引擎失败时用户消息可能未入库。

---

## 4. PromptBuilder：模块化提示词

### 4.1 两层结构

```
system_prompt = build_static_layer(character, traveler)
              + "\n\n---\n\n"
              + build_dynamic_layer(scene, context)
```

| 层 | 刷新频率 | 内容 |
|----|---------|------|
| **静态层** | 角色/世界不变则稳定 | Sage 人格、苏格拉底规则、Mermaid 规则、Traveler 身份 |
| **动态层** | 每轮对话 | 关系、脚手架、课程、策略、记忆、情感等 |

静态层数据源：`Character` + `WorldCharacter`（`world_title`, `world_background`, `relationship_seed`）。

### 4.2 学习场景模块编排（`SceneConfig.LEARNING`）

按 `get_priority()` 升序组装；`always_include=True` 的模块跳过 `should_include`：

| 优先级 | 模块 | 固定/动态 | 数据源 |
|--------|------|----------|--------|
| 1 | `RelationshipContext` | 上下文 | `context.relationship` |
| 2 | `ScaffoldContext` | 上下文 | `prev_emotion` + `mastery_level` |
| 5 | `WorldSettingModule` | **固定** | `World.description` |
| 10 | `NarrativeModule` | **固定** | `Course.meta.course_narrative_plan` |
| 12 | `CourseContentModule` | 条件 | `LessonPlan` + `CourseProgress` + `meta` |
| 25 | `StrategyModule` | 条件 | `dimension_scores` + `strategy_rules` |
| 30 | `MisconceptionModule` | 条件 | `LearnerProfile.misconceptions` |
| 40 | `EpisodeModule` | 条件 | `LearnerProfile.episodes` |
| 50 | `PreferenceModule` | 条件 | `LearnerProfile.preferences` |
| 60 | `AffectModule` | 条件 | `LearnerProfile.affect` |
| 70 | `MemoryFactsModule` | 条件 | `memory_manager.retrieve` |
| 75 | `RecallContextModule` | 条件 | `recall_service`（需 `current_topic`） |
| 80 | `MetacognitionModule` | 条件 | `LearnerProfile.metacognition` |

**其他场景**：

- `REVIEW`：仅 `MemoryFactsModule`
- `ASSESSMENT`：空（未实现）

### 4.3 未接线模块

| 模块 | 状态 |
|------|------|
| `CourseIntentModule` | 已实现读 `Course.meta`（current_level/motivation/pace），**未加入 `MODULE_CONFIGS`**，生产 Prompt 不注入 |

### 4.4 静态层硬编码块（L1 级）

以下写在 `build_static_layer`，修改需发版：

1. **苏格拉底五条规则**（`builder.py:230-235`）
2. **Mermaid 使用规范**（`builder.py:238-241`）
3. **默认教师降级文案**（无 Character 时）

### 4.5 动态层降级

`build_with_fallback`：模块异常时 `logger.warning`，单模块跳过；整体失败时 `_build_basic_dynamic_layer`（仅关系阶段 + 情感/掌握度一行）。

---

## 5. 脚手架与关系（教学态辅助）

### 5.1 ScaffoldContext — ZPD 自适应

`compute_scaffold_level(emotion_type, mastery_level)` → 1–5 级指令。

| 条件示例 | 等级 |
|---------|------|
| frustration + mastery&lt;30 | 5（最高支持） |
| excitement + mastery&gt;70 | 1（最低支持） |
| neutral + mastery 30–70 | 3 |

**硬编码风险**：完整规则表在 `scaffold.py` 内 if-else；`mastery_level` 当前恒为 50，脚手架主要受情感驱动。

### 5.2 RelationshipService

| 能力 | 说明 |
|------|------|
| `update_dimensions` | 8 类情感 → trust/familiarity/respect/comfort delta |
| `derive_stage` | 四维均值 → stranger/acquaintance/friend/mentor/partner |
| `get_instructions` | 低信任/低舒适 → 温和引导文案 |
| `check_events` | 阶段变化、维度突破事件 |

阶段阈值（0.20/0.45/0.65/0.85）与 delta 表均**硬编码**于 `relationship.py`。

### 5.3 DynamicAnalyzer（教学相关部分）

| 能力 | 模式 | 用途 |
|------|------|------|
| `analyze_emotion` | LLM JSON 分类（主） / 关键词加权（备） | 本轮情感、关系更新 |
| `update_learner_profile` | 规则 | `affect` / `preferences` 轻量写入 |

8 类情感 taxonomy 硬编码于 `EDUCATION_EMOTIONS`。

---

## 6. 课程结构与进度

### 6.1 CourseGenerator — 教材 → 大纲

**入口**：`POST /api/textbooks/courses/{course_id}/generate`

| 步骤 | 说明 |
|------|------|
| 合并教材 `extracted_text` | 按章节边界截断 `MAX_GENERATION_CHARS` |
| LLM 调用 | `temperature=0.3`, `max_tokens=4096` |
| 解析 JSON | `overview`, `lessons[]`, `concept_map` |
| 持久化 | `course.meta` + 每课一行 `LessonPlan` + 初始化 `CourseProgress` |

**concept_map 契约**：

```json
{
  "nodes": [{"id": "concept_1", "label": "概念名"}],
  "edges": [{"source": "a", "target": "b", "relation": "prerequisite"}]
}
```

`RecallService` 要求边 `type=requires`（生成 prompt 写 `relation: prerequisite`）——**存在字段名不一致风险**，需映射或统一。

### 6.2 TeachingPlanner — 进度权威（新）

| 方法 | 职责 |
|------|------|
| `get_current_lesson` | 当前章 dict + `_index` / `_total` |
| `get_progress` | 全课进度百分比、每章 `_status` |
| `advance_lesson` | 标记完成 + 索引 +1，写 `CourseProgress` |
| `set_lesson` | 手动跳章 |
| `_record_lesson_progress` | 首次到达写 `ProgressTracking(topic_type=lesson)` |

**数据源优先级**：`LessonPlan` + `CourseProgress` &gt; `course.meta` 回退。

### 6.3 自动推进双源（架构债）

| 组件 | 推进写往 | 读取章列表 |
|------|---------|-----------|
| `TeachingPlanner` | `CourseProgress` | `LessonPlan` |
| `MasteryTracker._try_auto_advance` | **`course.meta`** | **`course.meta.generated_lessons`** |

掌握度达标时，**可能只更新 meta 而不更新 `CourseProgress`**，导致 `CourseContentModule` 显示进度与掌握度推进不一致。

### 6.4 工具调用短路

LLM 返回 `<tool>...</tool>` 时，第 10 步 `return type: tool_request`，**跳过**步骤 11–19（情感、记忆、画像、掌握度、叙事、成就）。

前端需确认工具执行后是否补跑观察者；当前无自动补偿。

---

## 7. LLM 调用链

### 7.1 配置合并

```
get_effective_character_llm_config(user, sage_character)
  = User 默认 (provider, api_key, model, temperature, max_tokens, base_url)
    覆盖 Character.llm_settings 中非空字段
```

### 7.2 Adapter 栈

| 组件 | 职责 |
|------|------|
| `llm/manager.py` | Provider 路由、缓存、预算 |
| `llm/adapter.py` | 统一 `chat()` / 流式接口 |
| `llm/providers.py` | Claude / OpenAI / Ollama 等端点 |
| `llm/resilience.py` | 重试与错误分类 |

教学对话调用：

```python
llm_adapter.chat(
    messages=working_context + [current_user],
    system_prompt=system_prompt,
    temperature=..., max_tokens=..., ...
)
```

### 7.3 额外 LLM 调用点（非主编排）

| 场景 | 调用 |
|------|------|
| 每轮情感分析 | `DynamicAnalyzer.analyze_emotion`（可 LLM） |
| 会话开场 greeting | `_generate_contextual_greeting`（start 时） |
| 课程生成 | `CourseGenerator.generate` |

单轮 chat 典型 **1–2 次** LLM（教学 + 情感）；greeting 在 start 时额外 1 次。

---

## 8. 画像 → 教学闭环

| 链路 | 实现 | 强度 |
|------|------|------|
| `dimension_scores` → `StrategyModule` | 读 `strategy_rules` 三档指令 | 0.75 |
| `preferences` / `metacognition` → 对应模块 | 文本拼接 | 0.70 |
| `misconceptions` / `episodes` | 模块就绪，**无写入器** | 0.20 |
| `ConceptMastery` → `mastery_level` context | **未实现** | 0.00 |
| `RecallService` → `RecallContextModule` | **缺 current_topic** | 0.40 |

**StrategyModule 匹配规则**：

- `score < 0.4` → `low_instruction`
- `0.4 ≤ score ≤ 0.7` → `mid_instruction`（种子多为 NULL → 不干预）
- `score > 0.7` → `high_instruction`
- `scene` 过滤：`learning` / `all`

---

## 9. 接口契约

### 9.1 学习会话 API（`api/routes/learning.py`）

#### `POST /api/learning/courses/{course_id}/start`

| Body | `{ "sage_id": int | null }` |
| 行为 | 创建 `Session`；Seed Memory；返回 greeting + 会话元数据 |
| Greeting | 优先 LLM 情境开场 → fallback `_GREETING_FALLBACKS` |

#### `POST /api/learning/courses/{course_id}/chat`

| Body | `{ "message": string, 1–5000 字 }` |
| 前置 | 存在未结束 `Session` |
| 响应 `ChatResponse` | 见下表 |

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | `text` \| `tool_request` \| `error` | |
| `reply` | string | 已 strip `<memory>` |
| `emotion` | object | `{emotion_type, confidence, valence, arousal}` |
| `relationship_stage` | string | 五阶段之一 |
| `relationship` | object | 四维 + stage + history |
| `expression_hint` | string | 前端立绘：`happy`/`thinking`/`concerned`/`default` |
| `memory_extracted_count` | int | 本轮 Channel-1 记忆条数 |
| `narrative_events` | list | 叙事 toast/modal |
| `new_achievements` | list | 新解锁成就 |

#### `POST /api/learning/sessions/{session_id}/end`

结束会话；`session_count++`；更新 `UserProfile`。

#### `GET /api/learning/sessions/{session_id}/history`

返回聊天记录列表。

---

### 9.2 课程与进度 API（`api/routes/textbook.py` 节选）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/courses/{id}/generate` | AI 生成课程结构 |
| GET | `/courses/{id}/progress` | `teaching_planner.get_progress` |
| POST | `/courses/{id}/advance` | 手动推进下一课 |
| POST | `/courses/{id}/set-lesson` | 跳转指定章索引 |
| GET | `/courses/{id}/mastery` | 课程掌握度概览 |
| GET | `/courses/{id}/lessons` | `LessonPlan` 列表 |

---

### 9.3 内部服务 API

#### `PromptBuilder.build(character, scene, context, traveler_character=None) → str`

完整 system prompt。

#### `TeachingPlanner.get_current_lesson(db, course) → dict | None`

**推荐**作为 `current_topic` 来源：取 `concepts[0]` 或 concept_map 节点 id。

#### `CourseGenerator.generate(text, course_name, ...) → dict`

返回 `{overview, lessons, concept_map}`。

---

## 10. 可调参数

### 10.1 L1：`config.py`

| 分组 | 教学相关键 |
|------|-----------|
| `learning_system.memory` | 工作记忆 Token/条数上限 |
| `learning_system.mastery` | 掌握度 delta、自动推进阈值 70、章初始 20 |
| `learning_system.profile` | 策略依赖的 strength/weakness 阈值 |
| `Settings.llm_*` | 默认 Provider（用户/角色可覆盖） |

### 10.2 L2：DB 规则表

| 表 | 教学消费方 |
|----|-----------|
| `strategy_rules` | `StrategyModule` |
| `characters.traits` | 静态层五维性格参数 |
| `characters.system_prompt_template` | 静态层自定义块 |
| `lesson_plans` | `CourseContentModule` / `TeachingPlanner` |
| `course.meta` | 概览、concept_map、叙事 plan、意图字段（部分未注入） |

### 10.3 L3：运行时

| 存储 | 内容 |
|------|------|
| `sessions.relationship` | 关系四维 + 阶段 |
| `course_progress` | 当前章索引、已完成列表 |
| `chat_messages` | 工作记忆源 |

---

## 11. 前端契约

| Store / 组件 | API |
|--------------|-----|
| `learning.ts` `startSession` | `POST /courses/{id}/start` |
| `learning.ts` `sendMessage` | `POST /courses/{id}/chat` |
| `CoursePage.vue` | `GET /worlds/{id}/learner_profile` |
| `Learning.vue` | 消费 `narrative_events` / `new_achievements` / `expression_hint` |

---

## 12. 测试覆盖

| 文件 | 覆盖点 |
|------|--------|
| `test_teaching_system.py` | StrategyModule、RecallService |
| `test_prompt_builder.py` | 模块组装、静态层 |
| `test_course_content_integration.py` | CourseContent + 进度 |
| `test_textbook_course_gen.py` | CourseGenerator 端到端 |
| `test_learning_sessions.py` | start/chat API |
| `test_llm_call_chain.py` | LLM 适配器链 |

**缺口**：`process_message` 全链路集成；`tool_request` 短路副作用；`CourseIntentModule` 接线；自动推进双源一致性。

---

## 13. 已知缺陷与改造路线图

| 优先级 | 项 | 说明 |
|--------|-----|------|
| **P0** | 注入 `current_topic` | 打通 RecallContext + 概念关联 |
| **P0** | `mastery_level` 读 `ConceptMastery` | 修复 Scaffold 与真实掌握度脱节 |
| **P0** | 统一自动推进 | `MasteryTracker` 改写 `CourseProgress` |
| P1 | 接入 `CourseIntentModule` | 加入 `MODULE_CONFIGS` 或合并进 CourseContent |
| P1 | `tool_request` 观察者补偿 | 至少写记忆/情感 |
| P1 | concept_map 边类型统一 | `prerequisite` vs `requires` |
| P2 | Scaffold/Relationship 规则表化 | 减少 if-else 硬编码 |
| P2 | `SceneConfig` 可配置化 | 运营按场景开关模块 |
| P3 | ASSESSMENT 场景模块 | 测验/评估流 |

---

## 14. 硬编码风险清单

| ID | 位置 | 内容 | 建议 |
|----|------|------|------|
| T-H1 | `learning_engine.py:161` | `mastery_level: 50` | 读掌握度服务 |
| T-H2 | `builder.py:230-241` | 苏格拉底 + Mermaid 全文 | 模板表或 Character 字段 |
| T-H3 | `scaffold.py:56-95` | 脚手架等级规则 | config 或 DB |
| T-H4 | `relationship.py:22-72` | 情感 delta + 阶段阈值 | L2 规则表 |
| T-H5 | `learning.py:71-77` | 五阶段 greeting 模板 | 优先 `Character.greeting` |
| T-H6 | `learning.py:58-67` | EXPRESSION_MAP | 可迁前端或配置 |
| T-H7 | `course_intent.py` 标签映射 | 枚举中文 | 与 Course 表单文档同步 |
| T-H8 | `SceneConfig.MODULE_CONFIGS` | 模块列表 | 长期场景配置表 |
| T-H9 | `course_generator` prompt | 全文模板 | 版本化 prompt 资产 |

---

## 15. 与总览及其他子系统交叉引用

| 链路 | 本系统责任 |
|------|-----------|
| 画像 → 教学 | §8 StrategyModule 等 |
| 教学 → 学习 | §3 主编排返回 `ChatResponse` |
| 教学 → 记忆 | 步骤 13 `extract_and_store` |
| 记忆 → 教学 | `MemoryFactsModule` + `RecallContext` |
| 概念关联 | §6 + Recall（待 `current_topic`） |

---

*文档基于 `learning_engine.py`、`prompt_builder/*`、`teaching_planner.py`、`course_generator.py`、`api/routes/learning.py`、`api/routes/textbook.py` 及关联测试代码勘探生成，2026-06-20。*
