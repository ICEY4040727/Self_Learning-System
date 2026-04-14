# 前后端联调重构计划（Draft）

> **状态**: DRAFT — 待 Owner/Creator/Reviewer 三方讨论确认
> **提出者**: Reviewer
> **日期**: 2026-04-14
> **关联文档**: [前端重构七层次总结](./前端重构七层次总结.md) | [问题汇总索引](./00-问题汇总索引.md)

---

## 1. 背景

`前端重构七层次总结.md` 规划了前端 14 项问题的分阶段重构，但原文档明确标注"不涉及后端代码修改"。经过 Reviewer 审查，**前端至少 5 项问题的正确解决依赖后端先完成重构**：

| 前端问题 | 后端阻塞项 | 原因 |
|----------|-----------|------|
| #29 API 调用统一 | #06 save.py 遗留接口 | 前端不确定最终使用 `/save` 还是 `/checkpoints` |
| #31 角色模板 key 统一 | 后端 PERSONA_TEMPLATES key 已部分修复 | `characterPresets.ts` 的 `socratic` vs `socrates` 仍不一致 |
| #32 worldStore 去留 | #07 archive.py 死代码 | world 的 API 结构未稳定 |
| #33 error-toast 统一 | 后端错误响应格式 | 部分端点错误格式不一致 |
| #22 背景图片统一 | 后端 world scenes 配置 | scenes 返回结构不统一 |

**结论**：需要制定前后端联动计划，按依赖关系排序执行。

---

## 2. 后端遗留问题（合并为 4 个集群）

### 集群 A：save.py 减肥（#01, #06, #12, #20）

| 问题 | 严重度 | 当前状态 |
|------|--------|---------|
| #06 遗留接口 150 行 | 高 | ❌ 未解决 |
| #20 ChatMessage 查询重复 6 次 | 高 | ❌ 未解决 |
| #12 ChatMessage 重复导入 | 低 | ❌ 未解决 |
| #01 save.py stage_map 未统一 | 中 | ⚠️ 部分解决 |

**预期收益**: save.py 888→~600 行

### 集群 B：死代码清除（#07, #09, #11, #17）

| 问题 | 严重度 | 当前状态 |
|------|--------|---------|
| #17 两套关系算法（算法B死代码） | 高 | ✅ 已确认死代码，未删除 |
| #07 _ensure_world_knowledge 空操作 | 中 | ❌ 未解决 |
| #11 _get_world_sages 死代码 | 低 | ❌ 未解决 |
| #09 HOT RELOAD 注释 | 低 | ❌ 未解决 |

**预期收益**: 删除 ~100 行死代码

### 集群 C：架构修复（#10, #18）

| 问题 | 严重度 | 当前状态 |
|------|--------|---------|
| #18 服务层自管 DB 连接 | 高 | ❌ 未解决 |
| #10 tool_confirm 占位接口 | 中 | ❌ 未解决 |

**预期收益**: 消除 DB 连接泄漏风险

### 集群 D：前端清理（#16, #02）

| 问题 | 严重度 | 当前状态 |
|------|--------|---------|
| #16 buildTraitsPayload 恒等函数 | 低 | ❌ 未解决 |
| #02 Limiter 实例重复 | 低 | ❌ 未解决 |

**预期收益**: 代码清晰度提升

---

## 3. 联调重构计划（5 个 Phase）

### Phase 0 — 后端死代码清除
> **前置条件**: 无 | **风险**: 极低 | **预估工作量**: 0.5 天

**后端任务**:
- [ ] #17 删除 `dynamic_analyzer.update_relationship_stage`（~46 行）
- [ ] #07 删除 `_ensure_world_knowledge` 函数 + 3 处调用
- [ ] #11 删除 `_get_world_sages` 函数
- [ ] #09 删除 `# HOT RELOAD TEST` 注释

**前端任务**: 无

**验收**: `pytest` 通过 + `python -c "import ast; ..."` 语法检查

---

### Phase 1 — 后端 save.py 重构
> **前置条件**: Phase 0 完成 | **风险**: 中 | **预估工作量**: 1-2 天

**后端任务**:
- [ ] #06 删除遗留 save 接口（/save, /save/{id}, GET /save 列表）→ -150 行
- [ ] #20 提取 `_get_session_messages()` + `_count_session_messages()` 辅助函数
- [ ] #12 清理 ChatMessage 重复导入
- [ ] #01 save.py stage_map 替换为 `RELATIONSHIP_STAGE_LABELS`

**前端任务**:
- [ ] 确认前端是否仍调用 `/save/*` 遗留接口 → 如果有，迁移到 `/checkpoints/*`

