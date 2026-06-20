# 01 记忆系统 — 详细设计

> **版本**：v1.0.4  
> **日期**：2026-06-20  
> **状态**：已落地（核心链路可用，向量检索与部分运维能力待补）  
> **上级文档**：[四大系统闭环架构设计 — 总览](WholeDesign.md)

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

记忆系统负责在学习对话全生命周期内，**采集、存储、检索、衰减**关于学生的认知事实，并为教学 Prompt 构建、画像聚合、叙事触发、掌握度追踪提供统一事实源。

设计替代关系：P1 #183 起，**`MemoryFact` 表 + `MemoryManager` 服务** 取代早期 `Knowledge` 节点与 ChromaDB 向量检索方案（ChromaDB 仍为架构债，当前未接入）。

### 1.2 系统边界

| 范围内 | 范围外 |
|--------|--------|
| `memory_facts` 长期记忆 CRUD（经 `MemoryManager`） | `LearnerProfile` 维度聚合逻辑（属学习画像系统） |
| `chat_messages` 工作记忆裁剪 | LLM 情感分析（属 `DynamicAnalyzer`） |
| 双通道记忆提取（LLM 标签 + 规则关键词） | 掌握度数值演算（属 `MasteryTracker`） |
| Seed Memory 初始化 | 叙事/成就规则匹配（属叙事系统，只读记忆） |
| Prompt 注入模块 `MemoryFactsModule` / `RecallContextModule` | 误解结构写入（当前存 `LearnerProfile.misconceptions`，非 MemoryFact） |
| 存档 `memory_snapshot` 快照 | 向量语义检索（未实现） |

### 1.3 核心设计约束

