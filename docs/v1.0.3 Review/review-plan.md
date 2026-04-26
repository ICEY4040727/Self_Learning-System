# v1.0.3 Review 方案（基于代码审查细化版）

> **版本**: v1.0.3
> **日期**: 2026-04-25
> **状态**: Review 执行中
> **基线**: `v1.0.0-baseline` 至 HEAD (1d932d0)
> **测试基线**: 263 passed, 13 skipped

## 一、代码审查预检结论

在深入审查了核心模块后，**已发现 12 个确认问题**，按严重级别分类如下。这些发现将直接指导 Review 的重点方向。

---

## 二、已确认的 Findings（代码实证）

### Critical / High

#### [2A-01] [High] `evolve_salience()` 未实现 — 记忆衰减系统空缺

**Evidence**:
- `config.py:50-83` 定义了 `salience_base_decay`、`salience_recall_factor`、`salience_type_multiplier` 等参数
- 但 `memory_facts.py` 和 `memory_manager.py` 中 **没有任何调用这些参数的代码**
- 没有 `evolve_salience()` 函数或方法存在
- Plan A3 决策："Salience 演化参数可配置" → 参数已配置但逻辑未实现

**Impact**: 记忆重要度永远停留在初始值，不会随时间衰减或因召回增强。这意味着：
- 所有记忆的重要度排序失效
- `min_salience=0.3` 过滤形同虚设（所有新建记忆 salience >= 0.5）
- 记忆系统退化回简单的 FIFO

**Suggestion**: 实现 `evolve_salience()` 定时任务或在 `retrieve_memories()` 后触发衰减逻辑。

---

#### [2A-02] [High] `t_valid` / `t_invalid` 时态字段未迁移到 MemoryFact 模型

**Evidence**:
- `models.py:95-114` MemoryFact 表定义中 **没有** `t_valid` / `t_invalid` 列
- `prompt_builder/modules/misconception.py` 中读取了 `t_invalid`，但来源不明（可能是 JSON 字段或旧代码残留）
- `report.py` 中也使用了 `t_valid`，同样来源不明
- 没有 Alembic 迁移添加这两个列

**Impact**: Plan A5 决策未兑现。时态过滤依赖不存在的字段，可能导致：
- 误解纠正检测失效（misconception 模块检查 `t_invalid` 永远为 None → 所有误解永远"未纠正"）
- 学习报告中的时间线数据缺失

**Suggestion**: 添加 Alembic 迁移，在 MemoryFact 上增加 `t_valid`/`t_invalid` 列，并在记忆写入时设置 `t_valid`。

---

#### [2A-03] [High] 记忆去重未实现 plan 描述的规则分类器

**Evidence**:
- Plan A2 描述了 `find_similar_memory`、`is_upgrade`、`is_duplicate`、`shared_tags` 等规则分类器
- 实际代码 `memory_manager.py` 中只实现了简单的 **tag 匹配去重**（同 type + 同 tags → merge）
- 缺少升级检测（is_upgrade）：当新记忆是对旧记忆的细化/纠正时，无法识别

**Impact**: Plan A2-误判保护决策"保守阈值，宁可多建不误删"部分满足（简单合并确实保守），但无法识别记忆升级场景，可能导致重复记忆累积。

---

#### [2A-04] [High] `retrieve_memories()` 未更新召回追踪

**Evidence**:
- `memory_facts.py:79-129` 的 `retrieve_memories()` 方法返回结果后 **没有调用** `update_recall_count()`
- `update_recall_count()` 方法存在（131-137 行）但从未在 retrieve 流程中被调用
- Plan A4 决策："`retrieve_memories()` 末尾是否更新 `recall_count` 和 `last_recalled_at`" → **未实现**

**Impact**:
- `recall_count` 永远为 0
- `last_recalled_at` 永远等于 `created_at`
- Plan A3 保护规则 "recall_count > 5 的记忆永不自动清理" 无法生效
- 所有基于召回频率的逻辑（包括未来 salience 演化）失效

