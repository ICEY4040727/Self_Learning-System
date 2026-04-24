# 系统一：记忆系统 — 详细设计

> **版本**：v1.0.2
> **日期**：2026-04-24
> **状态**：设计中

---

## 一、问题

记忆系统已经有基本的数据管道（提取→存储→检索），但存在 8 个问题。按对"越学越会"目标的阻碍程度排序：

| 编号 | 问题 | 阻碍 | 说明 |
|------|------|------|------|
| M4 | 无记忆去重 | **高** | LLM 在多轮对话中重复写入相似记忆，噪声淹没信号 |
| M3 | salience 是静态的 | **高** | 写入后从不变化，无法反映"哪些记忆真正活跃" |
| M1 | chat_messages 硬编码 30 条 | **中** | Token 超限时 context 爆炸；Token 不足时浪费空间 |
| M6 | 记忆提取散落在 learning_engine | **中** | 不利于维护，含冗余查询 |
| M8 | 只支持文本模糊搜索 | **中** | 无法按 concept_tags 精确匹配 |
| M2 | recall_count 从未更新 | **低** | 死代码，M3 的修复依赖它 |
| M5 | expires_at 未接入 | **低** | 过期记忆不清理 |
| M7 | ChatMessage 写入在 API 层 | **低** | 可接受，不改 |

**设计目标**：修复 M1-M6、M8（M7 不改），让记忆系统成为**单一入口**，一次到位。

---

## 二、方案：MemoryManager

**核心思想**：新建 `MemoryManager`，作为记忆系统的唯一入口。所有外部调用方（learning_engine、MemoryFactsModule）统一走 MemoryManager。不做"分阶段迁移"——一步到位。

### 2.1 为什么不是"包装层"

包装层意味着"原接口保留，新接口可选"。这制造双入口问题：有人走新路径，有人走旧路径，行为不一致。

正确做法：MemoryManager 是记忆系统的 Service Layer。`memory_facts_service` 和 `memory_extractor` 降为内部实现细节，外部不再直接调用。

```
改造前（两条路径）：
  learning_engine → memory_facts_service.write_memory_facts()
  MemoryFactsModule → memory_facts_service.retrieve_memories()
  learning_engine → memory_extractor.extract()

改造后（单一入口）：
  learning_engine → MemoryManager.extract_and_store()
  MemoryFactsModule → MemoryManager.retrieve()
  所有外部调用方 → MemoryManager.*
```

### 2.2 接口

```python
class MemoryManager:
    """记忆系统 — 唯一对外入口"""

    def __init__(self):
        self._facts = memory_facts_service      # 内部实现
        self._extractor = memory_extractor      # 内部实现

    # ---- 工作记忆（chat_messages）----

    def get_working_context(
        self, db: Session, session_id: int, *,
        max_tokens: int = 4000,
        max_messages: int = 50,
    ) -> list[dict]:
        """
        获取对话上下文，替代 learning_engine 中硬编码 30 条的查询。
        max_tokens 由调用方（PromptBuilder）分配。
        """
        ...

    # ---- 长期记忆（MemoryFact）----

    def retrieve(
        self, db: Session, character_id: int, *,
        world_id: int | None = None,
        fact_types: list[str] | None = None,
        concept_tags: list[str] | None = None,
        limit: int = 10,
    ) -> list[MemoryFact]:
        """
        检索记忆（供 PromptBuilder 注入上下文）。
        按 effective_salience 降序返回。
        每次调用更新 recall_count + last_recalled_at（M2）。
        """
        ...

    def observe_recent(
        self, db: Session, character_id: int, *,
        fact_types: list[str] | None = None,
        since: datetime | None = None,
        limit: int = 20,
    ) -> list[MemoryFact]:
        """
        观察近期记忆（供叙事引擎、成就系统使用）。
        与 retrieve 的区别：不更新 recall_count（观察不影响记忆状态）。
        按时间倒序，不做 salience 过滤。
        """
        ...

    def write_facts(
        self, db: Session, character_id: int, world_id: int | None,
        memories: list[dict], *,
        source_message_id: int | None = None,
    ) -> list[int]:
        """
        写入记忆（含去重，M4）。
        """
        ...

    # ---- 记忆提取 ----

    def extract_and_store(
        self, db: Session, llm_response: str, *,
        character_id: int,
        world_id: int | None,
    ) -> ExtractionResult:
        """
        从 LLM 回复提取记忆并存储。
        替代 learning_engine 中散落的提取逻辑（M6）。
        """
        ...

    # ---- 记忆维护 ----

    def compute_effective_salience(self, fact: MemoryFact) -> float:
        """计算动态 salience（M3）"""
        ...

    def cleanup_expired(self, db: Session) -> int:
        """清理过期记忆（M5）"""
        ...
```

