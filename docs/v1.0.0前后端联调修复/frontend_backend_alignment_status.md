# 前后端对齐状态标记文档

> **生成时间**: 2026-04-07  
> **最后更新**: 2026-04-08  
> **依据文档**: 
> - `docs/frontend_backend_fix_plan.md`
> - `docs/UI迁移书.md`
> - `docs/vue3_migration_contract_adaptation.md`
> - `docs/archive_improvement_plan.md`

---

## 一、已修复问题汇总

| # | 问题 | 状态 | 说明 |
|---|------|------|------|
| 1 | WorldDetail.vue checkpoint API 路径错误 | ✅ **已修复** | `WorldDetail.vue:178` 改为 `/save?subject_id=${courseId}` |
| 2 | UserProfile.refresh 响应处理 | ✅ 已修复 | `client.ts:48-52` 已处理 `data.data ?? data` |
| 3 | Checkpoint 类型定义不完整 | ✅ 已修复 | `types/index.ts:82-89` 已包含完整字段 |
| 4 | createCheckpoint world_id 验证 | ✅ 已确认 | `stores/learning.ts` 已正确传递 |
| 5 | Character.avatar 字段名不一致 | ✅ 已修复 | `Character.vue` 已做兼容 `avatar: c.avatar \|\| c.avatar_url` |

---

## 二、P0 待修复问题

**当前无 P0 待修复问题** ✅

---

## 三、报告功能对齐状态

### 3.1 后端已实现的 Report API

| API 端点 | 方法 | 路由 | 状态 | 对应前端方法 |
|----------|------|------|------|--------------|
| 掌握度趋势 | GET | `/report/mastery-trends` | ✅ 已实现 | `reportApi.getMasteryTrends()` |
| 关系进化历程 | GET | `/report/relationship-history` | ✅ 已实现 | `reportApi.getRelationshipHistory()` |
| 世界对比 | GET | `/report/world-comparison` | ✅ 已实现 | `reportApi.getWorldComparison()` |
| 里程碑事件 | GET | `/report/milestones` | ✅ 已实现 | `reportApi.getMilestones()` |
| 单世界掌握度趋势 | GET | `/report/worlds/{id}/mastery-trends` | ✅ 已实现 | `reportApi.getWorldMasteryTrends()` |

### 3.2 前端已实现的组件

| 组件 | 文件路径 | 状态 | 说明 |
|------|----------|------|------|
| 报告页主容器 | `frontend/src/views/ReportPage.vue` | ✅ 已创建 | 包含 Tab 导航 |
| 掌握度趋势图 | `frontend/src/components/MasteryTrendsChart.vue` | ✅ 已创建 | 列表式展示 |
| 关系进化历程 | `frontend/src/components/RelationshipTimeline.vue` | ✅ 已创建 | 287行完整实现 |
| 世界对比网格 | `frontend/src/components/WorldComparisonGrid.vue` | ✅ 已创建 | 237行完整实现 |
| 里程碑列表 | `frontend/src/components/MilestoneList.vue` | ✅ 已创建 | 175行完整实现 |

### 3.3 前端类型定义

| 类型 | 定义位置 | 状态 | 说明 |
|------|----------|------|------|
| MasteryTrendItem | `types/index.ts:347-353` | ✅ 已定义 | 与后端对齐 |
| MasteryTrendResponse | `types/index.ts:355-360` | ✅ 已定义 | 与后端对齐 |
| RelationshipEvent | `types/index.ts:363-372` | ✅ 已定义 | 与后端对齐 |
| RelationshipHistoryResponse | `types/index.ts:374-377` | ✅ 已定义 | 与后端对齐 |
| WorldComparisonItem | `types/index.ts:380-388` | ✅ 已定义 | 与后端对齐 |
| MilestoneEvent | `types/index.ts:393-400` | ✅ 已定义 | 与后端对齐 |
| WorldMasteryTrendItem | `types/index.ts:403-407` | ✅ 已定义 | 与后端对齐 |

---

## 四、后端有但前端未调用的 API（P2 可选增强）

这些是后端已实现但前端未使用的功能：

| API | 后端 | 前端 API 定义 | 调用状态 |
|-----|------|---------------|----------|
| `/character/{id}/avatar` | ✅ | `characterApi.uploadAvatar()` | ❌ 未调用 |
| `/character/stats` | ✅ | `characterApi.getStats()` | ❌ 未调用 |
| `/character/{id}/levelup` | ✅ | `characterApi.levelup()` | ❌ 未调用 |
| `/progress/due` | ✅ | ❌ 未定义 | - |
| `/persona/generate` | ✅ | ❌ 未定义 | - |
| `/progress/{id}/review` | ✅ | ❌ 未定义 | - |
| `/sessions/{id}/end` | ✅ | ❌ 未定义 | - |

---

## 五、修复清单

### P0 立即修复

- [x] 1. 修复 `WorldDetail.vue` 的 checkpoint API 路径改为 `/save?subject_id=${courseId}`

---

## 六、验证清单

修复完成后，验证以下功能正常工作：

- [ ] 选择世界 → 选择课程 → 查看存档列表
- [ ] 加载存档（读档）
- [ ] 查看 ReportPage（所有 Tab）

---

## 七、更新日志

| 日期 | 更新内容 |
|------|----------|
| 2026-04-07 | 初始创建，标记现有状态 |
| 2026-04-08 | 确认 UserProfile.refresh 已自动修复；更新 checkpoint 修复方案为使用 /save 接口；所有 P0 问题已修复 |
