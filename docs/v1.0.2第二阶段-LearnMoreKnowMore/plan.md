# v1.0.2 第二阶段完整实施方案 — LearnMoreKnowMore

> **版本**：v1.0.2
> **日期**：2026-04-23
> **状态**：讨论中

基于对代码库的深入审查和效果优先级分析，以下是重新编排的第二阶段方案。按每阶段独立可交付的方式组织。

## 概念澄清与架构设计讨论

> 以下讨论基于对代码库的深入追踪，澄清了几个核心概念并提出了系统闭环设计方案。

### 概念纠正：MemoryFact ≠ 全量记忆

**之前讨论中的混淆**：将 MemoryFact 等同于"全量记忆"，混淆了两种完全不同的数据。

**正确定义**：

| 概念 | 是什么 | 存储位置 | 用途 |
|------|--------|---------|------|
| **全量记忆**（Full Context） | 原始对话消息的完整记录 | `chat_messages` 表 | 同一次 Session 内的上下文连续性 |
| **用户画像**（User Profile） | 从对话中抽象出的结构化认知事实 | `memory_facts` 表 + `learner_profiles` 表 | 跨 Session、跨课程的认知继承 |

**全量记忆**：就是 `chat_messages` 表中的所有消息，按 `session_id` 查询后全量注入 API 的 `messages` 参数。在同一次 Session 内，AI 自然记得所有内容，不需要 MemoryFact 补充。

**MemoryFact（用户画像的原子单元）**：是 LLM 从对话中**提取、抽象**出的结构化认知事实。它不是原始对话的复述，而是对"学生是怎样的人、学了什么、怎么学最好"的**精炼总结**。

```
全量记忆（chat_messages）:
  学生: "递归好难理解"
  AI: "让我换个方式解释..."（200字）
  学生: "哦我好像懂了一点"
  AI: "太好了！让我们再试试..."（300字）
  ↓ 约 600 tokens

MemoryFact（抽象画像）:
  fact_type: "concept_struggle"
  content: "递归抽象理解困难，图解辅助后初步理解"
  concept_tags: ["递归", "抽象思维"]
  salience: 0.8
  ↓ 约 30 tokens
```

**两者的关系**：MemoryFact 是全量记忆的"精华压缩版"。100 条对话（~7000 tokens）可能只产出 3 条 MemoryFact（~90 tokens），但能传达"学生在递归上有困难，图解有帮助"这个关键认知。

**MemoryFact 的独特价值**（全量记忆做不到的）：

| 场景 | 全量记忆 | MemoryFact |
|------|---------|-----------|
| 同 Session 内 | ✅ 天然支持 | 冗余但不碍事 |
| 跨 Session 继承 | ❌ 新 Session 没有历史 | ✅ 通过 character_id 检索 |
| 分支间经验互通 | ❌ 各 Session 独立 | ✅ 共享同一个 sage 的记忆 |
| 跨课程了解学生 | ❌ 不同 Course 不同消息 | ✅ 同一个 sage 跨课程 |
| 长期画像积累 | ❌ 消息是原始对话 | ✅ 结构化事实（fact_type + salience） |
| Token 压力大时 | ❌ 要么全发要么丢 | ✅ 精华版注入，几十 token 搞定 |

---

### Token 压缩提示：前端给用户的通知

**场景**：当对话历史过长（超过模型上下文窗口的 80%）时，系统自动压缩旧消息，只保留最近几条 + MemoryFact 摘要。这个压缩过程应该**对用户可见**。

**为什么需要通知用户**：
1. **省钱意识**：有的 API 按上下文长度收费（如 Claude 的 input tokens），压缩后用户的花费更少
2. **理解行为**：用户知道"为什么 AI 突然不记得 100 条之前说的话了"
3. **控制感**：让用户知道系统在帮他优化，而不是偷偷丢数据

**前端 UI 设计**：

```
Learning.vue 对话区域，在压缩发生时插入一条系统消息：

┌─────────────────────────────────────────┐
│ 📦 上下文已压缩                           │
│                                         │
│ 为节省 Token 开销，系统已将前 180 条对话   │
│ 压缩为精华摘要（保留了最近 6 条原文）。     │
│                                         │
│ 你的人品画像已完整保存，知者依然了解你。  │
│                                         │
│ 原始对话: 12,600 tokens                  │
│ 压缩后:   1,200 tokens                  │
│ 节省:     11,400 tokens (90.5%)          │
│                                         │
│ [查看压缩详情]            [知道了]         │
└─────────────────────────────────────────┘
```

**后端返回字段**（在 chat API 响应中）：

```python
{
    "message": {"role": "sage", "content": "..."},
    "context_compression": {  # 仅在压缩发生时存在
        "triggered": true,
        "original_messages": 180,
        "kept_messages": 6,
        "original_tokens": 12600,
        "compressed_tokens": 1200,
        "compression_ratio": 0.905,
        "memory_facts_used": 8,  # 注入了多少条 MemoryFact 作为补偿
    }
}
```

**触发条件**：

```python
# learning_engine.py 中，发送前估算
estimated_tokens = estimate_tokens(system_prompt, messages)
model_limit = llm_adapter.context_window  # 如 200000, 128000, 8192

if estimated_tokens > model_limit * 0.8:
    # 触发压缩：保留最近 N 条 + MemoryFact 摘要
    messages = compress_messages(messages, budget=int(model_limit * 0.6))
    context_compression = build_compression_report(...)
    # 前端收到 context_compression 字段，展示通知
```

**各模型的触发概率**：

| 模型 | 上下文窗口 | 触发压缩的消息数 | 实际发生概率 |
|------|-----------|---------------|------------|
| Claude 3.5 Sonnet | 200K | ~1500 条 | 极低 |
| GPT-4o / DeepSeek | 128K | ~1000 条 | 极低 |
| Qwen Max | 32K | ~200 条 | 低 |
| Llama 3 8B（本地） | 8K | ~40 条 | **高** |

---

### 四大系统闭环设计

> 这是本系统最核心的架构设计：让记忆系统、学习画像、教学策略、游戏化叙事形成一个**自增强闭环**。

#### 当前问题：四大系统各自独立

```
现状：
  记忆系统（MemoryFact）  → 只管存取事实，不影响其他系统
  学习画像（LearnerProfile）→ 只管记录偏好，不被其他系统读取
  教学系统（PromptBuilder）→ 只管构建 prompt，不感知画像变化
  叙事系统（scenes）       → 只是世界观配置，不感知学习状态
```

#### 目标：形成闭环

```
┌─────────────────────────────────────────────────────────────┐
│                        学习对话                               │
│  学生: "递归好难理解"                                         │
│       ↓                                                      │
│  ① 记忆系统提取 MemoryFact                                   │
│     fact_type="concept_struggle"                             │
│     content="递归抽象理解困难"                                 │
│     concept_tags=["递归","抽象思维"]                           │
│     salience=0.8                                             │
│       ↓                                                      │
│  ② 学习画像更新 LearnerProfile                               │
│     metacognition.abstract_thinking -= 0.1                   │
│     preference.visual_learning += 0.1                        │
│     （聚合规则：3 条同类 struggle → 标记为"弱项"）              │
│       ↓                                                      │
│  ③ 教学策略调整 PromptBuilder                                 │
│     ScaffoldContext 读到 abstract_thinking 低                 │
│     → 指令变为"用具体例子和图表辅助讲解"                        │
│     → 下次 AI 老师主动用 Mermaid 图/类比来教                   │
│       ↓                                                      │
│  ④ 叙事+游戏化响应                                           │
│     学生产生困惑 → 叙事事件: "导师察觉到你的困惑"               │
│     relationship.comfort += 0.05                              │
│     → 触发场景联想: 从"函数村庄"调取对应上下文到"积分深渊"         │
│     → 如果连续 3 次 struggle 在同一概念:                       │
│       触发成就 "百折不挠"                                     │
│       触发叙事 "导师决定换一种方式..."                          │
│       ↓                                                      │
│  ⑤ 画像变化再次反馈到记忆                                     │
│     LearnerProfile 变化 → 写入 MemoryFact:                   │
│     fact_type="student_state"                                │
│     content="学习风格转变：从理论偏好转为实践偏好"               │
│     → 下次教学策略自动适应新风格                               │
└─────────────────────────────────────────────────────────────┘
```

#### 需要增强的 5 条连接