**接口精简说明**：

| 取舍 | 理由 |
|------|------|
| `retrieve` 更新 recall_count，`observe_recent` 不更新 | 两个方法职责清晰：retrieve 是"使用记忆"，observe_recent 是"观察记忆"（叙事引擎、成就系统）。一次到位。 |
| 去重始终启用，无开关 | 去重是系统行为，不给调用方选择权 |
| 去重简化为"同 type merge，不同 type 写入" | 见 §2.3 |

### 2.3 去重策略（M4）

**核心规则**：同 fact_type + 同 concept_tags 的重复 → merge；不同 fact_type → 一定写入。

```
对每条待写入记忆：
  1. 查询近 24h 内同 character_id + 同 fact_type + concept_tags 有交集的 MemoryFact
  2. 如果命中 → 更新已有记录的 content、salience（取较高值）
  3. 如果未命中 → 正常写入
  4. concept_tags 为空时 → 用 content 前 100 字符做模糊匹配

关键：不同 fact_type 永远不去重。
  concept_struggle(递归) 和 concept_mastered(递归) 是不同状态，必须共存。
```

**为什么不用更复杂的语义相似度**：LLM 每次提取的记忆措辞差异很大，精确匹配不可行。但 concept_tags 是 LLM 被约束输出的结构化字段，它是稳定的语义锚点。24h 窗口限制范围，避免误杀。

### 2.4 Effective Salience（M3）

```
effective = base_salience * retention

retention = exp(-adjusted_decay * hours / 24)

adjusted_decay = base_decay * type_multiplier / (1 + recall_count * 0.5)
```

**type_multiplier**（按 fact_type 差异化衰减）：

| fact_type | multiplier | 理由 |
|-----------|-----------|------|
| concept_struggle | 0 | 困难标记不衰减，持续提醒系统 |
| concept_mastered | 0.3 | 已掌握的知识缓慢衰减 |
| preference | 0 | 学习偏好稳定，不衰减 |
| student_state | 1.5 | 临时状态，快速刷新 |
| event | 0.8 | 历史事件适度衰减 |
| commitment | 0.5 | 承诺较稳定 |

**设计意图**：
- struggle/preference 不衰减（multiplier=0 → retention=1），因为它们是"系统应该记住"的信号
- student_state 快速衰减，因为"今天头疼"不应影响一个月后的教学
- 所有参数可配置（存在 config 中），不硬编码

### 2.5 概念标签（concept_tags）来源

RecallContextModule 需要"学树遍历时关联递归"——前提是两个知识点的 concept_tags 有交集。concept_tags 不是凭空产生的，它有两个来源：

| 来源 | 何时产生 | 质量等级 |
|------|---------|---------|
| **教材结构**（首选） | 上传教材时，由 LLM 从章节标题/知识点列表提取 | 高——教材是 ground truth |
| **LLM 提取**（兜底） | 对话中由 LLM 在 `<memory>` 标签内输出 | 中——依赖 prompt 质量 |

**教材标签提取**（本次不实现，但接口预留）：
```
教材上传 → LLM 分析章节结构 → 提取 {chapter, section, concept_tags}
→ 存入 Course.metadata.concept_map
→ 创建 Step 时关联 concept_tags
→ RecallContextModule 可据此做跨 Step 关联
```

**当前阶段**：RecallContextModule 使用 LLM 提取的 concept_tags。但这是自引用的（LLM 产出 tags → LLM 消费 tags 做关联）。因此 RecallContextModule 的 MVP 实现应该把"关联"降级为简单的 concept_tags 字符串匹配，不做语义推理。

