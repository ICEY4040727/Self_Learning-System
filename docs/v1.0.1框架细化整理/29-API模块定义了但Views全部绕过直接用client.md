# 问题 29: API 模块定义了但 Views 全部绕过，直接用 `client`

## ⚠️ 未解决

**说明**: Views 仍直接使用 client

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

### Views 直接使用 client 的情况（33 处）

| View/Component | 直接 API 调用 |
|---|---|
| `Login.vue` | `client.post('/auth/login')` |
| `Archive.vue` | `client.get('learning_diary')` × 7 |
| `WorldDetail.vue` | `client.get('/worlds/...')` × 12 |
| `Character.vue` | `client.get('/character')` × 5 |
| `CoursePage.vue` | `client.get('/courses/...')` × 6 |
| `Worlds.vue` | `client.get('worlds')` × 2 |

## 影响分析

1. **API 模块是死代码**：`characterApi` 93 行代码完全未被使用
2. **双份维护**：API 路径、参数处理分散在 12+ 个文件中，修改 API 时容易遗漏
3. **不一致的错误处理**：有的地方 `.then(res => res.data)`，有的解构 `{ data }`，有的直接用返回值
4. **类型安全缺失**：直接用 client 的地方多为 `as Type` 强制断言，而非利用 API 模块的类型推导

---

## 统一解决方案（#29 + #32）

> **注意**：此问题与 #32（worldStore 未使用）需统一解决

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
│  - 状态管理                                              │
│  - 错误处理                                              │
└─────────────────────────┬───────────────────────────────┘
                          │ worldApi, archiveApi, etc.
┌─────────────────────────▼───────────────────────────────┐
│                    API Modules                           │
│  character.ts, world.ts, archive.ts, auth.ts, memory.ts │
└─────────────────────────────────────────────────────────┘
```

### 实现步骤

#### Phase 1: 补充缺失的 API 模块

**新建 `frontend/src/api/world.ts`：**
```typescript
import client from './client'
import type { World, WorldCreateRequest } from '@/types'

export const worldApi = {
  list: (): Promise<World[]> =>
    client.get('/worlds').then(res => res.data),

  get: (id: number): Promise<World> =>
    client.get(`/worlds/${id}`).then(res => res.data),

  create: (data: WorldCreateRequest): Promise<World> =>
    client.post('/worlds', data).then(res => res.data),

  update: (id: number, data: Partial<World>): Promise<World> =>
    client.put(`/worlds/${id}`, data).then(res => res.data),

  delete: (id: number): Promise<void> =>
    client.delete(`/worlds/${id}`),

  getCourses: (id: number) =>
    client.get(`/worlds/${id}/courses`).then(res => res.data),

  getCharacters: (id: number) =>
    client.get(`/worlds/${id}/characters`).then(res => res.data),

  addCharacter: (worldId: number, characterId: number) =>
    client.post(`/worlds/${worldId}/characters`, { character_id: characterId }),

  removeCharacter: (worldId: number, characterId: number) =>
    client.delete(`/worlds/${worldId}/characters/${characterId}`),
}
```

**新建 `frontend/src/api/archive.ts`：**
```typescript
import client from './client'

export const archiveApi = {
  getDiaries: () =>
    client.get('/learning_diary').then(res => res.data),

  createDiary: (content: string) =>
    client.post('/learning_diary', { content }),

  getProgress: () =>
    client.get('/progress').then(res => res.data),

  getSessions: () =>
    client.get('/sessions').then(res => res.data),

  getEmotionTrajectory: (sessionId: number) =>
    client.get(`/sessions/${sessionId}/emotion_trajectory`).then(res => res.data),

  getCourses: () =>
    client.get('/courses').then(res => res.data),

  getWorlds: () =>
    client.get('/worlds').then(res => res.data),
}
```

**新建 `frontend/src/api/course.ts`：**
```typescript
import client from './client'

export const courseApi = {
  get: (courseId: number) =>
    client.get(`/courses/${courseId}`).then(res => res.data),

  getSages: (courseId: number) =>
    client.get(`/courses/${courseId}/sages`).then(res => res.data),

  getSessions: (courseId: number) =>
    client.get(`/courses/${courseId}/sessions`).then(res => res.data),

  getMemoryFacts: (courseId: number, statsOnly = true) =>
    client.get(`/courses/${courseId}/memory-facts?stats_only=${statsOnly}`).then(res => res.data),

  start: (courseId: number, sageId: number) =>
    client.post(`/courses/${courseId}/start`, { sage_id: sageId }),
}
```

**新建 `frontend/src/api/auth.ts`：**
```typescript
import client from './client'
import type { LoginRequest, RegisterRequest } from '@/types'