| # | 连接 | 当前状态 | 需要做的 | 对应 Phase |
|---|------|---------|---------|-----------|
| 1 | MemoryFact → LearnerProfile | ❌ 无连接 | 定期从 MemoryFact 聚合更新画像（如发现 3 条同类 struggle → 标记为"弱项"；多条 preference → 更新偏好维度） | 2A |
| 2 | LearnerProfile → PromptBuilder | ⚠️ 部分（ScaffoldContext 读 level） | 增强：根据画像的 metacognition 四维度动态调整教学策略（不只是脚手架级别），如 abstract_thinking 低 → 自动加类比 | 2B |
| 3 | MemoryFact → 叙事系统 | ❌ 无连接 | 根据记忆触发叙事事件：连续 concept_struggle → 触发"导师特别关心"剧情；concept_mastered → 触发"概念突破"事件 | 2D |
| 4 | LearnerProfile → 游戏化指标 | ❌ 无连接 | 画像变化映射为游戏指标：abstract_thinking 提升到阈值 → 解锁"抽象思维者"成就；连续学习 N 天 → 好感度提升 | 2E |
| 5 | 叙事事件 → MemoryFact | ❌ 无连接 | 叙事事件也作为 MemoryFact 记录："导师在递归困难时给予了特别鼓励" → 下次对话 AI 自然延续这个叙事 | 2D |

#### 连接 1 详细设计：MemoryFact → LearnerProfile 聚合管道

```python
# backend/services/profile_aggregator.py（新增）

class ProfileAggregator:
    """定期从 MemoryFact 聚合更新 LearnerProfile"""

    def aggregate(self, db, user_id, world_id, character_id):
        facts = db.query(MemoryFact).filter(
            MemoryFact.character_id == character_id,
            MemoryFact.t_invalid.is_(None),
        ).all()

        profile = db.query(LearnerProfile).filter(
            LearnerProfile.user_id == user_id,
            LearnerProfile.world_id == world_id,
        ).first()

        # 聚合规则
        struggles = [f for f in facts if f.fact_type == "concept_struggle"]
        mastered = [f for f in facts if f.fact_type == "concept_mastered"]
        prefs = [f for f in facts if f.fact_type == "preference"]

        # 更新元认知维度（基于 struggle/mastered 的比例）
        total = len(struggles) + len(mastered)
        if total > 0:
            profile.metacognition["abstract_thinking"] = max(0.1, 1.0 - len(struggles) * 0.1)
            profile.metacognition["problem_solving"] = min(1.0, len(mastered) * 0.1)

        # 更新偏好（基于 preference 的内容聚类）
        visual_prefs = [p for p in prefs if "图" in p.content or "视觉" in p.content]
        if len(visual_prefs) >= 2:
            profile.preferences["visual_learning"] = True
```

**调用时机**：每次 Session 结束时（`end_session`）或用户刷新画像时（`POST /user/profile/refresh`）。

#### 连接 3+5 详细设计：叙事 ↔ 记忆双向绑定

```python
# 在 NarrativeEngine.check_triggers() 中：

def check_triggers(self, context, db):
    events = []

    # 读取 MemoryFact 判断是否触发叙事事件
    recent_struggles = db.query(MemoryFact).filter(
        MemoryFact.character_id == context["sage_character_id"],
        MemoryFact.fact_type == "concept_struggle",
        MemoryFact.t_invalid.is_(None),
        MemoryFact.created_at >= datetime.now(UTC) - timedelta(hours=1),
    ).all()

    # 连续 3 次 struggle → 触发"导师换方式"叙事
    if len(recent_struggles) >= 3:
        events.append({
            "type": "struggle_cascade",
            "concepts": [s.concept_tags for s in recent_struggles],
        })
        # 连接 5：叙事事件写回 MemoryFact
        db.add(MemoryFact(
            character_id=context["sage_character_id"],
            fact_type="event",
            content=f"导师在{recent_struggles[0].concept_tags}上连续尝试多种教学方式",
            concept_tags=["叙事事件", "教学策略调整"],
            salience=0.7,
        ))

    return events
```

#### 闭环的最终效果

```
第 1 次学习：AI 用默认策略教，提取了 5 条 MemoryFact
第 2 次学习：AI 根据画像调整风格，发现学生偏好图解，提取了 3 条新记忆
第 5 次学习：画像已经很准确（抽象思维 0.3、动手能力 0.8），AI 策略高度个性化
第 10 次学习：叙事系统积累了丰富的事件记忆，好感度到了"朋友"
               → AI 对话风格从"严谨导师"变为"亲切伙伴"
               → 成就系统解锁了"思维转换者"（抽象思维从 0.1 提升到 0.5）
               → 学生在画像页面看到自己的成长曲线

这就是"越学越会"：不只是 AI 记住更多，而是整个系统越来越懂这个学生。
```

---

## 实施时间线

```
Phase 2A 记忆系统修复（A1-A5）
Phase 2B Prompt 组装策略（B1-B4）
Phase 2C 教材上传+课程生成（C1-C5）
Phase 2D 历险叙事系统（D1-D4）
Phase 2E 游戏化指标（E1-E4）
Phase 2F 语义检索+画像UI（F1-F2）
```

**关键依赖关系**：
- 2B 依赖 2A（Prompt 组装需要新的记忆检索接口）
- 2D 依赖 2B（叙事 Prompt 注入需要新的模块体系）
- 2E 可以和 2C-2D 并行（独立于记忆和叙事）
- 2F 依赖 2A（语义检索需要去重后的干净数据）

---

## 风险与缓解

| 风险 | 概率 | 缓解 |
|------|------|------|
| PDF 解析质量差 | 中 | pymupdf 对中文 PDF 较好；纯文本 fallback |
| LLM 调用成本高 | 中 | 教材解析一次性成本；运行时每轮只多约 50 tokens |
| 去重误判 | 中 | 设置保守阈值，宁可多建不误删；人工 review 接口 |
| 叙事模板不够灵活 | 低 | 用户自定义 + 多个示例模板 |
---

## Phase 2A：记忆系统修复（1.5 周）

> **目标**：修复当前记忆系统的核心缺陷，让"越学越会"真正生效
> **为什么最优先**：记忆是整个系统的地基，当前地基有三个裂缝（无去重、无演化、无时态）

### A1. 记忆提取提示词优化

**文件**：`backend/services/prompt_builder/builder.py` → `build_static_layer()` 末尾追加

**现状**：记忆提取指令隐式嵌入系统提示词，LLM 提取质量不稳定
**改动**：在静态层末尾追加结构化提取指南

```python
# 在 build_static_layer() 的 Socratic Method Rules 之后追加：
parts.append("""【记忆提取规则】
在回复末尾，如果对话中出现以下类型的重要信息，请用 <memory> 标签提取：
1. 概念掌握变化：学生从"不会"到"初步理解"到"掌握"的转变
2. 误解：学生说错了什么、错误模式是什么、严重程度
3. 学习行为模式：学生喜欢/回避什么理解方式
4. 情感转折点：从挫败到突破、从好奇到无聊

不要提取：寒暄内容、重复已知信息、无诊断价值的细节
每条记忆必须包含至少 1 个 concept_tag（关联到具体知识概念）
每条记忆的 content 必须是自包含的（不依赖上下文就能理解）
每轮最多提取 3 条记忆""")
```

**涉及文件**：
- `backend/services/prompt_builder/builder.py`（追加提取指南）

#### 讨论区

**owner** ： 我想知道结构化提取之后怎么真正的存储被结构化提取出来的东西

**reviewer 回复**：

现有的存储流程已经打通，路径如下：

```
LLM 回复（含 <memory> 标签）
  ↓ learning_engine.py 中 _extract_memory_tags() 解析
  ↓ 得到 list[dict]，每条包含 fact_type/content/concept_tags/salience
  ↓ 调用 memory_facts_service.write_memory_facts()
  ↓ 逐条 db.add(MemoryFact(...))
  ↓ 写入 SQLite memory_facts 表
```

当前 `write_memory_facts()`（`backend/services/memory_facts.py:29-77`）的逻辑是：
1. 遍历 `memories` 列表
2. 每条截断至 500 字
3. 直接 `db.add()` 写入 MemoryFact 表，字段包括 `character_id, world_id, fact_type, content, concept_tags, salience, recall_count=0`

**所以 A1 的改动不涉及存储流程本身**——存储链路已存在且工作正常。A1 改的是**输入端**：通过优化系统提示词中的提取规则，让 LLM 输出更高质量的 `<memory>` 标签内容。类比说：存储管道已经建好了，A1 是改善流进管道的水质。

**owner追问**：
所以说我们是直接把东西写到表里？我记得之前有一篇设计文档构想的是：只使用postgreSQL来提高检索速度，实际内容追加json或者别的什么，我还专门讨论过为什么这样做比直接用系统文件管理器更好。难道我们目前的实现就是全都写表里吗？你认为写表里更好吗？

**reviewer 回复**：