**验收**: `pytest` 通过 + save.py < 650 行

---

### Phase 2 — 前端清理（低风险）
> **前置条件**: 无（可与 Phase 0/1 并行）| **风险**: 极低 | **预估工作量**: 0.5 天

**前端任务**:
- [ ] #24 删除所有 `[DEBUG]` 日志（~12 行）
- [ ] #28 删除 `home-bg.jpg`（未引用）
- [ ] #23 统一或删除 `MOCK_CHARACTERS`
- [ ] #25 统一 `page-fade` CSS（只保留一处定义）
- [ ] #16 删除 `buildTraitsPayload` 恒等函数
- [ ] #35 简化 `client.ts` refresh 方法（删除 `data.data ?? data`）

**后端任务**: 无

**验收**: `npm run build` 通过

---

### Phase 3 — 前后端联调
> **前置条件**: Phase 0 + Phase 1 + Phase 2 完成 | **风险**: 中 | **预估工作量**: 2-3 天

**后端任务**:
- [ ] #18 简化 `update_learner_profile` 签名（移除 `db=None` fallback）
- [ ] #10 决策：`tool_confirm` 实现还是删除？
- [ ] #02 统一 Limiter 实例到一处

**前端任务**:
- [ ] #30 分离 `types/index.ts`（常量 → `constants/uiConstants.ts`）
- [ ] #31 合并角色模板（`characterPresets.ts` + `personaTemplates.ts` → 统一一份）
  - ⚠️ 需确认最终 key 命名：`socratic` vs `socrates`
- [ ] #33 提取 `useAsync` composable + 全局 `ErrorToast` 组件
- [ ] #36 从 `_build_start_response` 中删除 `character_sprites` legacy alias

**验收**:
- 后端: `pytest` 通过
- 前端: `npm run build` 通过 + 无 TypeScript 错误
- 联调: 角色创建流程端到端测试通过

---

### Phase 4 — 前端架构统一
> **前置条件**: Phase 3 完成 | **风险**: 高 | **预估工作量**: 2-3 天

**前端任务**:
- [ ] #32 决策：使用 `useWorldStore` 还是删除？
- [ ] #29 统一 API 调用方式（全部走 Store 或全部走 API 模块）
- [ ] #22 统一背景/样式系统
- [ ] #27 替换 `alert()` 为 toast
- [ ] #26 清理重复组件文件名

**后端任务**:
- [ ] 配合前端确认最终 API 列表和响应格式

**验收**:
- 全部 e2e 测试通过
- 无 View 直接 `import client`
- 无 `alert()` 调用

---

## 4. 执行依赖图

```
Phase 0 (后端死代码) ──→ Phase 1 (save.py 重构) ──→ Phase 3 (联调) ──→ Phase 4 (前端架构)
                                                       ↑
Phase 2 (前端清理) ────────────────────────────────────┘
```

Phase 0 和 Phase 2 可并行执行。

---

## 5. 需要三方讨论的决策点

### ⚖️ 决策 1: save.py 遗留接口删除时机
- **选项 A**: Phase 1 立即删除（推荐）→ 前端 Phase 4 可直接基于 `/checkpoints` 统一
- **选项 B**: 标记 deprecated，v1.1.0 再删 → 前端需兼容两套
- **Reviewer 建议**: 选 A，前端已迁移到 checkpoints

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | ✅ 选 A | 前端 Learning.vue 和 CheckpointPanel.vue 都已使用 `/checkpoints/*`，`/save/*` 无前端调用，立即删除无风险 |
| **Reviewer** | 建议选 A | 见上文 |
| **Owner** | A 删除过程中如果有未迁移到 checkpoints的，必须写文档记录| |

</details>

### ⚖️ 决策 2: 前端 Store vs API 模块
- **选项 A**: 使用 Store（`useWorldStore`）→ 跨组件共享、缓存
- **选项 B**: 使用 API 模块（`characterApi` 等）→ 轻量
- **选项 C**: 混合（列表页用 Store，详情页直接 API 调用）
- **Reviewer 建议**: 需 Creator 评估工作量和收益

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | ✅ 选 A（Store 模式） | 1) `useWorldStore` 已定义 139 行完整 CRUD，只差被使用；2) Worlds/WorldDetail/Character 多页面需共享 worlds/characters 数据；3) 删除 worldStore 再裸调 API 本质上没解决重复问题；预估工作量：迁移 3 个 View 约 1 天 |
| **Reviewer** | 需 Creator 评估 | 见上文 |
| **Owner** | 可以选A 但必须搞清是否有API模块实现但Store未实现功能，如果有，需写入文档供useWorldStore功能补全| |
| **Reviewer** | ✅ 已调查，见下方功能对比分析 | |

