# 五大系统闭环架构设计 — 总览

> **版本**：v1.0.2
> **日期**：2026-04-24
> **状态**：设计中
> **详细设计**：[01 记忆系统](01_memory_system.md) | [02 学习画像](02_learner_profile.md) | [03 教学系统](03_teaching_system.md) | [04 叙事系统](04_narrative_system.md) | [05 游戏化系统](05_gamification_system.md)

---

## 核心原则：数据驱动，不硬编码

任何可能变化的东西——成就条件、策略阈值、画像维度、叙事触发规则——都不应写死在代码里。它们应该是数据库中的配置数据。代码只提供通用的执行引擎。

**判断标准**：如果明天要加一个新成就/新维度/新策略/新叙事事件，是改代码还是加一行数据？应该是后者。

---

## 闭环总览

### 核心循环（直接影响教学质量）

```
记忆系统 -> 学习画像 -> 教学系统 -> 学习过程 -> 新记忆
               ^                         |
               +-- 课程进度 <-------------+
```

### 观察者系统（只读主循环数据，产生副作用但不直接影响教学策略）

```
叙事引擎   -- 观察 --> MemoryFact/Relationship 变化 -> 触发事件 -> 前端弹窗
游戏化引擎 -- 观察 --> 画像变化 + 记忆变化 -> 解锁成就 -> 前端通知
```

---

## 现有代码盘点

| 系统 | 现有文件 | 行数 | 稳定性 | 本次改造 |
|------|---------|------|--------|---------|
| 记忆 | memory_facts.py + memory_extractor.py | 540 | 高 | 新建 Service Layer（MemoryManager） |
| 画像 | dynamic_analyzer.py | 285 | 中（结构不匹配 bug） | 修复 bug + 新增聚合器 |
| 教学 | prompt_builder/ | 425 | 高 | 新增 2 个 Module |
| 关系 | relationship.py | 106 | 高 | 不改 |
| 游戏化 | 无 | 0 | 全新 | 从零新建 |
| 叙事 | 无 | 0 | 全新 | 从零新建 |

---

## 各系统摘要

### 系统一：记忆系统

**核心改进**：新建 MemoryManager（Service Layer），修复 6 个现有问题。
- 单一入口（MemoryManager），一次到位
- Token 预算替代硬编码 30 条消息
- 记忆去重（同 type merge，不同 type 共存）
- 有效 salience 计算（按 fact_type 差异化衰减）
- retrieve（更新 recall_count）与 observe_recent（不更新）分离

**详细设计**：[01_memory_system.md](01_memory_system.md)

### 系统二：学习画像

**核心改进**：修复 profile 结构不匹配 bug + 新增 ProfileAggregator。
- 统一 Profile JSON 结构 v2（6 个一级 key，各有明确写入者）
- dynamic_analyzer 改为合并写（不覆盖其他系统的字段）
- 可扩展的维度系统（profile_dimension_defs 表）
- 5 种聚合方法（ratio/count/conversion_rate/keyword_extract/emotion_balance）

**详细设计**：[02_learner_profile.md](02_learner_profile.md)

### 系统三：教学系统

**核心改进**：新增 StrategyModule + RecallContextModule。
- 可配置的教学策略规则（strategy_rules 表）
- 基于画像维度值匹配 low/mid/high 策略指令
- RecallService 基于概念关联生成上下文化的记忆召回提示
- context 扩展 course_progress

**详细设计**：[03_teaching_system.md](03_teaching_system.md)

### 系统四：叙事系统

**核心改进**：从零新建 NarrativeEngine。
- 可配置的触发规则（narrative_trigger_rules 表）
- 6 种 condition_type 覆盖各类事件
- 英雄之旅节奏设计（困难=试炼，掌握=恩赐）
- 冷却机制防止打断学习

**详细设计**：[04_narrative_system.md](04_narrative_system.md)

### 系统五：游戏化系统

**核心改进**：从零新建 GamificationEngine。
- 内在动机优先（不使用积分/排行榜）
- 可配置的成就定义（achievement_defs 表）
- 6 种 condition_type + 6 种 category
- 隐藏成就 + 稀有度梯度
- 成就与叙事的联动通过数据配置实现

**详细设计**：[05_gamification_system.md](05_gamification_system.md)

---

## 新增数据库表汇总

| 表名 | 所属系统 | 用途 |
|------|---------|------|
| profile_dimension_defs | 画像 | 维度定义（可扩展） |
| strategy_rules | 教学 | 教学策略规则（可扩展） |
| narrative_trigger_rules | 叙事 | 叙事触发规则（可扩展） |
| achievement_defs | 游戏化 | 成就定义（可扩展） |
| achievements | 游戏化 | 成就解锁记录（运行时） |

**所有"规则表"都通过 migration 的种子数据初始化。**

---

## 新增文件清单

| 文件 | 层次 | 行数估计 |
|------|------|---------|
| memory_manager.py | 数据层（Service Layer） | ~200 |
| profile_aggregator.py | 业务层 | ~150 |
| recall_service.py | 业务层 | ~120 |
| narrative_engine.py | 观察者 | ~150 |
| gamification.py | 观察者 | ~120 |
| prompt_builder/modules/strategy.py | Module | ~60 |
| prompt_builder/modules/recall_context.py | Module | ~30 |