你说的对，`记忆系统设计_基于文件存储.md` 确实设计了一套文件+数据库混合方案。但**当前实现确实是全部写 SQLite 表**（`memory_facts` 表的 `content` TEXT 字段直接存文本）。设计文档中的 JSON 文件存储方案从未被实现。

**设计文档的构想 vs 当前实现**：

| 维度 | 设计文档构想 | 当前实现 |
|------|------------|---------|
| 索引/元数据 | PostgreSQL/SQLite（fact_type, concept_tags, salience） | ✅ SQLite memory_facts 表 |
| 实际内容 | JSON 文件（`data/memories/{char_id}/`） | ❌ 直接存表的 content 字段 |
| 优势 | 大文本不占 DB 空间、可版本管理 | 实现简单、查询方便 |

**我的判断：当前方案对 MVP 够用，但应保留迁移空间。**

理由：
1. 当前记忆内容平均 50-200 字（LLM 提取的精炼摘要），不是大文本，放表里问题不大
2. 如果未来需要存储"完整对话摘要"等大文本，应该迁移到文件存储
3. **Phase 2A 不改动存储介质**——只改写入逻辑（去重、时态）。存储介质的迁移是独立优化，不阻塞核心功能

**建议**：在 A1 方案中加一个 TODO 注释标记未来迁移点。

---




### A2. MemoryFact 去重 + 状态演化

**文件**：`backend/services/memory_facts.py`

**现状**：`write_memory_facts()` 每次直接 `db.add()`，无去重
**改动**：写入前执行去重检查

```python
async def write_memory_facts(db, character_id, world_id, memories, source_message_id=None):
    for mem in memories:
        # === 新增：去重检查 ===
        existing = find_similar_memory(
            db, character_id, world_id,
            fact_type=mem["fact_type"],
            concept_tags=mem.get("concept_tags", []),
            similarity_threshold=0.6  # concept_tags 重叠率
        )

        if existing:
            if is_upgrade(existing, mem):
                # 状态升级：旧记忆失效，新记忆生效
                existing.t_invalid = datetime.utcnow()
                existing.salience = max(existing.salience, mem.get("salience", 0.5))
                # 创建新记忆替代
                new_fact = create_memory_fact(...)
                db.add(new_fact)
            elif is_duplicate(existing, mem):
                # 完全重复：只增强 salience，不新建
                existing.salience = min(1.0, existing.salience + 0.05)
                existing.recall_count += 1
            # else: 不同视角的新信息，正常新建
        else:
            new_fact = create_memory_fact(...)
            db.add(new_fact)
```

**去重逻辑细化**：

| 场景 | 旧记忆 | 新记忆 | 动作 |
|------|--------|--------|------|
| 状态升级 | "学生对递归有困难" | "学生掌握了递归" | 旧→t_invalid, 新建 |
| 确认增强 | "学生偏好视觉化" | "学生喜欢看图" | 旧→salience+0.05, 不新建 |
| 新信息 | "学生对递归有困难" | "学生对排序有困难" | 正常新建 |

**判断函数**：

```python
def is_upgrade(old, new):
    """判断是否是状态升级（同一概念，不同掌握程度）"""
    upgrade_patterns = [
        ("concept_struggle", "concept_mastered"),
        ("concept_struggle", "student_state"),
    ]
    return (old.fact_type, new["fact_type"]) in upgrade_patterns and \
           shared_tags(old.concept_tags, new.get("concept_tags", [])) >= 0.5

def is_duplicate(old, new):
    """判断是否是重复信息"""
    return old.fact_type == new["fact_type"] and \
           shared_tags(old.concept_tags, new.get("concept_tags", [])) >= 0.7
```

**涉及文件**：
- `backend/services/memory_facts.py`（重写 `write_memory_facts`，新增 `find_similar_memory`, `is_upgrade`, `is_duplicate`, `shared_tags`）
- `backend/tests/test_memory_facts.py`（补充去重测试）

#### 讨论区
**owner** : 我更想知道，你采取了状态机还是什么别的算法？你为什么觉得这种方式的去重是可行的？

**reviewer 回复**：

**不是状态机，是规则分类器（Rule-based Classifier）。**

状态机适合"有明确状态转移路径"的场景，但记忆去重不是——我们没有预定义"struggle → mastered → forgotten"这样的固定转移链。记忆之间的关系更复杂：两条记忆可能完全无关、可能重复、也可能一个是另一个的升级版。

所以采用的方法是**三条规则 + 一个相似度计算**：

```
新记忆到来
  ↓
Step 1: 找候选（同 character_id + 同 fact_type + 相似 concept_tags）
  ↓ 没找到 → 新建（新信息）
  ↓ 找到了
Step 2: 分类判断
  ├─ fact_type 升级模式（如 struggle→mastered）且 concept_tags 重叠≥50% → 状态升级
  ├─ fact_type 相同且 concept_tags 重叠≥70% → 确认增强（重复）
  └─ 其他 → 新建（不同视角）
```

**为什么可行**：

1. **concept_tags 是 LLM 已经在生成的字段**——我们不需要额外的 NLP 处理，直接复用 LLM 判断的概念标签作为匹配锚点
2. **fact_type 枚举只有 6 种**（student_state/concept_struggle/concept_mastered/preference/event/commitment），状态升级模式数量有限，规则表很小
3. **阈值设置保守**（重叠率 0.5/0.7）——宁可多建一条记忆，也不误合并两条不同的记忆

**为什么不用更复杂的算法**（如嵌入向量余弦相似度）：
- 当前数据量小（单个学生单世界可能几十到几百条记忆），O(n) 遍历足够快
- concept_tags 的 Jaccard 相似度比文本嵌入更可解释——你能直接看到"这两条记忆都涉及'递归'这个概念"
- 等到记忆量达到万级，才需要考虑向量检索

**owner追问**：
concept_tags是什么？fact_type又是什么？

**reviewer 回复**：

这是 MemoryFact 表的两个核心字段（`backend/models/models.py` 中定义）：

**`concept_tags`**（JSON 数组）：该条记忆关联的知识概念标签。由 LLM 在提取记忆时生成。
- 示例：`["递归", "函数调用", "栈"]`、`["变量作用域"]`
- 用途：去重匹配锚点、检索时的话题匹配

**`fact_type`**（字符串枚举）：该条记忆的类型。当前定义了 6 种：
- `student_state` — 学生状态（如"学生对递归初步理解"）
- `concept_struggle` — 学习困难（如"学生对指针概念有困难"）
- `concept_mastered` — 掌握概念（如"学生掌握了递归"）
- `preference` — 学习偏好（如"学生偏好图解而非文字说明"）
- `event` — 事件记录（如"学生连续学习30分钟"）
- `commitment` — 承诺/目标（如"学生计划每天复习"）

这两个字段是 LLM 通过 `<memory>` 标签提取时自动生成的，格式如：
```xml
<memory>{"fact_type": "concept_struggle", "content": "学生对递归的终止条件理解有误", "concept_tags": ["递归", "终止条件"], "salience": 0.8}</memory>
```

---

### A3. Salience 演化机制

**文件**：`backend/services/memory_facts.py`

**改动**：新增 `evolve_salience()` 函数

```python
def evolve_salience(db, character_id, world_id):
    """记忆 salience 演化

    规则：
    1. 时间衰减：每天 * 0.97（30天后降到原来的 40%）
    2. 召回增强：每次被检索到 +0.05（上限 1.0）
    3. 低 salience 清理：<0.2 且超过 60 天的标记为过期
    """
    memories = db.query(MemoryFact).filter(
        MemoryFact.character_id == character_id,
        MemoryFact.t_invalid.is_(None),  # 仍有效的
    ).all()

    now = datetime.utcnow()
    for mem in memories:
        days_old = (now - mem.created_at).days
        # 衰减
        mem.salience = mem.salience * (0.97 ** days_old)
        # 清理
        if mem.salience < 0.2 and days_old > 60:
            mem.t_invalid = now
```

**调用时机**：每次会话开始时（`learning_engine.py` 的 `start_learning`）

**涉及文件**：
- `backend/services/memory_facts.py`（新增 `evolve_salience`）
- `backend/services/learning_engine.py`（在 `start_learning` 中调用）

#### 讨论区
**owner** : memory_facts.py原本包含这个功能吗？还是说放在prompt组装器里实现更好？你的参数是怎么来的？你凭什么认为这些参数设计的合理？

**reviewer 回复**：

**1. memory_facts.py 原本不包含此功能。** 现有代码中只有 `delete_expired_memories()`（按 `expires_at` 时间点删除），没有基于时间的 salience 衰减。`salience` 字段写入后从未被修改过。