**Suggestion**: 在 `retrieve_memories()` 返回结果后，对每条返回的记忆调用 `update_recall_count()`。

---

### Medium

#### [2E-01] [Medium] Character 模型仍保留 `experience_points` 和 `level` 字段

**Evidence**:
- `models.py:154-155`: `experience_points = Column(Integer, nullable=False, default=0)` 和 `level = Column(Integer, nullable=False, default=1)`
- Plan E2 决策："**已删除** — 不做经验值系统"

**Impact**: 残留字段占用数据库空间，可能误导开发者以为有经验值功能。需要 Alembic 迁移删除。

---

#### [2E-02] [Medium] GamificationEngine 重复定义了 `stage_order` 列表

**Evidence**:
- `gamification.py:142`: `stage_order = ["stranger", "acquaintance", "friend", "mentor", "partner"]`
- `models.py:26-32`: `RELATIONSHIP_STAGE_LABELS = {"stranger": "初识", ...}`
- Plan E1-修正："复用 `relationship.py` 现有逻辑，不另搞映射" → 未完全遵守

**Impact**: 如果未来关系阶段列表变化，需要同步修改两处。

---

#### [2F-01] [Medium] 语义检索未实现 — 仍使用 ILIKE 模糊匹配

**Evidence**:
- `memory_facts.py:121`: `q = q.filter(MemoryFact.content.ilike(f"%{query}%"))`
- Plan F1："语义标签增强检索，多标签匹配替代纯 ILIKE" → **未实现**
- `concept_tags` 字段存在但未被用于检索

**Impact**: 记忆检索质量受限，无法通过概念标签进行精准匹配。

---

#### [2A-05] [Medium] `retrieve_memories()` 的 ILIKE 查询存在 SQL 注入风险

**Evidence**:
- `memory_facts.py:121`: `MemoryFact.content.ilike(f"%{query}%")` — `query` 参数直接拼入 SQL
- 虽然 SQLAlchemy 的 `ilike` 会参数化查询，但 `%` 和 `_` 通配符未转义，可能导致意外匹配

**Impact**: 安全风险较低（SQLAlchemy 参数化），但通配符注入可能导致非预期的记忆泄露。

---

#### [R1-01] [Medium] RecallService 未按 world_id 过滤记忆

**Evidence**:
- `recall_service.py:71-80`: 调用 `memory_manager.observe_recent()` 时 **未传 world_id**
- `profile_aggregator.py:224`: 同样调用 `observe_recent()` 时 **未传 world_id**
- 这意味着前置概念检查会包含其他世界的记忆事实

**Impact**: 跨世界概念混淆。如果学生在世界 A 学过"递归"且遇到了困难，在世界 B 教"递归"时会错误地提示"曾遇到困难"。

---

#### [R1-02] [Medium] NarrativeEngine._cooldowns 使用内存存储

**Evidence**:
- `narrative_engine.py:21`: `_cooldowns: dict[tuple[int, int, str], datetime] = {}`
- 服务器重启后冷却记录全部丢失，可能导致叙事事件短时间内重复触发

**Impact**: 非功能性缺陷，用户体验受影响但不会导致数据错误。

---

### Low

#### [2B-01] [Low] Plan 中 "A2 去重误判与 B3 记忆断层风险" 的关联提醒未在代码中体现

**Evidence**:
- Plan B3-关联："是否在代码注释或文档中建立了关联提醒" → 未找到相关注释

**Impact**: 纯文档/注释缺失，不影响功能。

---

#### [2C-01] [Low] CourseGenerator 未改名为 KnowledgeGraphGenerator

**Evidence**:
- `course_generator.py:90`: 类名仍为 `CourseGenerator`
- Plan C4："改名为 KnowledgeGraphGenerator"
- 但考虑到 C4-修正 "教材充实世界，不替代课程"，当前命名可能更合理