---

## 闭环强度评估

```
记忆 → 画像：✅ 强  ProfileAggregator 双数据源：MemoryFact + LearnerProfile.affect
画像 → 教学：✅ 强  StrategyModule 读取 dimension_scores
教学 → 学习：⚠️ 中  依赖 prompt 质量（架构层面无法加强，但画像驱动的策略注入是确定性保障）
学习 → 记忆：✅ 强  双通道提取：LLM 主动输出（通道1）+ 学生消息规则提取（通道2）
记忆 → 叙事：✅ 强  observe_recent 明确接口，写回约束为 event 类型
画像 → 成就：✅ 强  dimension_crossing 明确条件
概念关联：  ✅ 强  Course.concept_map 提供概念图谱 ground truth，RecallService 据此做前置关联
```

**修复后的闭环**：6/7 条链路强度为"强"。唯一不可架构层面加强的是"教学 → 学习"（LLM 教学质量），但 StrategyModule 的策略注入确保了 LLM 收到正确的画像信号。闭环效果的上限仍由 prompt 工程决定，但下限由双通道提取 + 概念图谱兜底。

---

## 可调参数集中管理

所有可能需要调优的参数集中到三层架构中，避免散落在代码各处。

### 第 1 层：config.py（系统级行为参数）

```python
# 新增到 Settings 类中
learning_system: dict = {
    "memory": {
        "dedup_window_hours": 24,          # 去重窗口
        "max_working_context_tokens": 4000, # 工作记忆 Token 预算
        "max_working_context_messages": 50, # 工作记忆消息上限
        "salience_base_decay": 0.1,        # salience 基础衰减率
        "salience_recall_factor": 0.5,     # 召回对衰减的减缓系数
        "default_retrieve_limit": 10,       # 默认检索条数
        "observe_recent_limit": 20,         # observe_recent 默认条数
    },
    "profile": {
        "hallucination_guard_min_facts": 3, # 聚合幻觉保护：最少事实条数
        "strength_threshold": 0.7,          # 优势标记阈值
        "weakness_threshold": 0.4,          # 弱势标记阈值
    },
    "extraction": {
        "channel2_enabled": True,           # 通道 2 开关
        "confusion_keywords": ["不懂", "没看明白", "什么意思", "不理解", "不明白"],
        "mastery_keywords": ["明白了", "懂了", "原来如此", "学会了", "理解了"],
        "emotion_negative_keywords": ["好难", "崩溃", "累了", "头疼", "放弃"],
        "preference_keywords": {
            "example_first": ["举个例子", "能举个例子吗", "比如呢"],
            "step_by_step": ["详细步骤", "一步一步", "能详细讲讲步骤吗"],
        },
        "confusion_question_mark_threshold": 0.3, # 问号密度阈值
    },
    "narrative": {
        "cooldown_storage": "memory",       # "memory" | "redis"（未来）
    },
}
```

**特点**：
- 所有参数可通过 `.env` 覆盖（pydantic_settings 天然支持）
- 不需要重启服务（`get_settings()` 可改为非 lru_cache 或增加刷新机制）

### 第 2 层：DB 规则表（业务规则）

| 表 | 可调参数示例 | 调整者 |
|----|------------|--------|
| profile_dimension_defs | 维度定义、聚合方法、参数 | 开发者 |
| strategy_rules | 策略阈值（low<0.4, high>0.7）、指令文本 | 开发者 |
| narrative_trigger_rules | 触发条件、冷却时间、事件模板 | 开发者 |
| achievement_defs | 解锁条件、稀有度、可见性 | 开发者 |

**特点**：新增维度/策略/成就 = 新增一行数据，不改代码。

### 第 3 层：DB 运行时数据（可扩展）

通道 2 的关键词表目前放在 config.py 中（第 1 层）。如果未来需要频繁扩展（比如支持日语/英语关键词），可迁移为 DB 表：

```sql
-- 未来扩展（当前不实现）
CREATE TABLE extraction_rules (
    id INTEGER PRIMARY KEY,
    signal_type VARCHAR(30),   -- confusion/mastery/emotion_negative/preference
    keywords JSON,             -- ["不懂", "没看明白", ...]
    output_fact_type VARCHAR(30),
    language VARCHAR(10) DEFAULT 'zh',
    enabled BOOLEAN DEFAULT TRUE
);
```

---

## 实施依赖图

```
Phase 2A: 记忆系统
  +-- memory_manager.py
  +-- 改造 learning_engine.py
      |
      +---> Phase 2B: 画像 + 教学系统
      |       +-- profile_dimension_defs + ProfileAggregator
      |       +-- strategy_rules + StrategyModule
      |       +-- RecallService + RecallContextModule
      |
      +---> Phase 2D: 叙事系统
      |       +-- narrative_trigger_rules + NarrativeEngine
      |
      +---> Phase 2E: 游戏化系统
              +-- achievement_defs + achievements + GamificationEngine

Phase 2F: 前端
  +-- 统一事件弹窗
  +-- 学习档案页
  +-- 成就页