**2. 放在 memory_facts.py 而非 prompt 组装器，因为：**
- salience 演化是**数据层逻辑**（修改数据库中记忆的权重值），不是展示层逻辑
- prompt 组装器只负责**读取** salience 来排序/过滤，不应承担**修改** salience 的职责
- 职责分离：`memory_facts.py` = 记忆的 CRUD + 生命周期管理，`prompt_builder` = 记忆的检索 + 组装

**3. 参数来源和合理性论证：**

| 参数 | 值 | 来源 | 论证 |
|------|----|------|------|
| 衰减系数 | 0.97/天 | Ebbinghaus 遗忘曲线的简化近似 | 0.97^30 ≈ 0.40（30天后保留40%），0.97^90 ≈ 0.06（90天后基本遗忘）|
| 召回增强 | +0.05/次 | ACT-R 认知架构中的"基础激活"机制 | 被检索 10 次后只增加 0.5，不会导致某条记忆永远霸占 top 位 |
| 清理阈值 | salience<0.2 且>60天 | 工程判断 | 配合 60 天最低期限，避免新创建但低 salience 的记忆被误删 |

**坦率说**：这些参数没有经过用户实验验证，是先验估计。正确做法是实现后加上可配置性（放在 config.py 或 world settings），上线后根据实际效果调整。

**owner**：
说说你打算如何加上可配置性？

**reviewer 回复**：

在 `backend/core/config.py` 中新增配置项：

```python
# 记忆系统参数（可在 .env 中覆盖）
MEMORY_SALIENCE_DECAY_RATE: float = 0.97    # 每日衰减系数
MEMORY_RECALL_BOOST: float = 0.05           # 每次召回增强量
MEMORY_CLEANUP_THRESHOLD: float = 0.2       # salience 清理阈值
MEMORY_CLEANUP_MIN_DAYS: int = 60           # 清理最低天数
MEMORY_DEDUP_TAG_OVERLAP_UPGRADE: float = 0.5  # 升级判断的 tag 重叠率
MEMORY_DEDUP_TAG_OVERLAP_DUPLICATE: float = 0.7  # 去重判断的 tag 重叠率
```

这样用户可以通过 `.env` 文件调整参数，不需要改代码。`evolve_salience()` 和去重函数从 config 读取这些值而非硬编码。

---

### A4. 召回追踪激活

**文件**：`backend/services/memory_facts.py` → `retrieve_memories()`

**现状**：`recall_count` 和 `last_recalled_at` 字段存在但从未更新
**改动**：检索到记忆后更新这两个字段

```python
def retrieve_memories(db, character_id, world_id, query=None, limit=8, min_salience=0.4):
    # ... 现有检索逻辑 ...

    # === 新增：更新召回追踪 ===
    for mem in memories:
        mem.recall_count += 1
        mem.last_recalled_at = datetime.utcnow()
    db.flush()

    return memories
```

**涉及文件**：
- `backend/services/memory_facts.py`（`retrieve_memories` 末尾追加 3 行）

#### 讨论区
**owner** : 召回追踪是什么意思？意义何在？

**reviewer 回复**：

**召回追踪 = 记录每条记忆"被用到过多少次"和"最后一次被用到是什么时候"。**

现有代码中已有 `recall_count`（被召回次数）和 `last_recalled_at`（最后召回时间）两个字段，但从未被更新——`retrieve_memories()` 查出记忆后直接返回，没有给这两个字段 +1。

**三个用途**：

1. **Salience 演化的输入**（A3 的配合）：被频繁召回的记忆说明它有价值，应该衰减得更慢。没有召回追踪，salience 演化就只能靠时间衰减这一个维度。
2. **记忆整合的依据**（未来功能）：如果多条记忆都被频繁召回且涉及相似概念，说明它们可以合并为 1 条精炼记忆。
3. **调试/诊断**：如果某条高 salience 记忆 `recall_count=0`，说明检索逻辑有问题。

**改动极小**：`retrieve_memories()` 末尾加 3 行，零风险。

**owner**：
同意该计划
---

### A5. 时态字段激活

**现状**：`记忆系统设计_基于文件存储.md` 设计了 `t_valid`/`t_invalid` 但未实现
**改动**：

1. Alembic 迁移：MemoryFact 新增 `t_valid`/`t_invalid` 列
2. 写入时：`t_valid = now()`, `t_invalid = None`
3. 检索时：过滤 `t_invalid IS NULL`（只返回仍有效的记忆）
4. 存档时：记录当前有效记忆 ID 快照（`valid_memory_ids`）

**涉及文件**：
- 新增 `backend/alembic/versions/xxxx_add_memory_temporal_fields.py`
- `backend/services/memory_facts.py`（写入、检索、演化逻辑）
- `backend/models/models.py`（MemoryFact 模型添加字段）

#### 讨论区
**owner** : 简要说明你准备如何实现该功能

**reviewer 回复**：

实现步骤（按执行顺序）：

**Step 1：Alembic 迁移**
```python
# 新增迁移文件
def upgrade():
    op.add_column('memory_facts', sa.Column('t_valid', sa.DateTime(), nullable=True))
    op.add_column('memory_facts', sa.Column('t_invalid', sa.DateTime(), nullable=True))
    # 回填：现有记忆的 t_valid 设为 created_at，t_invalid 保持 NULL
    op.execute("UPDATE memory_facts SET t_valid = created_at WHERE t_valid IS NULL")
```

**Step 2：模型层**
```python
# models.py 中 MemoryFact 添加
t_valid = Column(DateTime, nullable=True)
t_invalid = Column(DateTime, nullable=True)
```

**Step 3：写入逻辑**
`write_memory_facts()` 中创建 MemoryFact 时追加：`t_valid=datetime.now(UTC), t_invalid=None`

**Step 4：检索逻辑**
`retrieve_memories()` 的查询条件追加：`MemoryFact.t_invalid.is_(None)`（只返回仍有效的记忆）

**Step 5：去重逻辑**（A2 配合）
状态升级时：`existing.t_invalid = datetime.now(UTC)`（旧记忆标记失效）

**Step 6：存档快照**（可选，Phase 2D 时实现）
Checkpoint 的 `state_snapshot` 中记录 `valid_memory_ids` 列表。

改动量：迁移文件 1 个 + 模型 2 行 + 写入 1 行 + 检索 1 个过滤条件。

**owner**：
没太明白，该功能和召回追踪的区别是什么？

**reviewer 回复**：

**完全不同的两个功能，作用于不同层面：**

| 维度 | A4 召回追踪 | A5 时态字段 |
|------|------------|------------|
| **回答的问题** | "这条记忆被用过几次？" | "这条记忆还是不是有效的？" |
| **修改的字段** | `recall_count` + `last_recalled_at` | `t_valid` + `t_invalid` |
| **触发时机** | 每次 retrieve_memories() 被调用时 +1 | 去重判断为"升级"时标记旧记忆 t_invalid |
| **类比** | 图书馆书的"借阅次数"统计 | 图书馆书的"在架/已下架"状态 |

**具体例子**：
```
记忆A："学生对递归有困难"（创建于 3月1日）
  ↓ 3月5日：被检索到 → recall_count=1（A4 召回追踪）
  ↓ 3月10日：学生掌握了递归 → t_invalid=3月10日（A5 时态标记，记忆A失效）
  ↓ 同时创建记忆B："学生掌握了递归" → t_valid=3月10日（A5 时态标记，新记忆生效）
```

没有 A5，检索时会同时返回"有困难"和"已掌握"两条矛盾的记忆。A5 让旧记忆失效，保证只返回当前有效的认知状态。

---

### Phase 2A 讨论区

**需要确认的决策点**：

1. **去重范围**：只在同 `world_id` 内去重，还是跨 world 去重？
   - 建议：同 `world_id` 内去重（不同世界可能涉及不同知识领域）
2. **状态升级规则**：只处理 `concept_struggle → concept_mastered` 的自动升级，其他类型不自动合并？
3. **衰减速率**：0.97/天是否合适？（30天后降到 40%，90天后降到 6%）
4. **清理阈值**：salience < 0.2 且超过 60 天 → 设 t_invalid，是否合理？万一用户很久不上线，岂不是全清理了。

**reviewer 回复**：

好问题。**不会全清理**，因为衰减是按 `created_at` 算的，不是按"最后登录"算的。但确实存在风险：高 salience 的核心记忆（如"学生擅长抽象思维"）如果 90 天不登录也会被清理。

**修正方案**：加一条保护规则——`recall_count > 5` 的记忆永不被自动清理（频繁被召回的记忆说明它持续有价值，不应因时间衰减而被删除）。这条规则加在 `evolve_salience()` 中：
```python
if mem.salience < 0.2 and days_old > 60 and mem.recall_count <= 5:
    mem.t_invalid = now  # 只清理低召回+低 salience 的
```


---