**Impact**: 命名一致性，无功能影响。

---

## 三、基于发现调整的 Review 执行计划

### 3.1 优先级调整

基于预检发现，**Phase 2A（记忆系统）是最高风险区域**，4 个 High 级别问题全部集中在此。Review 执行顺序调整为：

```
Phase R2.1（Phase 2A 记忆系统）← 最高优先，4 个 High
    ↓
Phase R1（架构级：数据流 + API 一致性）← 验证记忆系统缺陷的跨模块影响
    ↓
Phase R2.5（Phase 2E 游戏化）← 2 个 Medium（残留字段 + 重复定义）
    ↓
Phase R2.6（Phase 2F 语义检索）← 1 个 Medium（ILIKE 未替换）
    ↓
Phase R3（代码级审查）← 补充安全、性能检查
    ↓
Phase R2.2-R2.4（Phase 2B/2C/2D）← 预检中表现良好，优先级降低
    ↓
Phase R4（文档级）← 最后执行
```

### 3.2 预检中表现良好的模块

以下模块在预检中**未发现严重问题**，Review 时可快速通过：

| 模块 | 状态 | 依据 |
|------|------|------|
| Phase 2B NarrativeModule | ✅ 实现与设计一致 | `always_include=True`, `priority=10`, 从 World.scenes 读取 |
| Phase 2D NarrativeEngine | ✅ 纯规则引擎 | 不调 LLM，冷却机制正常，写回记忆正常 |
| Phase 2D Prompt 双通道 | ✅ 已实现 | NarrativeModule 注入 Prompt + 前端弹窗 |
| Phase 2E AchievementDef/Achievement | ✅ 数据模型完整 | 唯一约束、幂等解锁、分类体系 |
| Phase 2F MemoryFactsDrawer | ✅ 前端组件存在 | Learning.vue 中已集成 |
| Phase 5 tool_confirm 清理 | ✅ 已完成 | git 历史确认移除 |
| 集成流程 | ✅ learning_engine 流程完整 | 20 步有序执行，各观察者正确串联 |

### 3.3 需要深入审查的剩余区域

| 区域 | 审查重点 | 预计发现 |
|------|---------|---------|
| `memory_manager.py` | 去重逻辑细节、extract_and_store 流程 | 可能有更多简化 |
| `memory_extractor.py` | `<memory>` 标签提取、双通道提取 | 验证 A1 设计契约 |
| `save_file_manager.py` | 存档快照是否包含新 Phase 数据 | 可能遗漏教材/成就数据 |
| 前端 API 模块 | 新增端点是否都有前端调用 | 可能有未调用端点 |
| Alembic 迁移 | 是否有遗漏的迁移 | t_valid/t_invalid, 删除 experience_points |
| `relationship.py` | derive_stage() 是否被 gamification 复用 | 已确认未复用 |

---

## 四、Review 执行产出规范

### 4.1 问题编号（沿用预检编号）

预检已发现的 12 个问题编号如下，后续审查继续递增：

```
[2A-01] ~ [2A-05]  Phase 2A 记忆系统（5 个）
[2B-01]            Phase 2B Prompt 组装（1 个）
[2C-01]            Phase 2C 教材上传（1 个）
[2E-01] ~ [2E-02]  Phase 2E 游戏化（2 个）
[2F-01]            Phase 2F 语义检索（1 个）
[R1-01] ~ [R1-02]  架构级（2 个）
```

### 4.2 产出文件结构

```
docs/v1.0.3 Review/
├── review-plan.md          ← 本文件（含预检发现）
├── 00-问题汇总索引.md       ← 所有问题总览（含预检 12 个）
├── R1-架构级审查.md         ← 数据流 + API + 跨模块问题
├── R2-功能级审查.md         ← 按 Phase 的设计契约验证
├── R3-代码级审查.md         ← 重复/死代码/安全/性能
├── R4-文档级审查.md         ← 文档同步检查
└── review-summary.md       ← 最终结论（Approve/Comment/Request Changes）
```

