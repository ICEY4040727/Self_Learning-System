# 学习系统记忆分类 — 设计指导思想

> **文档类型**：理论基础文档（设计决策的学术依据）
> **日期**：2026-03-31
> **用途**：记录我们的记忆分类系统从哪些理论/研究中来，日后回溯设计原因时参考

---

## 一、理论来源

### 1.1 Bloom 分类法（修订版，2001）

Anderson & Krathwohl 对 Bloom 原始分类法的修订，将知识分为四类：

| 知识类型 | 定义 | 原文 |
|---------|------|------|
| **事实知识** (Factual) | 学科的基本元素——术语、细节、公式 | "basic elements students need to know to be acquainted with a discipline or solve problems in it" |
| **概念知识** (Conceptual) | 元素之间的关系——分类、原理、模型 | "connections between basic elements within a larger whole that allow them to function together" |
| **程序知识** (Procedural) | 如何做某事——方法、步骤、技术 | "how to do something, methods of inquiry, and criteria for using skills" |
| **元认知知识** (Metacognitive) | 对认知过程的认知——自知、自监、自调 | "knowledge about cognition in general as well as awareness of one's own cognition" |

认知过程维度（从低到高）：Remember → Understand → Apply → Analyze → Evaluate → Create

**我们的应用**：用 Bloom 的知识类型区分记忆分类（事实/概念/程序/元认知），用认知过程层级标注掌握深度（`bloom_level` 字段）。