## Phase 2B：Prompt 组装策略重设计（1 周）

> **目标**：从"全部动态检索"改为"固定注入 + 动态检索"的混合策略
> **为什么第二**：Prompt 是 LLM 唯一能看到的东西，组装策略直接决定教学效果

### B1. 模块重新分类

**现状**：6 个 MemoryModule 全部走 `should_include → assemble` 的动态检索逻辑
**改动**：分为两类

| 类别 | 模块 | 注入方式 | 改动 |
|------|------|----------|------|
| **固定注入** | Misconception | 始终注入（活跃误解不可遗漏） | 改为 `FixedModule` |
| **固定注入** | Preference | 始终注入（1-2条简短摘要） | 改为 `FixedModule` |
| **固定注入** | Metacognition | 始终注入（1条极简评估） | 改为 `FixedModule` |
| **动态检索** | MemoryFacts | 按当前话题检索 top-5 | 保持 `MemoryModule` |
| **动态检索** | Episode | 检索近期关键事件 | 保持 `MemoryModule` |
| **条件注入** | Affect | 上次情感!=neutral时注入 | 保持但调整逻辑 |
| **条件注入** | WorldSetting | 新增，叙事上下文 | 新建 |

#### 讨论区
**owner** : 你调查过上下文窗口的长度支持的文本量吗？

**reviewer 回复**：

当前系统默认使用 Claude Sonnet（200K tokens）和 OpenAI GPT-4o（128K tokens）。系统提示词只是 context window 的一部分：

```
context window 总量（以 128K 为例）
  ├── 系统提示词（我们组装的）     ≈ 2,000-4,000 tokens
  ├── 对话历史（最近 N 条）         ≈ 3,000-8,000 tokens
  ├── 用户输入                     ≈ 50-500 tokens
  └── LLM 回复空间（输出）         ≈ 1,000-2,000 tokens
  总计使用                         ≈ 6,000-15,000 tokens
```

系统提示词只有 **2K-4K tokens** 的预算。静态层约占 800-1,200 tokens，动态层约 1,200-2,800 tokens。空间紧张但不会溢出。每个模块必须控制输出量——这也是分"固定注入"和"动态检索"的原因。如果用户使用本地小模型（8K context），可提供"精简模式"开关。

---

### B2. 新增 FixedModule 基类
修正方案：不新建 FixedModule，在现有 MemoryModule 中加一个类属性。
```python
# backend/services/prompt_builder/base.py

class FixedModule:
    """固定注入模块 - 始终注入，不依赖检索

    与 MemoryModule 的区别：
    - FixedModule 数据量小（1-3 条精炼摘要）
    - 始终注入，不受 should_include 限制
    - 优先级高于所有 MemoryModule
    """

    def get_section_name(self) -> str:
        raise NotImplementedError

    def assemble(self, context: dict) -> str | None:
        raise NotImplementedError
```
#### 讨论区
**owner** : 这个module的必要性是什么？为什么不基于现有的 memorymodule嵌入新功能？

**reviewer 回复**：

你说得对，新建基类不是必须的。本质区别只有一个：`should_include()` 的返回值。完全可以通过在现有 MemoryModule 中加一个 `always_include = False` 类属性来实现：

```python
class MemoryModule:
    always_include: bool = False  # 子类可覆写

    def should_include(self, context):
        if self.always_include:
            return True
        # 原有逻辑...
```

Misconception/Preference/Metacognition 只需设置 `always_include = True`，不需要改继承关系。**修正方案：不新建 FixedModule，在现有 MemoryModule 中加一个类属性。**

---

### B3. 模块优先级重新排序

**当前排序**（按 priority 数字）：

```
Misconception(30) → Episode(40) → Preference(50) → Affect(60) → MemoryFacts(70) → Metacognition(80)
```

**新排序**（按教学意义）：

```
固定层（始终注入）:
  1. Misconception     — 活跃误解（最关键，必须避免强化错误）
  2. Preference        — 学习偏好摘要（影响"怎么教"）
  3. Metacognition     — 元认知评估（1行极简）

动态层（按需检索）:
  4. MemoryFacts       — 当前话题相关知识记忆
  5. Episode           — 近期关键事件
  6. Affect            — 情感状态（条件注入）
```

这对应 `learning_memory_theory.md` 的"按教学意义分组"设计意图。

#### 讨论区
**owner** : 这种组装方式会不会让ai丢失上下文？即"上次聊到这里了但是ai很明显出现记忆断层"

**reviewer 回复**：

**不会，因为对话历史不在模块系统中。**

记忆断层的真正原因是"对话历史被截断"。我们系统的对话历史加载在 `learning_engine.py` 中，独立于 prompt_builder 的模块系统：

```
最终发送给 LLM 的 messages:
  [0] system prompt   ← prompt_builder 组装（静态层 + 动态层）
  [1] 历史消息 #1     ← 从 chat_messages 表加载
  [2] 历史消息 #2     ← 最近 N 条
  ...
  [N] 用户当前输入
```

模块系统只影响 `[0] system prompt`，不影响对话历史。上下文连续性靠的是对话历史，不是系统提示词中的记忆模块。记忆模块的作用是**补充**：第 50 轮时把第 3 轮的关键信息重新注入，**减少**断层。

真正会断层的风险场景：去重 bug 把关键记忆误标为 `t_invalid`。所以 A2 的去重逻辑必须保守。

**owner**：快在A2建立链接到这里并重点标注。

**reviewer**：⚠️ 已在 A2 讨论区末尾添加链接。**重要提醒**：去重逻辑必须保守——如果误标关键记忆为 `t_invalid`，会导致 B3 中提到的"记忆断层"风险。A2 和 B3 是强关联的。参见 → **A2 讨论区（去重误判风险与 B3 记忆断层的关联）**

---

### B4. 各模块输出格式规范化

**MisconceptionModule 改造**：

```python
# 现状：从 MemoryFact 检索 type="misconception"
# 改造：始终查询活跃误解（t_invalid IS NULL），格式强调

def assemble(self, context):
    misconceptions = memory_facts_service.retrieve_by_type(
        db, character_id, world_id,
        fact_type="misconception",
        active_only=True,  # t_invalid IS NULL
    )
    if not misconceptions:
        return None

    lines = ["该学生存在以下误解，教学时必须注意避免强化："]
    for mc in misconceptions[:3]:  # 最多3条
        lines.append(f"- [{mc.concept_tags}] {mc.content}")
    return "\n".join(lines)
```

**涉及文件**：
- `backend/services/prompt_builder/base.py`（新增 `FixedModule` 基类）
- `backend/services/prompt_builder/builder.py`（`SceneConfig` 重构，`build_dynamic_layer` 分固定/动态两层）
- `backend/services/prompt_builder/modules/misconception.py`（改造为 `FixedModule`）
- `backend/services/prompt_builder/modules/preference.py`（改造为 `FixedModule`）
- `backend/services/prompt_builder/modules/metacognition.py`（改造为 `FixedModule`）
- `backend/services/prompt_builder/modules/memory_facts.py`（增加 `active_only` 过滤）

> *（B4 模块输出格式规范化的讨论已整合到 B1-B3 的讨论区中）*

---

### Phase 2B 讨论区


⚠️ **Phase 2D 关联提醒**：Phase 2D 的 NarrativeModule（D3）将加入 Phase 2B 的固定层。设计模块体系时须预留叙事模块的 slot。→ 参见 **D3 讨论区**

**需要确认的决策点**：

1. **固定注入的数据量控制**：固定注入模块（Misconception/Preference/Metacognition）总输出不超过多少 tokens？
2. **Affect 条件**：只在情感 != neutral 时注入，还是始终注入？
3. **WorldSetting 模块**：是 Phase 2B 就建框架（空壳），还是等 Phase 2D 叙事系统一起做？

---

## Phase 2C：教材上传 + AI 课程生成（2 周）

> **目标**：学生上传 PDF → 系统自动生成课程
> **核心差异化功能**，系统的"入口"

### C1. Material 模型 + 存储层

```python
# backend/models/models.py 新增
class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    world_id = Column(Integer, ForeignKey("worlds.id"), nullable=True)

    # 文件信息
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)  # data/materials/{user_id}/{filename}
    file_size_bytes = Column(Integer, nullable=False)
    file_type = Column(String(20))  # "pdf", "txt", "epub"

    # 解析状态
    parse_status = Column(String(20), default="pending")  # pending/parsing/parsed/failed
    parse_error = Column(Text, nullable=True)
    parsed_content = Column(Text, nullable=True)  # 提取的纯文本
    chapter_count = Column(Integer, nullable=True)

    # AI 分析结果
    analysis_result = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=_utcnow)
```

### C2. 文件上传 API