### 2.6 提取质量保证（双通道提取）

"学习 → 记忆"是闭环中最薄弱的环节。如果 LLM 没有输出 `<memory>` 标签，整个闭环就断了。不能只靠 prompt 契约，需要结构性兜底。

**双通道提取**：

```
通道 1（主）：LLM 在回复中主动输出 <memory> 标签
  - 优点：语义丰富，可输出任意 fact_type
  - 缺点：依赖 prompt 质量，LLM 可能忘记输出
  - 触发：MemoryManager.extract_and_store(llm_response)

通道 2（兜底）：从学生消息中结构化提取信号
  - 优点：学生消息是确定性的输入，不依赖 LLM
  - 缺点：只能提取有限类型
  - 触发：MemoryManager.extract_student_signals(student_message)
```

**通道 2 的提取规则（纯规则，不调 LLM）**：

| 信号类型 | 规则 | 产出 |
|---------|------|------|
| 困惑信号 | 学生消息包含 "不懂"/"没看明白"/"什么意思"/"？" 密度 > 30% | concept_struggle（concept_tags 取最近提及的概念） |
| 理解信号 | 学生消息包含 "明白了"/"懂了"/"原来如此"/"学会了" | concept_mastered |
| 情绪信号 | 学生消息包含 "好难"/"崩溃"/"累了" | student_state(negative) |
| 偏好信号 | 学生消息包含 "能举个例子吗"/"能详细讲讲步骤吗" | preference(example_first/step_by_step) |

**合并逻辑**：通道 1 和通道 2 的结果合并后统一进入去重（§2.3）。如果通道 1 已经产出了同类型同 concept_tags 的记忆，通道 2 的结果被去重吞掉（不重复写入）。

**为什么通道 2 是必要的**：它保证闭环不会因为 LLM 忘记输出 `<memory>` 而完全断裂。即使通道 1 失效，通道 2 至少能提取基本的 struggle/mastered 信号——这是 ProfileAggregator 和 GamificationEngine 最核心的输入。

### 2.7 提取 prompt 契约

通道 1 的质量取决于 PromptBuilder 的 system_prompt。这是 MemoryManager 和 PromptBuilder 的**共同契约**：

```
PromptBuilder 必须在 system_prompt 中包含：
  1. 何时提取记忆（概念理解变化、偏好信号、情感变化）
  2. 输出格式：<memory>{"memories": [...]}</memory>
  3. fact_type 枚举和含义
  4. concept_tags 的输出约束（与教材 concept_map 对齐）
  5. 高质量提取的示例（few-shot）

MemoryManager 的 extract_and_store() 负责：
  1. 解析 <memory> 标签
  2. 验证 fact_type / concept_tags 格式
  3. 与通道 2 合并 → 去重 → 写入
```

**prompt 篇幅竞争**：PromptBuilder 同时承担教学质量和记忆提取，两者竞争篇幅。缓解措施：
- 提取指令放在 system_prompt 的固定位置（不是动态注入），减少 token 波动
- 通道 2 兜底意味着即使提取指令被压缩，核心信号不会丢失

### 2.8 提取触发修复

```python
# 当前（有 bug）：
def should_extract_memory(llm_response: str) -> bool:
    clean_text = strip_memory_tags(llm_response)
    return len(clean_text.strip()) > 20  # 即使没有 <memory> 标签也返回 True

# 修复：
def should_extract_memory(llm_response: str) -> bool:
    clean_text = strip_memory_tags(llm_response)
    return len(clean_text.strip()) > 20 and '<memory>' in llm_response
```

---

## 三、改造清单

一次性改造，不留旧路径：

| 文件 | 改动 | 说明 |
|------|------|------|
| `memory_manager.py` | **新建** ~150 行 | 唯一对外入口 |
| `learning_engine.py` | **改** ~15 行 | L165-183、L228-256 改调 MemoryManager |
| `prompt_builder/modules/memory_facts.py` | **改** ~5 行 | 改调 MemoryManager.retrieve() |
| `memory_extractor.py` | **改** 1 行 | should_extract_memory 加标签检查 |
| `memory_facts.py` | **不改** | MemoryManager 内部调用 |
| `alembic/versions/` | **新增** | 添加索引（见下方） |

