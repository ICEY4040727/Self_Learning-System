# 系统五：游戏化系统（GamificationEngine）— 详细设计

> **版本**：v1.0.2 | **日期**：2026-04-24 | **状态**：设计中
> **理论参考**：SDT 自我决定理论、PBL 框架、Octalysis 八种核心驱动力

---

## 一、定位

**观察者，不直接影响教学策略。** 检测成就条件，记录解锁，通过前端通知产生成就感。

**设计依据**：
- 自我决定理论（SDT）：成就应满足胜任感，而非外部奖励（过度理由效应：积分/代币会**削弱**内在动机）
- **不使用积分和排行榜**；成就解锁应是不可预见的惊喜；条件应反映真实学习进步
- Octalysis 核心驱动力：史诗意义（历险）、进步感（维度提升）、稀缺性（隐藏成就）、不可预见性（惊喜）

---

## 二、设计方案

### 2.1 可配置的成就定义

**新增表：achievement_defs**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增 |
| key | String(50) UNIQUE | 成就标识 |
| display_name | String(100) | 显示名 |
| description | Text | 描述 |
| category | String(20) | 分类 |
| condition_type | String(30) | 条件类型 |
| condition_params | JSON | 条件参数 |
| rarity | String(10) | "common"/"rare"/"legendary" |
| icon | String(50) | 图标 |
| hidden | Boolean | 解锁前是否可见 |
| enabled | Boolean | 是否启用 |

#### category 枚举

| category | 含义 | 对应驱动力 |
|----------|------|-----------|
| milestone | 里程碑 | 进步感 |
| growth | 成长 | 胜任感 |
| relationship | 关系 | 社交影响 |
| resilience | 韧性 | 史诗意义 |
| exploration | 探索 | 创造力 |
| hidden | 隐藏 | 不可预见性 |

#### condition_type 枚举

| condition_type | 含义 |
|---------------|------|
| stat_threshold | 学习统计达到阈值 |
| dimension_crossing | 画像维度跨越阈值 |
| relationship_stage | 关系达到指定阶段 |
| fact_transition | 记忆类型转化（struggle->mastered） |
| fact_count_threshold | 特定类型记忆达到数量 |
| consecutive_days | 连续学习天数 |

### 2.2 种子数据

**里程碑**：初入世界(1次学习)、常客(10次)、小有所成(5概念)、学有所长(20概念)

**成长**：抽象思维觉醒(维度跨越)、问题解决者

**韧性**：吃一堑长一智(struggle->mastered)、百折不挠(10次转化)

**关系**：心意相通(friend)、亦师亦友(trusted_partner)

**隐藏**：夜猫子(23点后学习)、马拉松选手(单次50条消息)

**新增成就 = 新增一行数据。**

### 2.3 解锁记录

**新增表：achievements**

| 字段 | 说明 |
|------|------|
| user_id | 用户 |
| character_id | 角色 |
| achievement_key | 关联 achievement_defs.key |
| unlocked_at | 解锁时间 |
| context | 解锁上下文（如哪个概念） |

唯一约束：`(user_id, character_id, achievement_key)` 防重复。

### 2.4 GamificationEngine 工作流程

```
1. 查询 achievement_defs（enabled=True）
2. 排除已解锁的
3. 对每条未解锁的：检查条件 -> 满足则插入记录
4. 返回新解锁列表
```

**幂等保证**：唯一约束防止重复解锁。
**不调 LLM**，零 API 成本。

### 2.5 与叙事系统协作

成就解锁可触发叙事事件——通过 narrative_trigger_rules 数据配置，不改代码：

```
trigger_type: "achievement_unlocked"
condition_params: {"achievement_key": "learn_from_setback"}
event_template: "你从失败中站了起来！"
```

### 2.6 与前端交互

```json
{"response": "...", "new_achievements": [{"key": "learn_from_setback", "display_name": "吃一堑长一智", "rarity": "rare", "context": {"concept": "递归"}}]}
```

展示策略：rare/legendary 全屏庆祝动画，common 用 toast，隐藏成就额外标签。

### 2.7 学生成就 API

```
GET /api/worlds/{world_id}/achievements
返回：{unlocked: [...], locked_visible: [...], total_unlocked, total_available}
```

---

## 三、新增/修改文件

| 文件 | 操作 |
|------|------|
| gamification.py | 新建 ~120 行 |
| models.py | 修改（新增 AchievementDef, Achievement） |
| learning_engine.py | 修改（末尾调用） |
| API route | 新增 GET achievements |

---

## 四、测试

| 测试 | 验证什么 |
|------|---------|
| test_stat_threshold | total_sessions >= 1 触发 |
| test_dimension_crossing | prev=0.3->current=0.6 检测 |
| test_idempotent | 不重复解锁 |
| test_hidden_not_in_locked | 隐藏成就不在 locked_visible |

---

## 五、设计原则

| 原则 | 做法 | 不做 |
|------|------|------|
| 内在动机优先 | 标记真实进步 | "登录送积分" |
| 惊喜感 | 隐藏成就 | 透明成就列表 |
| 不破坏学习节奏 | 观察者模式，不调 LLM | 额外 LLM 调用 |
| 数据驱动 | DB 配置 | if/elif 硬编码 |