```python
# backend/api/routes/materials.py

@router.post("/upload")
async def upload_material(
    file: UploadFile,
    world_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """上传教材文件（PDF/TXT/EPUB）

    流程：
    1. 验证文件类型和大小（<50MB）
    2. 存储到 data/materials/{user_id}/
    3. 后台触发解析任务
    4. 返回 material_id
    """

@router.get("/{material_id}/status")
async def get_parse_status(material_id: int, ...):
    """查询解析进度"""

@router.post("/{material_id}/generate-course")
async def generate_course(material_id: int, world_id: int, ...):
    """基于解析结果生成课程

    流程：
    1. 读取 analysis_result
    2. 创建 Course + 章节
    3. 生成知识图谱种子数据（MemoryFact seed）
    4. 返回 course_id
    """
```
#### 讨论区
**owner** : 我想知道这个文件到底被传哪了

**reviewer 回复**：

文件存储路径：`data/materials/{user_id}/{filename}`，是**本地文件系统存储**。流程：

```
用户上传 PDF
  ↓ FastAPI UploadFile 接收（暂存内存/临时文件）
  ↓ 验证类型+大小
  ↓ 写入 data/materials/{user_id}/{uuid}_{original_filename}
  ↓ Material 记录中 file_path 存储这个绝对路径
  ↓ parsed_content 存入 DB 的 Text 字段（提取的纯文本）
  ↓ 原始文件保留（供重新解析用）
```

docker-compose.yml 中已配置 `volumes: - ./data:/app/data`。安全性：API 层需验证 `material.user_id == current_user.id`，防止越权访问。

**owner**：
那我认为应该在设置页加上设置学习材料区的地方，这个功能与我在A1的质问有关系，可以在A1处加上到这里的链接

**reviewer 回复**：同意。设置页的"学习材料管理区"可以作为 C5 前端组件的一部分——用户既能在 WorldDetail 中管理世界绑定的教材，也能在设置页统一管理所有上传的材料。已添加 A1→C2 交叉引用。

---

### C3. PDF 解析服务

```python
# backend/services/material_parser.py

class MaterialParser:
    """教材解析服务"""

    async def parse_pdf(self, file_path: str) -> dict:
        """解析 PDF 文件

        步骤：
        1. pymupdf 提取文本（按页/按章节）
        2. 章节检测（正则匹配 "第X章"、"Chapter X" 等）
        3. 清洗文本（去页眉页脚、合并跨页段落）

        返回: {
            "chapters": [
                {"title": "第一章 导论", "content": "...", "page_range": [1, 15]},
                ...
            ],
            "total_pages": 200,
            "total_chars": 150000,
            "language": "zh"
        }
        """

    async def analyze_with_llm(self, parsed: dict) -> dict:
        """LLM 分析教材内容

        分章节送入 LLM（每章单独调用，避免超 token）
        合并结果

        返回: {
            "knowledge_points": [
                {"name": "递归", "bloom_level": "understand",
                 "prerequisites": ["函数", "栈"], "chapter": 3},
                ...
            ],
            "teaching_order": ["函数", "变量作用域", "递归", ...],
            "difficulty_assessment": "intermediate",
            "suggested_session_count": 15,
            "narrative_suggestion": "可以用'魔法咒语层层展开'来比喻递归"
        }
        """
```

#### 讨论区
**owner** : 我们为什么不找一些现有的pdf解析开源服务？它们应该比我们自己手搓的轮子更好，不是吗？

**reviewer 回复**：

你说得对，自搓轮子不是最优解。可选方案：

| 方案 | 优势 | 劣势 |
|------|------|------|
| **MinerU/magic-pdf**（上海AI Lab） | **中文 PDF 解析效果最好**，支持 OCR/表格/公式 | 需额外部署，较重 |
| **Marker** | PDF→Markdown，支持公式/表格 | 主要针对英文 |
| **Unstructured.io** | 通用文档解析 | 云端付费，本地依赖多 |
| **pymupdf**（当前方案） | 轻量，纯 Python | 只是文本提取，不理解排版 |

**建议分两阶段**：MVP 用 pymupdf 做基础文本提取（LLM 分析的是文本语义不是排版，够用）；优化阶段集成 MinerU 处理复杂 PDF（含公式、图表、扫描件）。

**owner**：
不错，这个方案还可以更具体。

**reviewer 回复**：

**C4 `KnowledgeGraphGenerator` 详细方案**：

```python
class KnowledgeGraphGenerator:
    async def generate(self, material_id: int, world_id: int, db: Session):
        material = db.get(Material, material_id)
        world = db.get(World, world_id)

        # Step 1: 从教材提取知识点
        kps = material.analysis_result["knowledge_points"]

        # Step 2: 结合世界观为每个知识点生成叙事建议
        hints = await self._generate_narrative_hints(kps, world.scenes)
        # "递归" + 赛博朋克 → "入侵多层防火墙，每层结构相同"

        # Step 3: 创建知识图谱节点
        for i, kp in enumerate(kps):
            node = KnowledgeNode(
                world_id=world_id, name=kp["name"],
                bloom_level=kp["bloom_level"],
                prerequisites=kp["prerequisites"],
                narrative_hint=hints[i],
                order_index=i, status="locked"
            )
            db.add(node)
        nodes[0].status = "available"  # 解锁第一个

        # Step 4: 写入 MemoryFact seed
        seed = MemoryFact(
            character_id=world.character_id, world_id=world_id,
            fact_type="event",
            content=f"教材《{material.original_filename}》已录入，共{len(kps)}个知识点",
            concept_tags=["知识图谱"], salience=0.9
        )
        db.add(seed)
```

**新增 KnowledgeNode 模型**：`id, world_id, name, bloom_level, prerequisites(JSON), narrative_hint, order_index, status(locked/available/learning/mastered)`

**与教学的关系**：Sage 按 `order_index` 顺序教学，`concept_mastered` 记忆触发解锁下一个节点。

---

### C4. 课程生成服务

```python
# backend/services/course_generator.py

class CourseGenerator:
    """课程自动生成"""

    async def generate(self, material_id: int, world_id: int, db: Session) -> Course:
        """
        1. 读取 Material.analysis_result
        2. 创建 Course（name=教材名, description=AI 生成摘要）
        3. 按 teaching_order 创建概念节点（写入 MemoryFact seed）
        4. 创建 prerequisite 关系（concept_tags 共享实现）
        5. 返回 Course 对象
        """
```
#### 讨论区
**owner** : 我认为你对课程生成的理解有问题。思考：如果课程完全由ai基于教材生成，那用户创建课程又是做什么？用户制定的那些课程背景又算什么？

**reviewer 回复**：

你说得对。正确定位：**用户创建的课程 = 世界（World），用户自定义的背景 = 世界观设定。** 教材不是"替代"课程，而是"充实"世界。

修正后的流程：
```
用户创建世界（自定义名称、背景、Sage角色、世界观）
  ↓ 用户在世界中上传教材
  ↓ AI 基于教材 + 世界观 → 生成知识图谱（不是生成课程）
  ↓ 知识图谱 = 学习路线图（知识点、顺序、难度）
  ↓ Sage 基于知识图谱 + 世界观 → 在对话中教学
```

**C4 应改名为 `KnowledgeGraphGenerator`**，只做：提取知识点+依赖关系、排序推荐路线、为每个知识点生成叙事建议（结合世界观）。

**owner**：
不错，这个方案还可以更具体。
---

### C5. 前端上传组件

- 新增 `MaterialUpload.vue`（拖拽上传 + 进度条）
- `WorldDetail.vue` 新增"上传教材"入口
- 解析完成后展示知识点列表 + "生成课程"按钮

**涉及文件**：
- 新增 `backend/models/materials.py` 或 `backend/models/models.py` 追加
- 新增 `backend/services/material_parser.py`
- 新增 `backend/services/course_generator.py`
- 新增 `backend/api/routes/materials.py`
- `backend/main.py` 注册新路由
- `backend/requirements.txt` 添加 `pymupdf`
- 新增 Alembic 迁移
- 前端：新增上传组件，修改 WorldDetail 页面

---

### Phase 2C 讨论区

**需要确认的决策点**：

1. **解析同步 vs 异步**：PDF 解析 + LLM 分析可能需要几分钟，用后台任务还是同步等待？ 同步等待和后台任务的呈现有什么区别？
2. **LLM 调用策略**：大教材可能需要 10+ 次 LLM 调用（逐章分析），成本如何控制？提前判断大小，让用户选择。
3. **课程与 World 的绑定**：上传教材时必须指定 World，还是先上传后绑定？"上传教材"入口不是在`WorldDetail.vue`吗？你为什么认为教材会和world不绑定？教材可是和课程绑定的，课程难道不是和world绑定的吗？
4. **知识图谱种子数据**：课程生成时写入的 MemoryFact seed，salience 应该设为多少？这个参数的意义是什么？

