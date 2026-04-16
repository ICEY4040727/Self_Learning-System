# 问题 32: `useWorldStore` 定义了完整的 CRUD 但 Views 全部绕过直接调 API

## ⚠️ 未解决

**说明**: worldStore 仍存在但 Views 直接调 API

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

---

## 统一解决方案（#29 + #32）

> **注意**：此问题与 #29（API 模块未使用）需统一解决

### 核心架构

```
┌─────────────────────────────────────────────────────────┐
│                      Views                              │
│  Login.vue, Archive.vue, Worlds.vue, WorldDetail.vue...│
└─────────────────────────┬───────────────────────────────┘
                          │ useWorlds(), useArchive(), etc.
┌─────────────────────────▼───────────────────────────────┐
│                    Composables                           │
│  useWorlds.ts, useArchive.ts, useCourses.ts, useAuth.ts│
│  - 封装 API 调用                                        │
│  - 状态管理（替代 Store）                               │
│  - 错误处理                                            │
└─────────────────────────┬───────────────────────────────┘
                          │ worldApi, archiveApi, etc.
┌─────────────────────────▼───────────────────────────────┐
│                    API Modules                           │
│  character.ts, world.ts, archive.ts, auth.ts, memory.ts │
└─────────────────────────────────────────────────────────┘
```

### 为什么用 Composables 替代 Store？

| | Store (Pinia) | Composables |
|---|---|---|
| 状态共享 | 全局单例 | 每个组件实例独立 |
| 适用场景 | 跨页面共享的全局状态 | 单页面的数据管理 |
| 本项目情况 | 139 行代码 0 次使用 | 推荐方案 |

**结论**：`worldStore` 的方法本质上是一个个独立的异步数据获取逻辑，更适合用 Composables 封装，而非全局 Store。

### 迁移策略

**Phase 1: 新建 API 模块**
- `api/world.ts` - 世界相关 API
- `api/archive.ts` - 归档相关 API
- `api/course.ts` - 课程相关 API

**Phase 2: 新建 Composables**
- `composables/useWorlds.ts` - 封装 worldApi 调用
- `composables/useWorldDetail.ts` - 封装单个世界的数据获取
- `composables/useArchive.ts` - 封装归档数据获取
- `composables/useCourses.ts` - 封装课程数据获取

**Phase 3: 迁移 Views**
- Worlds.vue → 使用 `useWorlds()`
- WorldDetail.vue → 使用 `useWorldDetail()`
- Archive.vue → 使用 `useArchive()`
- CoursePage.vue → 使用 `useCourses()`
- Character.vue → 直接使用 `characterApi`

**Phase 4: 清理**
- 删除 `stores/world.ts`
- 删除空的 stores 目录（如无其他 store）

### composables/useWorldDetail.ts 示例

```typescript
import { ref } from 'vue'
import { worldApi } from '@/api/world'
import { characterApi } from '@/api/character'
import { useToast } from './useToast'

export function useWorldDetail() {
  const world = ref<World | null>(null)
  const courses = ref<Course[]>([])
  const characters = ref<Character[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const toast = useToast()

  async function fetchWorld(id: number) {
    loading.value = true
    error.value = null
    try {
      const [worldData, coursesData, charactersData] = await Promise.all([
        worldApi.get(id),
        worldApi.getCourses(id),
        characterApi.list(),
      ])
      world.value = worldData
      courses.value = coursesData
      characters.value = charactersData
    } catch (e) {
      error.value = parseApiError(e)
      toast.error(error.value)
    } finally {
      loading.value = false
    }
  }

  async function createCourse(data: CreateCourseData) {
    try {
      const newCourse = await worldApi.createCourse(world.value!.id, data)
      courses.value.push(newCourse)
      toast.success('课程创建成功')
      return newCourse
    } catch (e) {
      toast.error(parseApiError(e))
      throw e
    }
  }

  return {
    world,
    courses,
    characters,
    loading,
    error,
    fetchWorld,
    createCourse,
  }
}
```

---

## PR 提交检查清单

- [ ] 新建 `api/world.ts`
- [ ] 新建 `api/archive.ts`
- [ ] 新建 `api/course.ts`
- [ ] 新建 `composables/useWorlds.ts`
- [ ] 新建 `composables/useWorldDetail.ts`
- [ ] 新建 `composables/useArchive.ts`
- [ ] 新建 `composables/useCourses.ts`
- [ ] 删除 `stores/world.ts`
- [ ] 迁移 Worlds.vue → useWorlds()
- [ ] 迁移 WorldDetail.vue → useWorldDetail()
- [ ] 迁移 Archive.vue → useArchive()
- [ ] 迁移 CoursePage.vue → useCourses()
- [ ] 迁移 Character.vue → characterApi
- [ ] **提供截图**：
  - 各页面功能正常截图
  - 验证无 console 错误

## 关联

- 此 PR 同时解决 #29（API 模块未使用）
- PR body 中使用 `Closes #29` 和 `Closes #32`