</details>

### ⚖️ 决策 3: 角色模板 key 最终命名
- 后端已支持 `socrates` + `苏格拉底型` 双 key
- 前端 `characterPresets.ts` 用 `socratic`，`personaTemplates.ts` 用 `socrates`
- **需确认**: 统一为 `socrates` 还是 `socratic`？

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | ✅ 统一为 `socrates` | 1) 后端已支持 `socrates` 作为主 key；2) `personaTemplates.ts`（CreatePersonaModal 使用）已用 `socrates`；3) 只需修改 `characterPresets.ts` 一个文件 |
| **Reviewer** | _待定_ | |
| **Owner** | socrates | |
| **Reviewer** | ✅ 已调查，见下方分析 | |

</details>

### ⚖️ 决策 4: tool_confirm 接口处置
- **选项 A**: 删除（当前为 placeholder，无实际功能）
- **选项 B**: 实现（需定义工具执行框架）
- **Reviewer 建议**: 选 A，无使用场景

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | ✅ 选 A（删除） | 无使用场景，是 v0.x 遗留占位代码，删除可减少 API 表面积 |
| **Reviewer** | 建议选 A | 见上文 |
| **Owner** | A删除 | |

</details>

### ⚖️ 决策 5: Phase 2/3 是否可并行
- Phase 2（前端清理）不依赖后端改动
- Phase 3（联调）需要 Phase 0+1 完成
- **问题**: Phase 2 是否与 Phase 0/1 并行，还是等后端先完成？

<details>
<summary>💬 讨论区</summary>

| 角色 | 意见 | 理由 |
|------|------|------|
| **Creator** | ✅ 建议并行 | Phase 2 全是前端删除操作（DEBUG 日志、冗余资源、MOCK 数据），零后端依赖。可立即开始 Phase 0 + Phase 2，不等后端 |
| **Reviewer** | _待定_ | |
| **Owner** | 不并行 | creator整理过前端问题，我相信creator,但我认为不并行能减少潜在问题。 |

</details>

---

## 5.5 Reviewer 技术调查（回应 Owner 疑问）

### 📋 决策 2：characterApi vs useWorldStore 功能对比

| 功能 | characterApi | useWorldStore | 差异说明 |
|------|:---:|:---:|------|
| 角色 CRUD (list/create/delete) | ✅ | ✅ | Store 和 API 都有 |
| 角色详情 (get by id) | ✅ | ❌ | **Store 缺失** |
| 角色更新 (update) | ✅ | ❌ | **Store 缺失** |
| 角色头像上传 (uploadAvatar) | ✅ | ❌ | **Store 缺失** |
| 角色统计 (getStats) | ✅ | ❌ | **Store 缺失** |
| 角色升级 (levelup) | ✅ | ❌ | **Store 缺失** |
| 世界 CRUD | ❌ | ✅ | API 无 world 模块 |
| 课程 CRUD | ❌ | ✅ | API 无 course 模块 |
| 世界-角色绑定 | ❌ | ✅ | API 无此功能 |
| 时间线 | ❌ | ✅ | API 无此功能 |
| 存档点/分支 | ❌ | ✅ | API 无此功能 |
| 状态管理 (select/reset) | ❌ | ✅ | Store 独有 |

**结论**:
- characterApi 有 5 个方法是 Store 未实现的：, , , , 
- useWorldStore 有 7 个功能域是 API 未覆盖的：World/Course/Timeline/Checkpoint/绑定/选择状态管理
- **建议**: 如果选 Store 模式，需补全 5 个缺失方法；如果选 API 模块，需新增 world.ts + course.ts

### 📋 决策 3：socrates vs socratic 详细分析

| 维度 | socrates | socratic |
|------|----------|----------|
| **使用位置** | personaTemplates.ts, CreatePersonaModal.vue | characterPresets.ts |
| **用途** | 角色创建时的模板选择 | 角色预设列表的 key |
| **含义** | 人名（苏格拉底，哲学家） | 形容词（苏格拉底式的，教学法） |
| **后端** | 已支持作为主 key | 无此 key |
| **指向** | 同一个苏格拉底型角色模板 | 同一个苏格拉底型角色模板 |

**结论**:  和  指向完全相同的角色模板，只是命名风格不同。建议统一为 （与后端主 key 一致），只需修改  一个文件。


## 6. 风险评估

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| save.py 删除遗留接口后前端有遗漏调用 | 中 | 高 | 全局搜索 `/save` 引用 |
| 角色模板 key 变更导致已有数据不兼容 | 低 | 高 | 后端双 key 兼容已实现 |
| Phase 4 架构变更引入新 bug | 中 | 中 | 每个 Phase 独立 PR + 回归测试 |
| dynamic_analyzer 删除后影响其他引用 | 极低 | 低 | 已确认零调用 |