---

## Phase 2D：历险叙事系统（1.5 周）

> **目标**：把"上课"包装为"历险"，增加沉浸感

### D1. 叙事模板 Schema

```json
{
  "narrative": {
    "theme": "magic_academy",
    "title": "魔法学院的试炼",
    "chapters": [
      {
        "id": "ch1",
        "name": "入学测试",
        "trigger": {"type": "first_session"},
        "scene_key": "academy_entrance",
        "narrative_intro": "你踏入了魔法学院的大门，{sage_name}导师正在等你..."
      },
      {
        "id": "ch2",
        "name": "基础修炼",
        "trigger": {"type": "mastery_threshold", "value": 0.3},
        "scene_key": "training_ground",
        "narrative_intro": "经过入学测试，{sage_name}认为你可以开始正式修炼了..."
      }
    ],
    "events": [
      {
        "type": "breakthrough",
        "trigger": {"type": "concept_mastered"},
        "template": "一道光芒在你脑海中亮起！你领悟了「{concept}」！{sage_name}赞许地点了点头。"
      },
      {
        "type": "struggle",
        "trigger": {"type": "concept_struggle", "duration": 3},
        "template": "{sage_name}注意到你在「{concept}」上遇到了瓶颈..."
      }
    ],
    "examples": [
      "魔法学院（适合编程/数学类）",
      "太空探索（适合物理/天文类）",
      "古代书院（适合文科类）",
      "自定义..."
    ]
  }
}
```

#### 讨论区
**owner** : 我不喜欢这个叙事模板。我们本来是要让用户自定义自己的故事，或者用户输入提示词让ai生成。现在这个模板不是赤裸裸的偷懒吗？

**reviewer 回复**：

你说得对。修正方案——用户自定义叙事的两种方式：

1. **结构化描述**：用户提供世界背景文字，AI 基此生成叙事框架
2. **自由提示词**：用户只输入一句"我想在赛博朋克世界里学编程"，AI 自动构建完整叙事

修正后 D1：
```json
{
  "narrative_input": {
    "mode": "prompt",
    "user_prompt": "我想在赛博朋克城市里学编程",
    "ai_generated": {
      "world_theme": "赛博朋克黑客城市",
      "learner_role": "新晋黑客",
      "sage_role": "传奇黑客导师",
      "knowledge_metaphor": "编程概念=黑客技能",
      "progression_arc": "从街头混混到传说级黑客",
      "event_templates": {
        "breakthrough": "你成功入侵了「{concept}」系统！{sage_name}在终端那头打了个响指。",
        "struggle": "「{concept}」的加密层比想象中复杂..."
      }
    }
  }
}
```

预制模板降级为"示例/灵感参考"。AI 生成叙事框架是一次性调用（创建世界时），不增加运行时成本。

---

### D2. 叙事引擎

```python
# backend/services/narrative_engine.py

class NarrativeEngine:
    """历险叙事引擎"""

    def check_triggers(self, context: dict) -> list[dict]:
        """检查叙事触发条件

        根据学习进度（mastery）、事件类型（concept_mastered/struggle）
        返回应该触发的叙事事件列表
        """

    def format_event(self, event: dict, context: dict) -> str:
        """格式化叙事事件（替换模板变量）"""

    def get_current_chapter(self, narrative: dict, mastery: float) -> dict:
        """根据掌握度获取当前章节"""
```

#### 讨论区
**owner** : 这个叙事引擎还不错，你还可以更多考虑它如何能在各个世界背景都保持通用性

**reviewer 回复**：

通用性关键：**引擎只处理"事件类型"和"触发条件"，不关心具体文本。**

```python
class NarrativeEngine:
    EVENT_TYPES = ["breakthrough", "struggle", "milestone", "stage_change", "session_start", "session_end"]
    TRIGGER_TYPES = ["concept_mastered", "concept_struggle", "mastery_threshold", "affection_threshold", "session_count"]

    def check_triggers(self, context) -> list[dict]:
        """纯逻辑判断：发生了什么事件？不含叙事文本"""

    def format_event(self, event, narrative) -> str:
        """从 narrative 的 event_templates 取模板+填变量"""
```

**分离点**：`check_triggers()` 是纯逻辑（所有世界通用）。`format_event()` 的模板来自每个世界自己的 narrative 配置。引擎本身不知道"魔法学院"或"赛博朋克"。

**owner**：你的思路可行性稍欠，你只是将问题推给了别的东西，将引擎和具体文本分离是很好，但是分离之后呢？“如果触发了事件，到底会显示什么给用户”，你还是没有考虑到。

**reviewer 回复**：你说得对。漏了最关键的环节——"触发后做什么"。修正后完整链路：

```
NarrativeEngine.check_triggers(context)
  ↓ 返回 [{"event_type": "breakthrough", "concept": "递归"}]
  ↓
NarrativeEngine.format_event(event, world.narrative)
  ↓ 从 event_templates 取模板 → "你领悟了「递归」！"
  ↓ 返回 {"title": "概念突破", "content": "...", "type": "breakthrough"}
  ↓
─── 分叉：两个输出通道 ───
  ├─ 通道1: NarrativeModule → 注入 system prompt
  │   "学生刚刚领悟了递归，请在回复中自然地呼应"
  └─ 通道2: API 返回前端 → GameEventOverlay.vue 弹窗
      全屏遮罩 + 打字机效果 + 背景切换
```

同一事件同时走两个通道：prompt 注入让 Sage 在对话中呼应事件，前端弹窗给学生视觉反馈。两者缺一不可。

---

### D3. 叙事 Prompt 注入

新增 `backend/services/prompt_builder/modules/narrative.py`：

```python
class NarrativeModule(MemoryModule):
    """叙事上下文模块"""

    def get_section_name(self) -> str:
        return "【历险叙事】"

    def assemble(self, context):
        # 读取 World.scenes（叙事模板）
        # 调用 NarrativeEngine 获取当前章节 + 事件
        # 返回叙事上下文注入 Prompt
```
#### 讨论区
**owner** : 这里涉及到prompt组装问题，要更谨慎，建议与上文讨论记忆检索处放在一起考虑

**reviewer 回复**：

同意。NarrativeModule 应该和 Phase 2B 的模块体系统一设计。它不是独立的特殊模块，而是遵循相同的 `always_include`/`should_include` 机制：

```python
class NarrativeModule(MemoryModule):
    always_include = True  # 叙事上下文始终注入
    priority = 10  # 最高优先级——叙事框架定义了"我们在哪"
```

**在 build_dynamic_layer 中的最终顺序**：
```
固定层：Narrative → Misconception → Preference → Metacognition
动态层：MemoryFacts → Episode → Affect
```

叙事在前（定义角色和场景），认知在后（定义教学策略）。两者互不冲突。

**owner**：
我希望你在phase 2B相应位置建立一个链接到此处，来提示2B设计时要考虑到这里。

**reviewer**：⚠️ 链接已建立。→ 参见 **Phase 2B 讨论区**（B1 模块表中的 WorldSetting 行 + B3 排序中的 Narrative 模块位置）。Phase 2B 实施时须将 NarrativeModule 纳入固定层设计。
---

### D4. 前端叙事事件展示

- Galgame 风格事件弹窗（全屏遮罩 + 打字机效果文字 + 特效）
- 章节转换时背景图切换（复用现有 Background 组件）
- 好感度变化动画

**涉及文件**：
- 新增 `backend/services/narrative_engine.py`
- 新增 `backend/services/prompt_builder/modules/narrative.py`
- `backend/services/prompt_builder/builder.py`（`SceneConfig` 添加 `NarrativeModule`）
- `backend/models/models.py`（World.scenes JSON 结构定义）
- 前端：新增 `NarrativeEvent.vue` 事件弹窗组件
- 前端：`Learning.vue` 增加叙事事件监听
- 预制 3 套示例叙事模板（魔法学院/太空探索/古代书院）

---
#### 讨论区
**owner** : 模板问题我已经在D1里说过了，不过这个特殊ui的想法我很喜欢。

**reviewer 回复**：

收到。D4 前端叙事事件展示保留，模板问题已在 D1 修正。Galgame 风格的事件弹窗是这个 Phase 的亮点 UI。

---

### Phase 2D 讨论区

**需要确认的决策点**：