export const authApi = {
  login: (data: LoginRequest) =>
    client.post('/auth/login', data).then(res => res.data),

  register: (data: RegisterRequest) =>
    client.post('/auth/register', data).then(res => res.data),
}
```

#### Phase 2: 创建 Composables

**新建 `frontend/src/composables/useWorlds.ts`：**
```typescript
import { ref } from 'vue'
import { worldApi } from '@/api/world'
import { useToast } from './useToast'

export function useWorlds() {
  const worlds = ref<World[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const toast = useToast()

  async function fetchWorlds() {
    loading.value = true
    try {
      worlds.value = await worldApi.list()
    } catch (e) {
      error.value = parseApiError(e)
      toast.error(error.value)
    } finally {
      loading.value = false
    }
  }

  async function createWorld(data: CreateWorldData) {
    try {
      const newWorld = await worldApi.create(data)
      worlds.value.push(newWorld)
      toast.success('世界创建成功')
      return newWorld
    } catch (e) {
      toast.error(parseApiError(e))
      throw e
    }
  }

  async function deleteWorld(id: number) {
    try {
      await worldApi.delete(id)
      worlds.value = worlds.value.filter(w => w.id !== id)
      toast.success('世界已删除')
    } catch (e) {
      toast.error(parseApiError(e))
      throw e
    }
  }

  return { worlds, loading, error, fetchWorlds, createWorld, deleteWorld }
}
```

类似创建：
- `useArchive.ts` - 封装日记、进度、会话等 API
- `useCourses.ts` - 封装课程相关 API
- `useAuth.ts` - 封装登录注册

#### Phase 3: 迁移 Views

**Worlds.vue 迁移前：**
```typescript
import client from '@/api/client'

async function fetchWorlds() {
  const { data } = await client.get('worlds')
  worlds.value = data
}
```

**Worlds.vue 迁移后：**
```typescript
import { useWorlds } from '@/composables/useWorlds'

const { worlds, loading, fetchWorlds, createWorld } = useWorlds()

onMounted(() => fetchWorlds())
```

**WorldDetail.vue 迁移前：**
```typescript
import client from '@/api/client'

async function fetchWorld() {
  const { data } = await client.get(`/worlds/${worldId.value}`)
  selectedWorld.value = data
}
```

**WorldDetail.vue 迁移后：**
```typescript
import { useWorldDetail } from '@/composables/useWorldDetail'

const { world, courses, characters, loading, fetchWorld } = useWorldDetail()

onMounted(() => fetchWorld(route.params.id))
```

#### Phase 4: 清理

- 删除 `stores/world.ts`（139 行死代码）
- 移除各 View 中的 `import client from '@/api/client'`
- 保留 `client.ts` 作为 axios 实例基础

### 迁移清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `api/world.ts` | 新建 | 世界相关 API |
| `api/archive.ts` | 新建 | 归档相关 API |
| `api/course.ts` | 新建 | 课程相关 API |
| `api/auth.ts` | 新建 | 认证相关 API |
| `composables/useWorlds.ts` | 新建 | 世界状态管理 |
| `composables/useArchive.ts` | 新建 | 归档状态管理 |
| `composables/useCourses.ts` | 新建 | 课程状态管理 |
| `composables/useAuth.ts` | 新建 | 认证状态管理 |
| `stores/world.ts` | 删除 | 死代码清理 |
| `Login.vue` | 修改 | 使用 useAuth |
| `Archive.vue` | 修改 | 使用 useArchive |
| `Worlds.vue` | 修改 | 使用 useWorlds |
| `WorldDetail.vue` | 修改 | 使用 useWorldDetail |
| `Character.vue` | 修改 | 使用 characterApi |
| `CoursePage.vue` | 修改 | 使用 useCourses |

---

## PR 提交检查清单

- [ ] 新建 `api/world.ts`
- [ ] 新建 `api/archive.ts`
- [ ] 新建 `api/course.ts`
- [ ] 新建 `api/auth.ts`
- [ ] 新建 `composables/useWorlds.ts`
- [ ] 新建 `composables/useArchive.ts`
- [ ] 新建 `composables/useCourses.ts`
- [ ] 新建 `composables/useAuth.ts`
- [ ] 删除 `stores/world.ts`
- [ ] 迁移 Login.vue
- [ ] 迁移 Archive.vue
- [ ] 迁移 Worlds.vue
- [ ] 迁移 WorldDetail.vue
- [ ] 迁移 Character.vue
- [ ] 迁移 CoursePage.vue
- [ ] **提供截图**：
  - Worlds.vue 页面截图
  - WorldDetail.vue 页面截图
  - API 调用网络请求截图（验证走 API 模块）

## 关联

- 此 PR 同时解决 #32（worldStore 未使用）
- PR body 中使用 `Closes #29` 和 `Closes #32`
