# 问题 29: API 模块定义了但 Views 全部绕过，直接用 `client`

## 问题类型
架构不一致（前端）

## 涉及文件
- `frontend/src/api/character.ts` — 定义了 `characterApi`（CRUD 方法完整）
- `frontend/src/api/client.ts` — 定义了 `userProfileApi`、`reportApi`
- `frontend/src/api/memory.ts` — 定义了 `memoryApi`
- 12+ views/components — 全部直接 `import client from '@/api/client'`

## 具体分析

### API 模块定义情况

| 模块 | 方法 | 被引用次数 |
|------|------|-----------|
| `characterApi` | list, create, get, update, delete, uploadAvatar, getStats, levelup | **0** |
| `userProfileApi` | get, refresh | **0** |
| `reportApi` | getMasteryTrends, getRelationshipHistory, getWorldComparison, getMilestones, getWorldMasteryTrends | **0** |
| `memoryApi` | 各种方法 | **1**（仅 Learning.vue） |

### Views 直接使用 client 的情况

| View/Component | 直接 API 调用 |
|---|---|
| `Worlds.vue` | `client.get('worlds')` |
| `WorldDetail.vue` | `client.get('/worlds/...')` × 3 + `client.get('/character')` |
| `Character.vue` | `client.get('/character')` |
| `CoursePage.vue` | `client.get(...)` × 多处 |
| `Login.vue` | `client.post('/auth/login')` |
| `Archive.vue` | `client.get(...)` |
| `KnowledgeGraph.vue` | `client.get(...)` |
| `CheckpointPanel.vue` | `client.get(...)` |
| `TimelineTree.vue` | `client.get(...)` |
| `EmotionTrajectory.vue` | `client.get(...)` |
| `CreatePersonaModal.vue` | `client.post(...)` |
| `stores/world.ts` | `client.get('/worlds')` |
| `stores/learning.ts` | `client.get(...)` |

## 影响分析

1. **API 模块是死代码**：`characterApi` 93 行代码完全未被使用
2. **双份维护**：API 路径、参数处理分散在 12+ 个文件中，修改 API 时容易遗漏
3. **不一致的错误处理**：有的地方 `.then(res => res.data)`，有的解构 `{ data }`，有的直接用返回值
4. **类型安全缺失**：直接用 client 的地方多为 `as Type` 强制断言，而非利用 API 模块的类型推导

## 建议修复方向

1. **方案 A**：删除未使用的 API 模块（更轻量）
2. **方案 B**：将 Views 迁移到使用 API 模块（更规范但工作量大）
3. 无论哪种，都应统一 API 调用方式，消除"部分封装、部分裸调用"的混乱状态