1. **叙事模板存储位置**：存在 `World.scenes` JSON 列中，还是独立表？ 
**owner**：你有什么想法？
2. **叙事事件粒度**：每个叙事事件是否需要前端弹窗，还是只在 Prompt 中注入文字？
**owner**：需要弹窗，给用户刺激。
3. **章节触发条件**：除了 mastery 阈值，是否还需要其他触发条件（如会话数、时间）？
**owner**：你有什么想法？
4. **用户自定义叙事模板的编辑方式**：JSON 编辑器还是表单？
**owner**：对于这个自定义方式，到底是叙事模板还是别的什么，我还不大确定。

---

## Phase 2E：游戏化指标激活（1 周）

> **目标**：激活已有的经验值/等级/好感度字段，让学习有"游戏感"

### E1. 好感度系统

```python
# backend/services/gamification.py

def compute_affection(relationship: dict) -> int:
    """计算好感度 0-100

    加权平均: trust*0.3 + familiarity*0.2 + respect*0.3 + comfort*0.2
    映射到 0-100
    """

def get_affection_stage(affection: int) -> str:
    """好感度 → 关系阶段标签

    0-20: 陌生人
    21-40: 熟人
    41-60: 朋友
    61-80: 挚友
    81-100: 灵魂伴侣
    """
```
#### 讨论区
**owner** : 好感度系统看起来还不错，我想知道你给出的代码是现编的还是援引自本地代码已经实现的一些地方？

**reviewer 回复**：

**一半援引一半现编。**

**已实现的**（`backend/services/relationship.py`）：
- `derive_stage(dimensions)` — 4 维平均 → 5 级阶段（stranger/acquaintance/friend/mentor/partner）
- `update_dimensions()` — 根据情感类型更新 4 维数值
- `check_events()` — 检测阶段变化和维度突破

**现编的部分**：
- `compute_affection()` — 把 4 维映射为 0-100 的单一数值。现有代码没有这个
- `get_affection_stage()` — 5 级标签映射。和现有 `derive_stage()` 不一致

**修正**：应该直接复用 `derive_stage()` 的逻辑，不另搞映射。好感度展示只做：把 4 维数值可视化为前端 UI（雷达图或心形条）。

**owner**：
那你应当修复你在E1中的表述，不是吗？

**reviewer 回复**：修正 E1 如下：

E1 好感度系统应直接复用 `backend/services/relationship.py` 的现有逻辑：
- 展示：将 4 维数值（trust/familiarity/respect/comfort）可视化为前端 UI（雷达图或心形条）
- 阶段判断：复用 `derive_stage(dimensions)` 的 5 级映射（stranger/acquaintance/friend/mentor/partner）
- 更新：复用 `update_dimensions()` 根据情感类型更新 4 维数值
- 不另搞 `compute_affection()` 映射和 `get_affection_stage()` 标签

新增的 `gamification.py` 只做：调用 relationship.py 的函数 + 格式化为前端需要的 API 响应。
---

### E2. 经验值系统

```python
# 学习行为 → XP 获得规则
XP_RULES = {
    "send_message": 5,            # 每条发言
    "concept_mastered": 50,       # 掌握一个概念
    "misconception_corrected": 30, # 纠正一个误解
    "session_complete": 20,       # 完成一次学习会话
    "streak_bonus": 10,          # 连续学习奖励（每天）
}

def compute_level(xp: int) -> int:
    """XP → 等级

    等级公式: level = floor(sqrt(xp / 100))
    Level 1: 0 XP
    Level 5: 2500 XP
    Level 10: 10000 XP
    """
```
#### 讨论区
**owner** : 经验值系统不太好，不喜欢。怎么不回复我！你是删除还是别的什么？！

**reviewer 回复**：抱歉漏了回复。**E2 经验值系统整节删除**。E4 中的经验值动画和等级提升特效也删除。方案中不再包含任何 XP/等级相关内容。
### E3. 成就系统

```python
class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    character_id = Column(Integer, ForeignKey("characters.id"))
    achievement_key = Column(String(50))  # "first_session", "streak_7", etc.
    unlocked_at = Column(DateTime)

# 预设成就（无 icon）
PRESET_ACHIEVEMENTS = {
    "first_session": {"name": "初入世界", "desc": "完成第一次学习会话"},
    "streak_7": {"name": "坚持不懈", "desc": "连续学习7天"},
    "concepts_10": {"name": "博学多才", "desc": "掌握10个概念"},
    "affection_friend": {"name": "心意相通", "desc": "好感度达到'朋友'"},
    "misconception_5": {"name": "迷途知返", "desc": "纠正5个误解"},
}
```
#### 讨论区
**owner** : 成就系统不错，成就系统应该和上文的特殊ui关联在一起实现，你认为呢？

**reviewer 回复**：

完全同意。成就解锁、叙事事件、好感度阶段变化应该共享同一套 Galgame 弹窗组件：

```
叙事事件弹窗    → "一道光芒亮起！你领悟了递归！"
成就解锁弹窗    → "成就解锁：博学多才 — 掌握10个概念"
好感度阶段变化  → "你和{Sage}的关系从'熟人'变成了'朋友'"
```

统一为 `GameEventOverlay.vue` 组件，接收 `{type, title, content}` 参数。E3 和 D4 的前端部分合并实现。

**owner**：
不错，在D4处建立到此处的链接，来提醒设计方案的。

**reviewer**：⚠️ 链接已建立。→ 参见 **D4 前端叙事事件展示**讨论区。D4 实施时须使用 `GameEventOverlay.vue` 统一处理叙事事件、成就解锁、好感度阶段变化三种弹窗。
---

### E4. 前端 HUD 增强

- 好感度条（心形进度条 + 阶段标签）
- 经验值动画（XP 增加时数字飘起）
- 成就解锁 Galgame 弹窗
- 等级提升特效

**涉及文件**：
- 新增 `backend/services/gamification.py`
- 新增 `backend/models/achievements.py` 或 `models.py` 追加
- `backend/services/learning_engine.py`（在消息处理循环中触发 XP 更新）
- 新增 Alembic 迁移
- 前端：HUD 组件增强，新增 `AchievementToast.vue`

---
#### 讨论区
**owner** : 经验值和等级不要了，其他的不错。

**reviewer 回复**：

收到。E2/E4 中移除经验值和等级相关内容。保留：
- E1：好感度系统（复用现有 `relationship.py` 的逻辑）
- E3：成就系统（+ Galgame 弹窗 UI，与 D4 共享 `GameEventOverlay.vue`）
- E4：HUD 增强（好感度条 + 成就展示，去掉经验值/等级部分）

---

### Phase 2E 讨论区

**需要确认的决策点**：

1. **好感度映射**：4维加权平均 → 0-100 的公式是否合理？还是用其他方式（如取最大维度）？
你怎么想？
2. **XP 来源**：`send_message` 每次 +5 是否会导致刷经验？（可能需要加每日上限）不要经验！
3. **等级与教学的关系**：等级提升是否解锁新的教学内容/对话风格？还是纯展示？不要等级！
4. **成就展示**：用 Galgame 弹窗还是其他方式？
弹窗，后续再添加展示架。对了：我们目前已达成的成就如何存储？
---

## Phase 2F：语义检索增强 + 学习画像 UI（1 周）

> **目标**：提升记忆召回质量，让学生看到自己的成长

### F1. 语义标签增强检索

```python
# backend/services/memory_facts.py 改造

def retrieve_memories(db, character_id, world_id, query=None, ...):
    if query and len(query) > 5:
        # 1. 生成检索标签（LLM 调用）
        search_tags = generate_search_tags(query)  # ["递归", "recursion", "循环", "自调用"]

        # 2. 多标签匹配（替代 ILIKE）
        memories = db.query(MemoryFact).filter(
            MemoryFact.character_id == character_id,
            MemoryFact.t_invalid.is_(None),
            or_(
                MemoryFact.concept_tags.op('@>')(cast(search_tags, JSON)),
                *[MemoryFact.content.ilike(f'%{tag}%') for tag in search_tags]
            )
        ).order_by(MemoryFact.salience.desc()).limit(limit).all()
```

### F2. 学习画像页面

- "我的学习风格"雷达图（偏好5维度）
- "成长曲线"折线图（掌握度随时间变化）
- "优势与待提升"展示（元认知4维度 + 学习统计）
- Galgame 风格 UI 包装

**涉及文件**：
- `backend/services/memory_facts.py`（检索逻辑增强）
- 新增 `backend/api/routes/user_profile.py`（画像 API）
- 前端：新增 `LearningProfile.vue` 页面

---

### Phase 2F 讨论区

**需要确认的决策点**：

1. **语义标签生成**：每轮对话多一次 LLM 调用来生成检索标签，延迟是否可接受？
2. **画像页面入口**：放在哪里？（个人设置页 / Home 页 / World 详情页）
3. **图表库选择**：Chart.js（轻量）还是 ECharts（功能丰富但更大）？

---