1. **单一入口**：外部经 [`memory_manager.py`](../../backend/services/memory_manager.py)（[`learning_engine.py:236`](../../backend/services/learning_engine.py#L236)、[`narrative_engine.py:125`](../../backend/services/narrative_engine.py#L125)），禁止绕过。
2. **观察者只读**：[`memory_manager.py:166`](../../backend/services/memory_manager.py#L166) `observe_recent()`；叙事 [`narrative_engine.py:42`](../../backend/services/narrative_engine.py#L42)。
3. **世界隔离**：[`memory_manager.py:125-128`](../../backend/services/memory_manager.py#L125-L128)、[`:188-190`](../../backend/services/memory_manager.py#L188-L190)；Seed [`memory_facts.py:90`](../../backend/services/memory_facts.py#L90)。
4. **数据驱动**：[`config.py:85-92`](../../backend/core/config.py#L85-L92)、[`:74-83`](../../backend/core/config.py#L74-L83)；检索 [`memory_manager.py:94`](../../backend/services/memory_manager.py#L94)。

### 1.4 实现进度量化

| 模块 | 代码行数 | 测试文件 | 稳定性 |
|------|---------|---------|--------|
| [`memory_manager.py`](../../backend/services/memory_manager.py) | 449 | `test_memory_manager.py` | A |
| [`memory_facts.py`](../../backend/services/memory_facts.py) | 254 | `test_memory_facts.py` | A |
| [`memory_extractor.py`](../../backend/services/memory_extractor.py) | 235 | manager 测试 | A |
| [`recall_service.py`](../../backend/services/recall_service.py) | 124 | 部分测试 | C（**B01**） |
| Prompt 模块（memory_facts / recall_context / episode） | 232 | `test_prompt_builder.py` | B |
| **合计** | **~1,294** | — | **B+（~85%）** |

---

## 2. 三层记忆模型

记忆系统在实现上分为三个互补层，对应认知科学中的工作记忆 / 长期语义记忆 / 初始化先验：

```
┌─────────────────────────────────────────────────────────────┐
│ L1 工作记忆（Working Memory）                                │
│ 载体：chat_messages                                         │
│ 生命周期：会话内；Token 预算裁剪                              │
│ 入口：MemoryManager.get_working_context()                    │
└───────────────────────────┬─────────────────────────────────┘
                            │ 每轮对话后提取
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ L2 长期记忆（Long-term Memory）                              │
│ 载体：memory_facts                                          │
│ 生命周期：持久；salience 衰减 + expires_at 过期               │
│ 入口：write_facts / retrieve / observe_recent                │
└───────────────────────────┬─────────────────────────────────┘
                            │ 会话 start 时一次性
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ L0 种子记忆（Seed Memory）                                   │
│ 载体：memory_facts（world_id=NULL）                          │
│ 来源：traveler 角色 + learner_profile 先验                   │
│ 入口：memory_facts_service.create_seed_memories()            │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 工作记忆（L1）

| 属性 | 值 |
|------|-----|
| 存储 | `chat_messages` 表，按 `session_id` 隔离 |
| 默认上限 | 50 条消息 **且** 4000 tokens（`learning_system.memory`） |
| 排序 | `timestamp DESC, id DESC` 取候选，再按 Token 预算从新到旧回填 |
| 角色映射 | `user` → `user`，`teacher` → `assistant` |
| 兜底 | 至少保留最新 1 条，即使单条超出 Token 预算 |

**硬编码风险**：Token 估算 `len(content)//3 + 4`，中英混合场景有 ±30% 误差，可接受；若需精确控制应接入 tokenizer（未排期）。

### 2.2 长期记忆（L2）

权威表 `memory_facts`，每条记录代表 Sage 对学生在某一认知维度上的**一条可引用事实**。

### 2.3 种子记忆（L0）

在 `POST /courses/{course_id}/start` 创建会话后，若存在 sage + traveler，调用 `learning_engine.create_seed_memories()`，将角色档案与历史画像统计转为跨世界事实，避免冷启动 Prompt 无上下文。

**触发频率**：每次 `start` 均调用（当前无「仅首次」去重）；若 traveler 不变，可能产生重复 Seed 行——依赖后续 `write_facts` 去重或运营清理。

---

## 3. 记忆分类（fact_type）

当前实现 **6 类** `fact_type`（`memory_extractor.py` 与 `MemoryFactsService` 保持一致）：

| fact_type | 语义 | 典型来源 | salience 衰减 | 参与掌握度 delta |
|-----------|------|---------|--------------|----------------|
| `student_state` | 学生状态、背景、元认知描述 | Seed / Channel-2 情绪 / LLM | 慢（×1.5） | 0 |
| `concept_struggle` | 概念学习困难 | LLM / Channel-2 困惑词 | **不衰减**（×0） | -15 |
| `concept_mastered` | 概念已掌握 | LLM / Channel-2 掌握词 | 较慢（×0.3） | +25 |
| `preference` | 学习偏好 | Seed / Channel-2 / LLM | **不衰减** | 0 |
| `event` | 学习事件、叙事写回 | LLM / NarrativeEngine | 中（×0.8） | 0 |
| `commitment` | 学习承诺、约定 | LLM | 中（×0.5） | 0 |

**与理论文档映射**（`docs/learning_memory_theory.md`）：6 类 fact_type 是工程化精简版，覆盖 ITS 覆盖模型（mastered/struggle）、情景事件（event）、元认知/偏好（student_state/preference），**误解（misconception）当前存于 `LearnerProfile` JSON，未建模为 MemoryFact**。

### 3.1 concept_tags 规范

| 规则 | 说明 |
|------|------|
| 类型 | `JSON` 字符串数组，最多 5 个（提取器截断） |
| 课程概念 | 与 `Course.meta.concept_map.nodes[].id` 对齐，供 `RecallService` 精确匹配 |
| Channel-2 哨兵 | `__channel2_confusion__` 等，用于去重；**故意不 Feed 掌握度**（`learning_engine` TODO-T8） |
| 空标签 | 允许，但无法参与 tag 去重与概念关联 |

**硬编码风险**：哨兵标签前缀 `__channel2_*` 写死在 `memory_manager._extract_student_signals`；新增 Channel-2 信号类型需改代码。

---

## 4. 数据模型

### 4.1 `memory_facts` 表

```sql
-- 逻辑字段摘要（详见 backend/models/models.py MemoryFact）
id                  INTEGER PK
character_id        INTEGER FK → characters.id  -- Sage 角色（记忆归属「哪位老师对学生的认知」）
world_id            INTEGER FK nullable         -- NULL = 跨世界事实
subject_id          VARCHAR(50) nullable        -- 预留，当前少用
fact_type           VARCHAR(30) NOT NULL
content             TEXT NOT NULL               -- 写入时截断 500 字
concept_tags        JSON                        -- 标签数组
source_message_id   INTEGER nullable            -- 溯源 ChatMessage.id（AI 回复）
salience            FLOAT default 0.5           -- [0.1, 1.0]
created_at          DATETIME
last_recalled_at    DATETIME
recall_count        INTEGER default 0
expires_at          DATETIME nullable           -- 到期后 retrieve/observe 不可见
t_valid             DATETIME nullable           -- 事实生效时刻
t_invalid           DATETIME nullable           -- 事实失效/纠正时刻（列已建，写入链路未产品化）
```

**索引**：migration `2026_04_25_memory_idx` 对 `(character_id, fact_type, created_at)` 等建索引。

### 4.2 `chat_messages` 关联字段

| 字段 | 用途 |
|------|------|
| `emotion_analysis` | 用户消息情感，供画像 `engagement` 维度，非记忆表字段 |
| `used_memory_ids` | 设计上记录本轮检索命中的 MemoryFact ID；**当前实现存的是 fact_type 列表（缺陷）** |

### 4.3 跨世界语义

| 操作 | world_id 策略 |
|------|--------------|
| Seed 写入 | 恒为 `NULL` |
| 对话提取写入 | 当前 `session.world_id` |
| `retrieve` / `observe_recent` | `world_id = W OR NULL` |
| 画像聚合（`ProfileAggregator`） | **不过滤 world**（按 character 跨世界）——与检索策略不一致，见总览 TR-C1 |

---

## 5. 服务层架构

```
                    ┌─────────────────────┐
                    │   LearningEngine    │
                    │  NarrativeEngine    │
                    │  save.py snapshot   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   MemoryManager     │  ← 唯一外部入口
                    │  (memory_manager)   │
                    └──────────┬──────────┘
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
    ┌─────────────────┐ ┌──────────────┐ ┌──────────────────┐
    │ memory_extractor│ │memory_facts_ │ │  recall_service  │
    │ Channel-1 解析  │ │   service    │ │ 概念前置关联提示  │
    └─────────────────┘ │  裸表 INSERT  │ └──────────────────┘
                          └──────────────┘
```

| 类 / 模块 | 职责 | 对外可见 |
|-----------|------|---------|
| [`MemoryManager`](../../backend/services/memory_manager.py) | 工作记忆 [`:45`](../../backend/services/memory_manager.py#L45)、检索 [`:94`](../../backend/services/memory_manager.py#L94)、写入 [`:255`](../../backend/services/memory_manager.py#L255) | **是** |
| [`MemoryFactsService`](../../backend/services/memory_facts.py) | INSERT [`:44`](../../backend/services/memory_facts.py#L44)、Seed [`:90`](../../backend/services/memory_facts.py#L90) | 否 |
| [`MemoryExtractor`](../../backend/services/memory_extractor.py) | 解析 [`:44-52`](../../backend/services/memory_extractor.py#L44-L52)、strip [`:58-66`](../../backend/services/memory_extractor.py#L58-L66) | 否 |
| [`RecallService`](../../backend/services/recall_service.py) | DAG [`:26-55`](../../backend/services/recall_service.py#L26-L55) | 是 |

---

## 6. 写入路径

### 6.1 主编排时序（每轮 chat）

```
process_message()
  ├─ [构建 Prompt] memory_manager.retrieve()  ← 读，更新 recall_count
  ├─ [LLM 调用]
  └─ [写记忆] memory_manager.extract_and_store()
        ├─ Channel-1: extract_memories(llm_response) → write_facts()
        └─ Channel-2: _extract_student_signals(user_message) → write_facts()
```

### 6.2 Channel-1：LLM 标签提取

**契约格式**（须写入 Sage system prompt 或教师模板）：

```xml
<memory>{"memories": [
  {
    "fact_type": "concept_mastered",
    "content": "学生理解了递归基线条件",
    "concept_tags": ["recursion_base_case"],
    "salience": 0.8,
    "expires_at": null
  }
]}</memory>
```

| 校验规则 | 行为 |
|---------|------|
| 无 `<memory>` 标签 | 返回空列表，不报错 |
| JSON 非法 | 记录 warning，丢弃整批 |
| 未知 `fact_type` | 降级为 `event` |
| `content` 空 | 跳过该条 |
| `salience` 非数字 | 默认 0.5，clamp 至 [0.1, 1.0] |
| `concept_tags` 非数组 | 置 `[]` |

返回用户可见文本前，调用 `strip_memory_tags()` 移除标签块。

### 6.3 Channel-2：规则关键词提取

配置源：[`config.py:74-83`](../../backend/core/config.py#L74-L83) `learning_system.extraction`。

| 信号 | 触发词示例 | 写入 fact_type | 哨兵 tag |
|------|-----------|---------------|---------|
| 困惑 | 不懂、不明白… | `concept_struggle` | `__channel2_confusion__` |
| 掌握 | 明白了、懂了… | `concept_mastered` | `__channel2_mastery__` |
| 负面情绪 | 好难、崩溃… | `student_state` | `__channel2_negative_emotion__` |
| 偏好 | 举个例子、一步一步… | `preference` | `__channel2_preference_{key}__` |

开关：`extraction.channel2_enabled`（默认 `true`）。

**设计决策**：掌握度排除 Channel-2 — [`learning_engine.py:277-283`](../../backend/services/learning_engine.py#L277-L283)；Channel-2 写入 [`memory_manager.py:291-371`](../../backend/services/memory_manager.py#L291-L371)。

### 6.4 去重合并（M4）

[`write_facts()`](../../backend/services/memory_manager.py#L205-L243) 在 [`config.py:61`](../../backend/core/config.py#L61) `dedup_window_hours` 内查找：

- 相同 `character_id`
- 相同 `fact_type`
- `concept_tags` 有交集（JSON `contains` 子串匹配）

命中则**更新** `content` 与 `max(salience)`，不新增行；无 tag 时跳过去重。

### 6.5 Seed Memory 清单

| 来源字段 | fact_type | salience | world_id |
|---------|-----------|----------|----------|
| `traveler.name` | student_state | 0.9 | NULL |
| `traveler.tags` | preference | 0.7 | NULL |
| `world_background` / `background` | student_state | 0.6 | NULL |
| `personality` | preference | 0.5 | NULL |
| `learning_stats.total_sessions` | student_state | 0.8 | NULL |
| `learning_stats.average_mastery` | concept_mastered | 0.85 | NULL |
| `preference_stability.*` | preference | 0.75 | NULL |
| `metacognition_trend.*` | student_state | 0.6 | NULL |

---

## 7. 读取路径

### 7.1 `retrieve()` — Prompt 注入用

| 参数 | 默认 | 说明 |
|------|------|------|
| `character_id` | 必填 | Sage ID |
| `world_id` | 可选 | 启用世界过滤 |
| `fact_types` | 无 | 类型白名单 |
| `concept_tags` | 无 | 标签 AND 过滤 |
| `limit` | 10（模块内覆写为 8） | 返回条数上限 |
| `min_salience` | 0.3 | 基于 **effective_salience** 过滤 |

**算法**：

1. SQL 预筛：`salience >= min_salience`、未过期、world 过滤，取 `limit × 5` 候选
2. 计算 `effective_salience`（见 §8）
3. 过滤 + 降序排序，截断 `limit`
4. 更新命中行的 `recall_count++`、`last_recalled_at`

### 7.2 `observe_recent()` — 观察者用

与 `retrieve()` 区别：

| 对比项 | retrieve | observe_recent |
|--------|----------|----------------|
| 排序 | effective_salience DESC | created_at DESC |
| recall 副作用 | **有** | **无** |
| 默认 limit | 10 | 20 |
| 时间窗 | 无 | 可选 `since` |

调用方：`NarrativeEngine`、`GamificationEngine`、`RecallService`、`ProfileAggregator._keyword_extract`。

### 7.3 `get_working_context()` — 对话历史

见 §2.1；在 `process_message` 第 8 步调用，结果 append 当前用户消息后送 LLM。

---

## 8. 有效显著度（effective_salience）

公式（`memory_manager.compute_effective_salience`）：

```
multiplier = salience_type_multiplier[fact_type]  # 0 表示不衰减
adjusted_decay = salience_base_decay × multiplier / (1 + recall_count × salience_recall_factor)
retention = exp(-adjusted_decay × hours_elapsed / 24)
effective_salience = salience × retention
```

| fact_type | multiplier（默认） | 含义 |
|-----------|-------------------|------|
| concept_struggle | 0.0 | 困难事实长期保留 |
| concept_mastered | 0.3 | 掌握事实慢衰减 |
| preference | 0.0 | 偏好不衰减 |
| student_state | 1.5 | 状态事实快衰减 |
| event | 0.8 | |
| commitment | 0.5 | |

**参数源**：`config.py` → `learning_system.memory` + `salience_type_multiplier`（L1）。

---

## 9. Prompt 注入模块

| 模块 | 优先级 | 数据源 | 与记忆系统关系 |
|------|--------|--------|--------------|
| `MemoryFactsModule` | 70 | `memory_manager.retrieve(limit=8)` | **核心**：格式化【学生认知记忆】 |
| `RecallContextModule` | 75 | `recall_service.get_recall_hints()` | 概念 DAG 前置提示 |
| `EpisodeModule` | 40 | `LearnerProfile.episodes` | 情景摘要，非 MemoryFact |
| `MisconceptionModule` | 30 | `LearnerProfile.misconceptions` | 误解追踪，非 MemoryFact |

### 9.1 MemoryFactsModule 输出格式

```
【学生认知记忆】
- [困难] 学生在递归上遇到困难...
- [掌握]* 学生理解了基线条件...
```

- `*` 表示 `salience >= 0.8`
- 单条 content 展示截断 100 字

### 9.2 RecallService（概念关联）

**前置条件**：

1. `Course.meta.concept_map` 存在 `nodes` + `edges`
2. `current_topic` 为图中节点 `id`
3. 存在 `requires` 边指向前置概念

**逻辑**：查前置概念的 `concept_struggle` / `concept_mastered` 标签集合，生成自然语言复习提示。

**断裂点（P0）**：`learning_engine` 构建 context 时**未设置 `current_topic`**，导致生产环境 `RecallContextModule` 恒为空。修复：从 `TeachingPlanner.get_current_lesson()` 取当前课首概念写入 context。

---

## 10. 下游系统集成

| 消费方 | 读/写 | 接口 | 耦合强度 |
|--------|------|------|---------|
| 学习画像 · `ProfileAggregator` | 读 | `observe_recent` / SQL count | 强 |
| 学习画像 · `MasteryTracker` | 读 | 本轮 `extract_and_store` 返回的 facts | 强（仅 Channel-1） |
| 叙事 · `NarrativeEngine` | 读+写 | `observe_recent` / `write_facts(event)` | 中 |
| 叙事 · `GamificationEngine` | 读 | `recent_facts` 参数 | 中 |
| 教学 · `PromptBuilder` | 读 | `retrieve` / `RecallService` | 强 |
| 存档 · `save.py` | 读 | 快照 top-50 by salience | 中 |

### 10.1 记忆 → 画像（出口）

`ProfileAggregator` 按 `profile_dimension_defs.source_fact_types` 统计 MemoryFact，**不按 world_id 过滤**（TR-C1）。Channel-2 哨兵事实计入分母，可能稀释 `ratio` 类维度——v1.0.5 可考虑聚合时 `WHERE concept_tags NOT LIKE '%__channel2_%'`。

### 10.2 记忆 → 掌握度（出口）

仅 `extract_and_store` 返回的 Channel-1 `ExtractedMemory` 对象传入 `mastery_tracker.update_from_memories()`；Channel-2 已写入 DB 但不影响掌握度。

---

## 11. 存档与恢复

### 11.1 快照结构（`save.py`）

```json
{
  "memory_snapshot": {
    "memory_ids": [1, 2, 3],
    "facts": [
      {"id": 1, "fact_type": "concept_struggle", "content": "...", "salience": 0.7}
    ]
  }
}
```

- 选取：`sage_character_id` + `world_id` 过滤，按 `salience DESC`，最多 **50** 条
- 跨世界事实（`world_id=NULL`）包含在内

### 11.2 恢复策略

读档时恢复 `chat_history`、`relationship`、`learner_profile_snapshot`；**MemoryFact 行本身不因读档回滚**（事实库向前累积）。快照主要用于 UI 展示与审计，非时间旅行。

---

## 12. 接口契约

### 12.1 内部服务 API（Python）

#### `MemoryManager.get_working_context(db, session_id, *, max_messages=None) → list[dict]`

| 项 | 说明 |
|----|------|
| 返回 | `[{"role": "user"|"assistant", "content": str}, ...]` 时间正序 |
| 异常 | 无会话消息时返回 `[]` |

#### `MemoryManager.retrieve(db, character_id, *, world_id=None, fact_types=None, concept_tags=None, limit=None, min_salience=0.3) → list[MemoryFact]`

| 项 | 说明 |
|----|------|
| 副作用 | 更新返回事实的 `recall_count`、`last_recalled_at` |
| 过期 | `expires_at < now` 不可见 |

#### `MemoryManager.observe_recent(db, character_id, *, world_id=None, fact_types=None, since=None, limit=None) → list[MemoryFact]`

| 项 | 说明 |
|----|------|
| 副作用 | **无** |

#### `MemoryManager.write_facts(db, character_id, world_id, memories, *, source_message_id=None) → list[int]`

| 项 | 说明 |
|----|------|
| `memories[]` 字段 | `fact_type`, `content`, `concept_tags?`, `salience?`, `expires_at?`, `t_valid?` |
| 返回 | 写入或合并后的 memory id 列表 |

#### `MemoryManager.extract_and_store(db, llm_response, student_message, *, character_id, world_id, source_message_id=None) → ExtractionResult`

| 项 | 说明 |
|----|------|
| 返回 | `ExtractionResult(memories: list[ExtractedMemory], raw_json?, error?)` |
| 说明 | Channel-1 结果在 `.memories`；Channel-2 无返回体 |

#### `MemoryFactsService.create_seed_memories(db, sage_character_id, traveler_character, traveler_world_link=None, learner_profile=None) → list[int]`

| 项 | 说明 |
|----|------|
| 调用时机 | `POST .../start` 创建会话后 |
| world_id | 全部写 `NULL` |

#### `RecallService.get_recall_hints(db, *, character_id, world_id, current_topic=None, course_id=None) → list[str]`

| 项 | 说明 |
|----|------|
| 返回 | 中文提示字符串列表；无条件时 `[]` |

---

### 12.2 HTTP API

#### `GET /api/archive/courses/{course_id}/memory-facts`

查询课程关联世界的记忆事实（经该世界 Sage 角色）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `stats_only` | query bool | `true` 仅返回统计 |

**响应（stats_only=false）**：

```json
{
  "stats": {
    "total": 42,
    "by_type": {"concept_struggle": 10, "concept_mastered": 8},
    "avg_salience": 0.612
  },
  "facts": [
    {
      "id": 1,
      "fact_type": "concept_struggle",
      "content": "…",
      "concept_tags": ["recursion"],
      "salience": 0.7,
      "created_at": "2026-06-20T10:00:00Z",
      "recall_count": 3
    }
  ]
}
```

| 约束 | 值 |
|------|-----|
| 列表上限 | 50 条 |
| content 截断 | 200 字 |
| 权限 | 课程所属 `world.user_id == current_user.id` |

#### `POST /api/learning/courses/{course_id}/chat`（记忆相关字段）

**响应字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `memory_extracted_count` | int | 本轮 Channel-1 提取条数 |
| `used_memory_ids` | list | **当前为 fact_type 列表（待修复为 id 列表）** |

#### `POST /api/learning/courses/{course_id}/start`

副作用：创建 Seed Memory（不单独返回 memory id）。

---

## 13. 可调参数（L1）

配置路径：`backend/core/config.py` → `Settings.learning_system`

### 13.1 `memory` 分组

| 键 | 默认 | 修改影响 |
|----|------|---------|
| `dedup_window_hours` | 24 | 去重时间窗 |
| `max_working_context_tokens` | 4000 | 工作记忆 Token 上限 |
| `max_working_context_messages` | 50 | 工作记忆条数上限 |
| `salience_base_decay` | 0.1 | 全局衰减基底 |
| `salience_recall_factor` | 0.5 | 召回次数抑制衰减 |
| `default_retrieve_limit` | 10 | retrieve 默认条数 |
| `observe_recent_limit` | 20 | observe 默认条数 |

### 13.2 `extraction` 分组

| 键 | 默认 | 修改影响 |
|----|------|---------|
| `channel2_enabled` | true | 关闭则仅 LLM 标签提取 |
| `confusion_keywords` | 中文词表 | Channel-2 困惑触发 |
| `mastery_keywords` | 中文词表 | Channel-2 掌握触发 |
| `emotion_negative_keywords` | 中文词表 | Channel-2 情绪触发 |
| `preference_keywords` | dict | Channel-2 偏好触发 |

### 13.3 `salience_type_multiplier`

按 `fact_type` 控制衰减倍率；**新增 fact_type 必须同步添加键**，否则默认 1.0。

### 13.4 关联但非本系统直属

`learning_system.mastery.delta_map` 由 `MasteryTracker` 读取，决定 fact_type 对掌握度的影响。

---

## 14. 运维

### 14.1 过期清理

```bash
cd backend && python -m backend.scripts.cleanup_memories
```

- 删除 `expires_at < now()` 的行
- **无内置定时任务**（v1.0.3 移除 scheduler）；需 cron / 外部编排

### 14.2 监控建议

| 指标 | 查询思路 | 告警阈值建议 |
|------|---------|-------------|
| 表行数增长 | `COUNT(*)` per character | 单角色 > 10k |
| 过期未清理 | `expires_at < now()` count | > 1000 |
| Channel-2 占比 | `concept_tags LIKE '%__channel2_%'` | > 50% 需调关键词 |
| retrieve 空率 | 日志 / 埋点 | 连续 N 轮为空 |

---

## 15. 测试覆盖

| 文件 | 覆盖点 |
|------|--------|
| `test_memory_manager.py` | 去重、衰减、双通道、recall_count、工作记忆 Token 预算 |
| `test_memory_facts.py` | Seed 写入、salience、跨 world_id |
| `test_prompt_builder.py` | MemoryFactsModule 组装 |
| `test_teaching_system.py` | RecallService 图遍历 |
| `test_archive.py` | memory-facts API（间接） |

**缺口**：`RecallContextModule` 与 `learning_engine` 端到端；`used_memory_ids` 契约；`t_invalid` 纠正流；Seed 重复 start 去重。

---

## 16. 已知缺陷与改造路线图

| 优先级 | 项 | 说明 | 目标版本 |
|--------|-----|------|---------|
| **P0** | `current_topic` 未注入 | RecallContext 空转 | v1.0.5 |
| **P0** | `used_memory_ids` 存 fact_type | 溯源失真 | v1.0.5 |
| P1 | Seed 每次 start 重复 | 可能膨胀事实表 | v1.0.5 |
| P1 | `t_invalid` 无写入 API | 纠正链路未闭环 | v1.0.5 |
| P1 | Channel-2 污染画像分母 | 聚合准确率 | v1.0.5 |
| P2 | ChromaDB 向量检索 | 语义召回 | 待定 |
| P2 | `fact_type` 规则表（L2） | 替代 extractor 硬编码枚举 | 待定 |
| P2 | JSON tag `contains` 误匹配 | 换 JSON1 `json_each` | 待定 |
| P3 | 精确 Token 计数 | 工作记忆预算 | 待定 |

---

## 17. 硬编码风险清单

| ID | 位置 | 内容 | 风险 | 建议 |
|----|------|------|------|------|
| M-H1 | `memory_extractor.py:132` | `valid_types` 集合 | 中 | 迁 DB 或 config 枚举表 |
| M-H2 | `memory_manager.py:314-368` | Channel-2 关键词与哨兵 tag | 中 | 迁 `extraction` 配置（部分已迁） |
| M-H3 | `memory_facts.py:210-214` | Seed 偏好 display_name 映射 | 低 | 数据驱动模板 |
| M-H4 | `memory_facts.py:145` | salience 0.9/0.7/… 魔法数 | 低 | 迁 config seed_salience_map |
| M-H5 | `memory_facts.py:209-224` | preference_stability 字段名 | 中 | 与 LearnerProfile 契约统一 |
| M-H6 | 设计文档 | ChromaDB | 高 | 明确延期或 POC 排期 |

---

## 18. 与总览文档的交叉引用

| 总览章节 | 本系统对应 |
|---------|-----------|
| 记忆 → 画像 | §10.1，`ProfileAggregator` 读 MemoryFact |
| 学习 → 记忆 | §6.1，`extract_and_store` |
| 记忆 → 叙事 | §10，`NarrativeEngine` + `write_facts(event)` |
| 概念关联 | §9.2，`RecallService`（待接线） |
| 可调参数 L1 | §13 |
| 可调参数 L3 | §4 `memory_facts` 运行时行 |

---

*文档基于 `backend/services/memory_*.py`、`memory_manager.py`、`recall_service.py`、`api/routes/archive.py`、`api/routes/learning.py`、`api/routes/save.py` 及关联测试文件代码勘探生成，2026-06-20。*