---

## 7. 讨论记录

| 日期 | 参与者 | 讨论内容 | 结论 |
|------|--------|---------|------|
| 2026-04-14 | Creator | 对草案提出 3 个问题：编号未注册、✅ 问题需补充 PR 来源、#04/#36 矛盾 | Reviewer 已修复 |
| 2026-04-14 | Creator | 决策 1-5 全部给出意见（见各决策区） | 待 Owner 确认 |
| 2026-04-14 | Reviewer | 修复索引：#34/#35/#36 正式注册、#04 改为 ⚠️ 部分解决 | 已更新 |
| 2026-04-14 | Owner | 决策 1: 选 A 但需文档记录未迁移项 | ✅ 有条件通过 |
| 2026-04-14 | Owner | 决策 2: 可选 A 但需功能对比文档 | ✅ Reviewer 已补充 |
| 2026-04-14 | Owner | 决策 3: 想 socrates/socratic 区别 | Reviewer 已调查 |
| 2026-04-14 | Owner | 决策 4: 删除后重建是否有困难 | Reviewer 确认零风险 |
| 2026-04-14 | Owner | 决策 5: 不并行 | ✅ 最终决定 |
| 2026-04-14 | Reviewer | 补充决策 2/3/4 技术调查报告 | 已写入 5.5 节 |

### ✅ 已确认问题的 PR 来源（回应 Creator 质疑）

| 问题 | 修复方式 | PR |
|------|---------|-----|
| #03 版本号硬编码 | config.py app_version + main.py 替换 | #221 |
| #04 character_sprites | 提取 _build_start_response（legacy alias 保留为 #36） | #219 |
| #08 STAGE_LABELS 重复 | 删除 types/index.ts 中 STAGE_LABELS，迁移引用 | #220 |
| #14 session 查询重复 | 提取 _get_active_session + _get_session_characters | #219 |

**说明**: #04 标记改为 ⚠️ 部分解决，legacy alias 完全清除归入 #36（Phase 3）。

---

## 附录：问题完整状态

| # | 问题 | 状态 | 所属 Phase |
|---|------|------|-----------|
| 01 | stage_map 重复 | ⚠️ 部分解决 | Phase 1 |
| 02 | Limiter 重复 | ❌ | Phase 3 |
| 03 | 版本号硬编码 | ✅ | — |
| 04 | character_sprites 冗余 | ⚠️ 部分解决（→ #36） | Phase 3 |
| 05 | start_learning 返回重复 | ✅ | — |
| 06 | save.py 遗留接口 | ❌ | Phase 1 |
| 07 | _ensure_world_knowledge 空操作 | ❌ | Phase 0 |
| 08 | 前端 STAGE_LABELS 重复 | ✅ | — |
| 09 | HOT RELOAD 注释 | ❌ | Phase 0 |
| 10 | tool_confirm 占位 | ❌ | Phase 3 |
| 11 | _get_world_sages 死代码 | ❌ | Phase 0 |
| 12 | ChatMessage 重复导入 | ❌ | Phase 1 |
| 13 | user-profile 格式不一致 | ✅ | — |
| 14 | session 查询重复 | ✅ | — |
| 15 | 角色模板 key 不匹配 | ✅ | — |
| 16 | buildTraitsPayload 恒等 | ❌ | Phase 2 |
| 17 | 两套关系算法 | ⚠️ 确认死代码 | Phase 0 |
| 18 | 自管 DB 连接 | ❌ | Phase 3 |
| 19 | SAVE_DIR 硬编码 | ✅ | — |
| 20 | ChatMessage 查询重复 | ❌ | Phase 1 |
| 22 | 背景图片硬编码 | ❌ | Phase 4 |
| 23 | MOCK 重复 | ❌ | Phase 2 |
| 24 | DEBUG 日志 | ❌ | Phase 2 |
| 25 | page-fade 冲突 | ❌ | Phase 2 |
| 26 | 组件文件名重复 | ❌ | Phase 4 |
| 27 | alert vs toast | ❌ | Phase 4 |
| 28 | 冗余资源 | ❌ | Phase 2 |
| 29 | API 模块未使用 | ❌ | Phase 4 |
| 30 | types 混合常量 | ❌ | Phase 3 |
| 31 | 角色模板重复 | ❌ | Phase 3 |
| 32 | worldStore 未使用 | ❌ | Phase 4 |
| 33 | error-toast 重复 | ❌ | Phase 3 |