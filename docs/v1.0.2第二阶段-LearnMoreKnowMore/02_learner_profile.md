# 系统二：学习画像（Learner Profile）— 详细设计

> **版本**：v1.0.2 | **日期**：2026-04-24 | **状态**：设计中
> **理论**：Zimmerman 自我调节学习三阶段（前思考/表现/反思）对应画像的偏好/状态/元认知；学生看到自己的画像本身就是元认知训练（Flavell）。

---

## 一、问题

| 编号 | 问题 | 阻碍 | 说明 |
|------|------|------|------|
| P1 | profile 结构不匹配 | **高** | dynamic_analyzer 写 `{preferences, affect, metacognition}`，create_seed_memories 读 `{metacognition_trend, learning_stats, preference_stability}`——完全不匹配 |
| P4 | 无跨会话聚合 | **高** | 画像只反映单次对话，无法积累学习特征 |
| P5 | 覆盖写 | **高** | dynamic_analyzer 的 `profile_row.profile = {...}` 覆盖其他系统写入的字段 |
| P2 | 偏好检测过于简陋 | 中 | 只检测"例子"和"步骤"两个关键词 |
| P3 | 元认知只有 self_confidence | 中 | 缺乏规划、监控、调节等维度 |

---

## 二、方案

### 2.1 统一 Profile 结构 v2

```json
{
    "affect": {"last_emotion": "...", "emotion_counts": {}, "emotion_trend": "..."},
    "preferences": {"example_first": true, "step_by_step": false},
    "learning_stats": {"total_sessions": 10, "concepts_mastered": 8, "concepts_struggling": 2},
    "metacognition": {"self_confidence": 0.7},
    "dimension_scores": {"abstract_thinking": 0.5, "problem_solving": 0.3},
    "dimension_snapshots": {"abstract_thinking": {"prev": 0.3, "updated_at": "..."}},
    "strengths": ["抽象思维"],
    "weaknesses": ["问题解决"]
}
```

**字段归属**（谁写、谁读）：

| 字段 | 写入者 | 读取者 |
|------|--------|--------|
| affect | dynamic_analyzer | PromptBuilder, 叙事引擎 |
| preferences | dynamic_analyzer | PromptBuilder, create_seed_memories |
| learning_stats | ProfileAggregator | create_seed_memories, 成就系统 |
| metacognition | dynamic_analyzer | create_seed_memories |
| dimension_scores | ProfileAggregator | StrategyModule, 成就系统 |
| dimension_snapshots | ProfileAggregator | 成就系统（检测维度跨越） |
| strengths/weaknesses | ProfileAggregator | 学生画像页, StrategyModule |

### 2.2 修复覆盖写（P5）

```python
# 改造前：覆盖写
profile_row.profile = {"preferences": ..., "affect": ..., "metacognition": ...}
# 改造后：合并写
existing = profile_row.profile if isinstance(profile_row.profile, dict) else {}
existing.update({"preferences": ..., "affect": ..., "metacognition": ...})
profile_row.profile = existing
```

### 2.3 可扩展的维度系统

**新增表：profile_dimension_defs**

| 字段 | 类型 | 说明 |
|------|------|------|
| key | String(50) UNIQUE | 维度标识 |
| display_name | String(100) | 显示名 |
| category | String(30) | "cognitive"/"metacognitive"/"affective" |
| source_fact_types | JSON Array | 数据来源 |
| aggregation_method | String(20) | 聚合方式 |
| aggregation_params | JSON | 聚合参数 |
| value_range | JSON | 值域 |
| enabled | Boolean | 是否启用 |

**聚合方法**：

| method | 计算逻辑 |
|--------|---------|
| ratio | 满足条件记录数 / 总记录数 |
| count | 指定类型记录数（归一化） |
| conversion_rate | struggle→mastered 转化比例 |
| keyword_extract | content 中关键词出现频率 |
| emotion_balance | 正面情绪计数 / 总情绪计数 |

**种子数据**：

| key | category | method |
|-----|----------|--------|
| abstract_thinking | cognitive | ratio |
| problem_solving | cognitive | conversion_rate |
| self_monitoring | metacognitive | keyword_extract |
| learning_resilience | affective | conversion_rate |
| engagement | affective | emotion_balance |

**新增维度 = 新增一行数据。**

### 2.4 ProfileAggregator

```
触发：learning_engine.process_message 末尾调用
流程：
  1. 读取 profile_dimension_defs（enabled=True）
  2. 保存当前 dimension_scores 作为 prev_snapshot
  3. 对每个维度：获取数据 → aggregate → clamp → save
  4. 计算 learning_stats（concept 计数）
  5. 计算 strengths（>0.7）/ weaknesses（<0.4）
  6. 合并写入 LearnerProfile.profile

幻觉保护：至少 3 条同类型 MemoryFact 才会生效。
不调 LLM，零 API 成本。
```

**双数据源**：ProfileAggregator 聚合不同类别的维度时需要不同输入：

| 维度类别 | 数据来源 | 获取方式 |
|---------|---------|---------|
| cognitive / metacognitive | MemoryFact | `MemoryManager.observe_recent()` |
| affective | LearnerProfile.affect | 直接读取 `profile_row.profile["affect"]` |

例如 `engagement` 维度用 `emotion_balance` 聚合，需要 `LearnerProfile.affect.emotion_counts`，这不是 MemoryFact 中的数据。

---

## 三、改造清单

| 文件 | 改动 | 说明 |
|------|------|------|
| `profile_aggregator.py` | **新建** ~150 行 | 维度聚合引擎 |
| `dynamic_analyzer.py` | **改** ~5 行 | 覆盖写→合并写 |
| `memory_facts.py` | **改** ~10 行 | create_seed_memories 适配统一 key |
| `models.py` | **改** | 新增 ProfileDimensionDef 模型 |
| `learning_engine.py` | **改** ~3 行 | 末尾增加 ProfileAggregator 调用 |

---

## 四、测试

| 测试 | 验证什么 |
|------|---------|
| test_profile_merge_write | 合并写不覆盖其他系统字段 |
| test_aggregator_ratio | ratio 聚合正确 |
| test_aggregator_hallucination_guard | < 3 条不更新维度 |
| test_strengths_weaknesses | 阈值（>0.7 强，<0.4 弱） |

---

## 五、实施步骤

```
Step 1: 修复 P1+P5（合并写 + 统一 key）
Step 2: 新增 profile_dimension_defs 表 + 种子数据
Step 3: 新建 ProfileAggregator
Step 4: 改造 learning_engine（末尾调用聚合）
Step 5: 测试