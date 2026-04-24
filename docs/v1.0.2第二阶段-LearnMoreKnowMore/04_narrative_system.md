# 系统四：叙事系统（NarrativeEngine）— 详细设计

> **版本**：v1.0.2 | **日期**：2026-04-24 | **状态**：设计中
> **理论参考**：Campbell 英雄之旅、Bruner 叙事心理学、Csikszentmihalyi 心流理论

---

## 一、定位

**观察者，不直接影响教学策略。** 通过 MemoryManager.observe_recent() 观察 MemoryFact 和 Relationship 变化，触发叙事事件。

**设计依据**：
- 英雄之旅（Campbell）：困难=试炼，掌握=恩赐，关系提升=蜕变——学习过程天然是历险叙事
- 叙事心理学（Bruner）：人类通过故事组织经验，叙事事件把学习"故事化"
- 心流理论：叙事不应干扰学习节奏，冷却时间确保不频繁打断

---

## 二、设计方案

### 2.1 可配置的触发规则

**新增表：narrative_trigger_rules**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增 |
| trigger_type | String(50) UNIQUE | 触发器标识 |
| display_name | String(100) | 显示名 |
| condition_type | String(30) | 条件类型 |
| condition_params | JSON | 条件参数 |
| priority | String(10) | "high"/"medium"/"low" |
| writeback_memory | Boolean | 是否写回 MemoryFact |
| cooldown_minutes | Integer | 冷却时间 |
| event_template | Text | 事件模板（支持 {concept} 变量替换） |
| prompt_template | Text | prompt 注入模板 |
| ui_template | String(20) | "toast"/"modal"/"badge" |
| enabled | Boolean | 是否启用 |

### 2.2 condition_type 枚举

| condition_type | 含义 |
|---------------|------|
| fact_created | 指定类型 MemoryFact 被创建 |
| fact_count_threshold | 时间窗口内同组事实达到阈值 |
| relationship_stage_change | 关系阶段变化 |
| profile_shift | 画像维度变化超过阈值 |
| session_event | Session 开始/结束 |
| time_gap | 距上次学习超过 N 天 |

### 2.3 种子数据

| trigger_type | condition | event_template | cooldown |
|-------------|-----------|---------------|----------|
| concept_mastered | fact_created: concept_mastered | 你成功掌握了「{concept}」！ | 5min |
| struggle_cascade | fact_count_threshold: struggle x3 | 「{concept}」似乎是一座难以翻越的山... | 60min |
| breakthrough | fact_transition: struggle->mastered | 经历了重重困难，你终于征服了「{concept}」！ | 30min |
| stage_change | relationship_stage_change | 你和导师的关系更近了一步。 | 120min |
| welcome_back | time_gap: 3 days | 好久不见！欢迎回到这个世界。 | 1440min |

**新增叙事事件 = 新增一行数据。**

### 2.4 NarrativeEngine 工作流程

```
触发：learning_engine.process_message 末尾调用
输入：MemoryManager.observe_recent() 获取近期记忆变化
流程：
  1. 查询 narrative_trigger_rules（enabled=True）
  2. 对每条规则：检查条件 -> 检查冷却 -> 生成事件
  3. 冷却存储：内存 dict {(user_id, character_id, trigger_type): last_time}
  4. 返回事件列表（按 priority 排序）
不调 LLM，零 API 成本。
```

**观察者约束**：叙事引擎是观察者，不能污染核心闭环。如果 `writeback_memory=True`，写入的 MemoryFact 的 fact_type 必须是 `event`——不与核心闭环的 fact_type（struggle/mastered/preference）竞争。

### 2.5 闭环中的位置

叙事系统处于闭环之外，是纯观察者：

```
核心闭环：记忆 → 画像 → 教学 → 学习 → 新记忆
观察者：                                        ↓
                              NarrativeEngine ←─┘
                                    ↓
                              前端弹窗 / 事件写回(event)
```

它不影响教学策略，但通过叙事事件增强学习体验（galgame 风格）。写回的 event 类型记忆可以被 MemoryManager.retrieve() 召回，作为"你之前经历过什么"的上下文，但不会被 ProfileAggregator 用于维度计算。

### 2.6 与前端交互

```json
{"response": "...", "narrative_events": [{"type": "concept_mastered", "text": "...", "ui_template": "toast"}]}
```

---

## 三、新增/修改文件

| 文件 | 操作 |
|------|------|
| narrative_engine.py | 新建 ~150 行 |
| models.py | 修改（新增 NarrativeTriggerRule） |
| learning_engine.py | 修改（末尾调用） |

---

## 四、测试

| 测试 | 验证什么 |
|------|---------|
| test_fact_created_trigger | concept_mastered 触发 |
| test_cooldown_enforcement | 冷却期不重复 |
| test_template_replacement | {concept} 替换 |
| test_writeback_memory | 事件写回 |

---

## 五、风险

| 风险 | 方案 |
|------|------|
| 叙事过多 | cooldown + 免打扰 |
| 叙事过少 | DB 调整 |
| 内存冷却丢失 | 可接受 |