> 来源：[Using Bloom's Taxonomy to Write Effective Learning Objectives](https://tips.uark.edu/using-blooms-taxonomy/) / [Wikipedia: Bloom's Taxonomy](https://en.wikipedia.org/wiki/Bloom's_taxonomy)

### 1.2 ITS 学生模型（智能教学系统）

智能教学系统（Intelligent Tutoring System）的核心组件之一是学生模型（Student Model），用于追踪学生的知识状态。三种经典模型：

**覆盖模型（Overlay Model）**

将领域知识分解为知识组件（Knowledge Components），学生模型是领域模型的子集。每个知识组件有一个掌握度值（Boolean 或连续值）。

- 优点：简单直观
- 缺点：只能表示"知道/不知道"，无法表示"错误地知道"

**扰动模型（Perturbation Model）**

覆盖模型的扩展。除了"学生知道什么"，还显式追踪"学生错误地认为什么"——即误解（misconceptions）。使用 bug library（已知常见错误库）和 generative modeling（从学生行为推断错误模式）。

- 关键洞察："不知道"和"错误地知道"需要不同的教学策略。不知道→教；错误地知道→先破再立。

**概率模型（Bayesian Knowledge Tracing, BKT）**

将掌握度建模为隐马尔可夫过程。每次学生回答问题后，用贝叶斯更新掌握度的概率。考虑四个参数：初始掌握概率、学习转移概率、猜测概率、失误概率。

**我们的应用**：
- 覆盖模型 → 我们的 `mastery` 字段（0-1 连续值）
- 扰动模型 → 我们的 `misconception` 类型（显式追踪误解）
- BKT 的启发 → 掌握度不只看"答对了"，还考虑猜测和失误的可能

> 来源：[A Review of Learner Models Used in ITS](https://www.researchgate.net/publication/258883086_A_Review_of_Learner_Models_Used_in_Intelligent_Tutoring_Systems) / [Comprehensive Review of AI-based ITS 2025](https://arxiv.org/html/2507.18882v1)

### 1.3 认知科学记忆分类

人类长期记忆分为：

| 记忆类型 | 定义 | AI Agent 对应 |
|---------|------|-------------|
| **语义记忆** (Semantic) | 关于世界的事实和知识："地球是圆的" | 知识图谱中的概念和关系 |
| **情景记忆** (Episodic) | 个人经历和事件："上周二讨论了递归" | 交互摘要（episode） |
| **程序记忆** (Procedural) | 技能和操作："骑自行车" | 程序性技能（skill） |

AI Agent 领域对此的扩展（来自 MemGPT/Letta 和 LangChain）：

| Agent 记忆类型 | 对应人类记忆 | 实现方式 |
|--------------|------------|---------|
| **工作记忆** (Working) | 工作记忆/短期记忆 | LLM context window |
| **语义记忆** (Semantic) | 语义记忆 | 向量数据库 / 知识图谱 |
| **情景记忆** (Episodic) | 情景记忆 | 对话历史 / 事件日志 |
| **程序记忆** (Procedural) | 程序记忆 | System prompt / 工具定义 |

**我们的应用**：用认知科学的分类框架，但做了适配——我们的"语义记忆"进一步拆分为事实知识、概念关系、误解三种，因为教学场景需要更细的粒度。

> 来源：[Semantic vs Episodic vs Procedural Memory in AI Agents](https://medium.com/womenintechnology/semantic-vs-episodic-vs-procedural-memory-in-ai-agents-and-why-you-need-all-three-8479cd1c7ba6) / [From Human Memory to AI Memory: A Survey](https://arxiv.org/html/2504.15965v2)

### 1.4 Jarvis 认知记忆架构（2025）

Jarvis 是一个为 AI 辅助学习设计的认知记忆架构。理论基础：

- **Bloom 的 Two Sigma 问题**：一对一辅导的学生比课堂教学的学生高出两个标准差——如何用 AI 逼近这个效果？
- **认知负荷理论**：学习材料要匹配学生的认知负荷水平
- **自我调节学习（SRL）**：学生需要学会规划、监控、评估自己的学习

Jarvis 的五个模块：
1. 持久记忆（Persistent Memory）— 跨会话记住学生
2. 元认知脚手架（Metacognitive Scaffolding）— 引导学生反思
3. 情感状态追踪（Emotional State Tracking）— 监测学习情绪
4. 间隔重复（Spaced Repetition）— FSRS 算法复习
5. 领域感知编排（Domain-Aware Orchestration）— 按学科特点调整

实证：一个学生使用 Jarvis 一年，在全职工作的同时完成了 39 学分 + 3 个行业认证。

**我们的应用**：Jarvis 验证了"持久学习者模型 + 元认知追踪 + 情感监测"这个组合在真实学习中是有效的。我们的 7 类记忆分类覆盖了 Jarvis 的全部模块。

> 来源：[Jarvis: A Cognitive Memory Architecture for AI-Augmented Learning](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5218379)

### 1.5 元认知技能追踪 MSKT（2025）

MSKT（Metacognitive Skills-driven Knowledge Tracing）论文的核心观点：传统知识追踪只跟踪"学生知道什么"，忽略了高阶元认知技能对学习的控制作用。

四个元认知维度：

| 维度 | 定义 | 弱表现 | 强表现 |
|------|------|--------|--------|
| **规划** (Planning) | 学习前制定策略 | 直接做题不先理解 | 先问框架再深入 |
| **监控** (Monitoring) | 学习中自我检测 | 以为懂了其实没有 | 能准确判断自己是否理解 |
| **调节** (Regulating) | 遇困难时调整策略 | 卡住就重复同样方法 | 主动换角度尝试 |
| **反思** (Reflecting) | 学习后总结评估 | 学完就忘不回顾 | 能总结今天学了什么 |

**我们的应用**：直接采用这四个维度作为 `metacognition` 的子字段。教师 LLM 根据元认知评估调整提问策略——如果 monitoring 弱，不能问"你懂了吗"（学生会说懂了但其实没懂），要用检测性问题验证理解。

> 来源：[Metacognitive Skills-driven Knowledge Tracing](https://www.sciencedirect.com/science/article/abs/pii/S0957417425028453)

### 1.6 Knowledge Tracing 综述

知识追踪（Knowledge Tracing）领域的关键概念：

**知识组件（Knowledge Component, KC）**：学习的最小单元。可以是一个概念、一个技能、一条规则。BKT 和 DKT 都以 KC 为基本追踪单位。

**两类 KC**：
- **Skill**（技能）：学生应该掌握的正确知识/操作
- **Misconception**（误解）：学生可能持有的错误知识

**知识追踪模型的输入**：
- 任务表现序列（对错）
- 知识组件标签
- 题目难度
- 时间特征（间隔、耗时）
- 行为信号（犹豫、反复修改）

**我们的应用**：
- KC 概念 → 我们的 knowledge 节点
- Skill vs Misconception 的区分 → 我们的 `type` 字段
- 时间特征 → 我们的 `t_valid` / `t_invalid` 时态模型
- 行为信号 → 通过情感分析间接获得（frustration ≈ 反复犯错的信号）

> 来源：[Knowledge Tracing: A Survey](https://dl.acm.org/doi/10.1145/3569576) / [Deep Knowledge Tracing 2015-2025 Systematic Review](https://www.preprints.org/manuscript/202510.1845)

---

## 二、综合映射

### 我们的 7 种记忆分类的学术依据

| 我们的分类 | Bloom | ITS 模型 | 认知科学 | Jarvis | MSKT | KT |
|-----------|-------|---------|---------|--------|------|-----|
| **事实知识** (knowledge) | Factual + Conceptual | Overlay (mastery) | 语义记忆 | 持久记忆 | — | KC (skill) |
| **概念关系** (edge) | Conceptual | — | 语义记忆 | 领域编排 | — | KC 依赖 |
| **误解** (misconception) | — | Perturbation | — | — | — | KC (misconception) |
| **程序性技能** (skill) | Procedural | Skill Tracing | 程序记忆 | — | — | KC (skill) |
| **交互摘要** (episode) | — | — | 情景记忆 | 持久记忆 | — | — |
| **学习偏好与情感** (preference/affect) | — | Learner Chars | — | 情感追踪 | — | — |
| **元认知** (metacognition) | Metacognitive | — | — | 元认知脚手架 | MSKT 4维度 | — |

### 为什么是这 7 种而不是更多或更少

- **不少于 7 种**：如果把 knowledge + misconception + skill 合并为一种"知识"，教师 LLM 无法区分"不知道"和"错误地知道"和"知道但不会做"——三者需要完全不同的教学策略。如果不单独追踪元认知，就无法判断学生说"我懂了"是真懂还是假懂。

- **不多于 7 种**：每增加一种分类，LLM 提取和维护的成本就增加。7 种已经覆盖了 Bloom 全部四类知识 + ITS 的扰动模型 + 认知科学的三种记忆 + Jarvis 的全部模块 + MSKT 的元认知。更细的粒度（如区分"表层误解"和"深层误解"）可以用字段（severity）而非新类型表达。

---

## 三、prompt 组装策略

基于以上理论，教师 LLM 收到的结构化信息应按教学意义分组，而非按存储结构分组：

```
【当前知识状态】— 源自 Bloom + Overlay Model
  已掌握(apply+): 递归(0.7), 变量作用域(0.8)
  学习中(understand): 终止条件(0.4)
  初识(remember): 尾递归优化(0.2)

【程序性技能】— 源自 Bloom Procedural + KT Skill
  能做: 编写阶乘函数(0.8), 读递归代码(0.7)
  需练习: 编写树遍历(0.3)

【⚠️ 误解】— 源自 ITS Perturbation Model
  [moderate] 认为递归一定需要函数自调用（未纠正）

【近期关键事件】— 源自 Episodic Memory
  [突破] 通过阶乘例子理解了 base case

【学习偏好】— 源自 ITS Learner Characteristics
  视觉化(0.8), 类比(0.7), 节奏慢

【情感模式】— 源自 Jarvis Emotional State Tracking
  挫折容忍低, 好奇心强, 对鼓励反应积极

【元认知】— 源自 MSKT 四维度
  规划中等, 自我监测弱, 调节中等, 反思强
```

**为什么这个顺序**：
1. 知识状态放最前——教师首先需要知道"教什么"
2. 技能状态紧随——"学生能做什么"决定出什么练习题
3. 误解用警告标记——教师必须避免强化错误认知
4. 近期事件提供上下文——"上次聊到哪了"
5. 偏好/情感/元认知放后面——影响"怎么教"而非"教什么"

---

## 四、时态行为的理论依据

### 为什么有些记忆随存档回滚，有些不回滚

**随存档回滚的**（事实知识、误解、技能、交互摘要）：

这些是**关于学习内容的记忆**——学生在特定时间点对特定主题的理解。从某个检查点分叉意味着"如果从那个时候重新来过"，所以这些记忆应该回到那个时候的状态。

类比：Galgame 中读档回到第三章，角色关系也应该回到第三章的状态。

**不回滚的**（学习偏好、情感模式、元认知）：

这些是**关于这个人的记忆**——学生作为一个学习者的特征。即使"回到过去"重新学习，这个人还是同一个人。

类比：现实中你不会因为重读一本书就忘记自己"喜欢视觉化学习"或"容易焦虑"。

但为了精确性，这些特征也带 `t_updated` 时间戳。分叉时间线中，如果某个特征是在检查点之后才被观察到的，那条时间线中不应该使用该特征（因为"在那个时候我们还不知道这一点"）。

---

*本文档记录设计决策的学术来源。具体实现方案见 `course_system_design.md`。*