### 4.3 Review 结论预测

基于预检发现的 4 个 High 级别问题（全部在 Phase 2A），**预测 Review 结论为 Request Changes**，阻塞项为：

1. **必须修复**: 2A-01（evolve_salience 未实现）、2A-04（召回追踪未实现）
2. **建议修复**: 2A-02（t_valid/t_invalid 缺失）、2A-03（去重简化）
3. **可延后**: 2E-01（残留字段）、2F-01（ILIKE 未替换）

---

## 五、Review 协作流程

### 5.1 执行顺序（基于优先级调整）

```
Step 1: 完成 R2.1（Phase 2A 深入审查）→ 确认 High 问题影响范围
    ↓
Step 2: 完成 R1（架构级）→ 验证跨模块影响
    ↓
Step 3: 完成 R2.5 + R2.6（游戏化 + 语义检索）
    ↓
Step 4: 完成 R3（代码级）→ 安全 + 性能
    ↓
Step 5: 完成 R2.2-R2.4 + R4（快速通过 + 文档）
    ↓
Step 6: 汇总 → review-summary.md
    ↓
Step 7: 通知 Owner
```

### 5.2 通知策略

- **立即通知**: 2A-01 ~ 2A-04 四个 High 问题（记忆系统核心功能缺失）
- **Review 完成后**: 完整的 review-summary.md
- **Request Changes**: 基于 Phase 2A 的 High 问题数量

### 5.3 测试验证状态

| 验证项 | 状态 | 说明 |
|--------|------|------|
| `pytest` | ✅ 263 passed | 全部通过 |
| `npm run build` | 待验证 | 需要执行 |
| 记忆去重专项测试 | 待验证 | 需检查 test_memory_facts.py 覆盖度 |
| 存档/读档集成测试 | 待验证 | 需检查 test_save_file_manager.py |

---

## 六、风险预判更新

基于代码审查，更新风险矩阵：

| 风险 | 原评估 | 代码验证后 | 说明 |
|------|--------|-----------|------|
| 记忆去重误删 | 中 | **低** ✅ | 实际实现非常保守（简单 tag 匹配合并） |
| Salience 演化缺失 | 未预判 | **确认 High** ❌ | 整个衰减系统未实现 |
| 召回追踪缺失 | 未预判 | **确认 High** ❌ | update_recall_count 存在但未被调用 |
| 时态字段缺失 | 未预判 | **确认 High** ❌ | 模型无此列 |
| Prompt 组装顺序 | 高 | **低** ✅ | NarrativeModule 正确实现 |
| 叙事引擎通用性 | 中 | **低** ✅ | 纯规则引擎，不耦合具体文本 |
| 成就/narrative 共享弹窗 | 中 | **待验证** | 前端需进一步检查 |
| 经验值残留 | 未预判 | **确认 Medium** ❌ | Character 模型仍有字段 |
| API 端点未调用 | 中 | **待验证** | 需对比前后端 |
| 存档快照遗漏 | 中 | **待验证** | 需检查 save_file_manager |

---

## 七、总结

### 预检核心结论

**Phase 2A（记忆系统）的实现完成度约 40%**：
- ✅ 已实现：记忆写入（write_memory_facts）、基础检索（retrieve_memories）、种子记忆（create_seed_memories）、简单去重、过期清理
- ❌ 未实现：salience 演化、召回追踪、时态字段、规则分类器去重、语义检索

**Phase 2B-2F 和架构集成表现良好**：
- ✅ Prompt 组装模块化正确
- ✅ 叙事引擎纯规则、不调 LLM
- ✅ 成就系统数据模型完整
- ✅ learning_engine 20 步流程完整串联
- ⚠️ 游戏化有残留字段和重复定义
- ⚠️ RecallService 有跨世界泄漏风险

> **下一步**: 按 3.1 调整后的优先级执行完整 Review，产出各层审查文档。