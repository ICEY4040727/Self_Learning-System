# 问题 32: `useWorldStore` 定义了完整的 CRUD 但 Views 全部绕过直接调 API

## 问题类型
架构不一致 / 死代码（前端 Store 层）

## 涉及文件
- `frontend/src/stores/world.ts` — 定义了 `useWorldStore`（139 行）
- `frontend/src/views/Worlds.vue` — 直接 `client.get('worlds')`
- `frontend/src/views/WorldDetail.vue` — 直接 `client.get('/worlds/...')` × 3

## 具体分析

### worldStore 提供的方法（全部未被 View 使用）

| Store 方法 | View 中的替代实现 |
|---|---|
| `fetchWorlds()` | `Worlds.vue` 自行 `client.get('worlds')` |
| `createWorld()` | `Worlds.vue` / `CreateWorldModal` 直接调 client |
| `fetchCourses()` | `WorldDetail.vue` 自行 `client.get('/worlds/.../courses')` |
| `fetchWorldCharacters()` | `WorldDetail.vue` 自行 `client.get('/worlds/.../characters')` |
| `fetchCharacters()` | `WorldDetail.vue` 和 `Character.vue` 各自调 `client.get('/character')` |
| `fetchTimelines()` | `TimelineTree.vue` 直接调 client |
| `fetchCheckpoints()` | `CheckpointPanel.vue` 直接调 client |

### Store 引用情况

在整个前端代码中搜索 `useWorldStore`：**0 处使用**。

## 影响分析

1. **139 行死代码**：worldStore 完全未被任何组件引用
2. **状态分散**：每个 View 自行管理 `worlds`、`courses` 等状态，页面间无法共享
3. **重复请求**：`WorldDetail.vue` 和 `Character.vue` 分别请求 `/character`，没有缓存机制
4. **命名误导**：新开发者可能以为使用了 Store 架构，实际没有

## 建议修复方向

1. **方案 A（推荐）**：让 Views 使用 worldStore，删除各 View 中重复的数据获取逻辑
2. **方案 B**：如果确定不需要 Store 模式，删除 worldStore（139 行），避免误导
3. 两种方案都需要确保选择一致——要么用 Store，要么不用，不应两者并存