**索引（随代码一起创建）**：

```sql
CREATE INDEX idx_memory_facts_retrieve
  ON memory_facts (character_id, fact_type, salience DESC);
CREATE INDEX idx_memory_facts_dedup
  ON memory_facts (character_id, fact_type, created_at DESC);
```

---

## 四、闭环中的位置

记忆系统是闭环的**起点和终点**：

```
[记忆] ──→ [画像] ──→ [教学] ──→ [学习] ──→ [新记忆] ← 回到起点
   ↑                                         |
   +──── RecallContext 关联已有记忆 ←─────────+
```

**关键约束**：
- 闭环中"学习 → 新记忆"是最薄弱的环节（依赖 LLM 输出 `<memory>` 标签，无结构化兜底）
- "教学 → 学习"同样隐式（依赖 prompt 质量，无独立度量）
- 架构提供了正确的数据流，但闭环效果的上限由 prompt 工程决定

## 五、记忆流向（改造后）

```
[对话]
  │
  ├─ 学生消息 ──┬→ DynamicAnalyzer（情感分析）──→ LearnerProfile
  │             └→ MemoryManager.extract_student_signals() [通道2，规则提取]
  │                    ↓
  │                 struggle/mastered/preference 信号
  │
  ├─ AI 回复 ──→ MemoryManager.extract_and_store() [通道1，LLM提取]
  │                │
  │                ├─ should_extract_memory() 检查
  │                ├─ memory_extractor.extract() 提取 <memory> 标签
  │                ├─ 与通道2结果合并
  │                └─ write_facts() 写入（含去重）
  │
  ├─ 构建上下文 ──→ MemoryManager.get_working_context(max_tokens)
  │                 └─ 按 Token 预算截断对话历史
  │
  └─ 注入记忆 ──→ MemoryManager.retrieve()
                   ├─ compute_effective_salience() 排序
                   └─ 更新 recall_count
```

---

## 六、测试

| 测试 | 验证什么 |
|------|---------|
| test_write_facts_same_type_merge | 同 fact_type + 同 tags → merge，不新建 |
| test_write_facts_different_type_keep | 不同 fact_type + 同 tags → 两条都保留 |
| test_write_facts_no_tags_fallback | concept_tags 为空时用 content 匹配 |
| test_effective_salience_decay | 衰减公式正确，recall_count 减缓衰减 |
| test_salience_no_decay_struggle | concept_struggle 不衰减 |
| test_retrieve_updates_recall_count | retrieve 后 recall_count +1 |
| test_should_extract_requires_tag | 无 `<memory>` 标签时不触发 |
| test_student_signal_confusion | "不懂" → concept_struggle |
| test_student_signal_mastery | "明白了" → concept_mastered |
| test_dual_channel_merge | 通道1+通道2 同类型被去重合并 |
| test_dual_channel_different | 通道1有但通道2无 → 通道1保留 |
| test_extract_and_store_e2e | 完整提取→去重→写入 |
| test_learning_engine_uses_manager | learning_engine 正确委托 MemoryManager |
| test_memory_facts_module_uses_manager | MemoryFactsModule 走 MemoryManager |

---

## 七、实施步骤

```
Step 1: 新建 memory_manager.py（所有方法）
Step 2: 改造 learning_engine.py（2 处改调）
Step 3: 改造 MemoryFactsModule（1 处改调）
Step 4: 修复 should_extract_memory
Step 5: 添加索引 migration
Step 6: 编写测试，运行确认不回归
```

---

## 八、风险

| 风险 | 回退 |
|------|------|
| 去重误杀 | 24h 窗口可调短；worst case 记忆缺失不影响对话 |
| salience 公式不准 | 参数可配置，公式可替换 |
| Token 预算不准 | max_messages 兜底 |
| 提取 prompt 质量不足 | 通道 2 兜底保证核心信号不丢失 |
| concept_tags 无 ground truth | 有 concept_map 时关联，无则跳过（不做模糊匹配） |
