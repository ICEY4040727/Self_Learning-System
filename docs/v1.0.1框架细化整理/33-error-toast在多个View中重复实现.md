# 问题 33: error-toast 在多个 View/Component 中重复实现（loading + error + showError 模式）

## ⚠️ 未解决

**说明**: 仍分散在各 View 中

## 问题类型
重复逻辑模式（前端）

## 涉及文件
- `frontend/src/views/WorldDetail.vue` — `showError()` + `.error-toast` CSS
- `frontend/src/views/Worlds.vue` — `showError()` + `.error-toast` CSS
- `frontend/src/views/Home.vue` — `errorMessage` + `.error-toast` CSS
- `frontend/src/components/KnowledgeGraph.vue` — `errorMessage` + `.error` CSS
- `frontend/src/components/TimelineTree.vue` — `errorMessage` + `.error` CSS
- `frontend/src/components/galgame/CheckpointPanel.vue` — `errorMessage` + `.error` CSS
- `frontend/src/components/ErrorToast.vue`（✅ 统一组件，04-15 15:27）

## 重复模式

几乎每个有数据获取的组件都重复以下 3 件套：

```typescript
// 1. 响应式变量
const loading = ref(false)
const errorMessage = ref('')

// 2. showError 函数（两种变体）
const showError = (error: unknown) => {
  errorMessage.value = parseApiError(error)
  setTimeout(() => (errorMessage.value = ''), 4000)  // 有的有定时清除，有的没有
}

// 3. 模板
<p v-if="errorMessage" class="error-toast">{{ errorMessage }}</p>
```

## CSS 重复

`.error-toast` 样式在以下文件中各自独立定义（内容基本相同）：
- `WorldDetail.vue`（scoped style）
- `Worlds.vue`（scoped style）
- `Home.vue`（scoped style）

`.error` 样式在：
- `KnowledgeGraph.vue`
- `TimelineTree.vue`
- `CheckpointPanel.vue`

两种 class 名（`error-toast` vs `error`）功能完全相同，只是命名不同。

## 影响分析

1. **6+ 处重复实现**：同样的 loading/error 逻辑散布在 6 个文件中
2. **行为不一致**：有的有 4 秒自动清除，有的没有；有的用 `error-toast`，有的用 `error`
3. **样式不统一**：同功能的 toast 在不同页面样式可能略有差异
4. **新增页面需重写**：每个新页面都要重新实现这套模式

---

## 统一解决方案（#27 + #33）

> **注意**：此问题与 #27（alert vs Toast）需统一解决，合并为一个 PR

### 核心架构

```
┌─────────────────────────────────────────────────────┐
│                    App.vue                          │
│  ┌─────────────────────────────────────────────┐   │
│  │ <ToastContainer />                          │   │
│  │   - 全局 Toast 展示层                        │   │
│  │   - 支持多个 Toast 并存                      │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ <router-view />                            │   │
│  │   - 各页面只关注业务逻辑                      │   │
│  │   - 调用 useToast() 触发通知                 │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### 实现步骤

#### 1. 扩展 ErrorToast.vue

```vue
<!-- frontend/src/components/ErrorToast.vue -->
<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  message: string
  type?: 'error' | 'success' | 'warning'
  duration?: number  // 0 表示不自动消失
}>()

const visible = ref(true)

watch(() => props.message, (newMsg) => {
  if (newMsg) {
    visible.value = true
    if (props.duration && props.duration > 0) {
      setTimeout(() => {
        visible.value = false
      }, props.duration)
    }
  }
}, { immediate: true })

const emit = defineEmits<{
  close: []
}>()

const typeColors = {
  error: 'rgba(223, 74, 74, 0.9)',
  success: 'rgba(34, 197, 94, 0.9)',
  warning: 'rgba(251, 191, 36, 0.9)'
}
</script>

<template>
  <Transition name="toast">
    <p 
      v-if="visible" 
      class="error-toast font-ui"
      :style="{ background: type ? typeColors[type] : typeColors.error }"
      @click="emit('close')"
    >
      {{ message }}
    </p>
  </Transition>
</template>

<style scoped>
.error-toast {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  padding: 8px 14px;
  border-radius: 6px;
  font-size: 13px;
  z-index: 9999;
  letter-spacing: 1px;
  max-width: 80vw;
  text-align: center;
  cursor: pointer;
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-20px);
}
</style>
```

#### 2. 创建 ToastContainer 组件

```vue
<!-- frontend/src/components/ToastContainer.vue -->
<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import ErrorToast from './ErrorToast.vue'

const { toasts, remove } = useToast()
</script>

<template>
  <Teleport to="body">
    <div class="toast-container">
      <ErrorToast
        v-for="toast in toasts"
        :key="toast.id"
        :message="toast.message"
        :type="toast.type"
        :duration="toast.duration"
        @close="remove(toast.id)"
      />
    </div>
  </Teleport>
</template>

<style scoped>
.toast-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  pointer-events: none;
  z-index: 9999;
}

.toast-container > * {
  pointer-events: auto;
}
</style>
```

#### 3. 创建 useToast composable

```typescript
// frontend/src/composables/useToast.ts
import { ref } from 'vue'

export interface Toast {
  id: number
  message: string
  type: 'error' | 'success' | 'warning'
  duration: number
}

// 全局 toast 状态
const toasts = ref<Toast[]>([])

export function useToast() {
  function show(
    message: string, 
    type: Toast['type'] = 'error',
    duration: number = 4000
  ): number {
    const id = Date.now()
    toasts.value.push({ id, message, type, duration })
    return id
  }

  function remove(id: number) {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index > -1) {
      toasts.value.splice(index, 1)
    }
  }

  // 便捷方法
  function error(message: string, duration = 4000) {
    return show(message, 'error', duration)
  }

  function success(message: string, duration = 4000) {
    return show(message, 'success', duration)
  }

  function warning(message: string, duration = 4000) {
    return show(message, 'warning', duration)
  }

  return {
    toasts,
    show,
    remove,
    error,
    success,
    warning
  }
}
```

#### 4. 简化各页面

**WorldDetail.vue 简化前：**
```typescript
const loading = ref(false)
const errorMessage = ref('')

const showError = (error: unknown) => {
  errorMessage.value = parseApiError(error)
  setTimeout(() => (errorMessage.value = ''), 4000)
}
```

**WorldDetail.vue 简化后：**
```typescript
import { useToast } from '@/composables/useToast'

const toast = useToast()

// API 错误时直接调用
toast.error(parseApiError(error))
```

### 迁移清单

| 文件 | 移除内容 | 替换为 |
|------|---------|--------|
| WorldDetail.vue | `showError()` + CSS | `useToast().error()` |
| Worlds.vue | `showError()` + CSS | `useToast().error()` |
| Home.vue | `errorMessage` + CSS | `useToast().error()` |
| KnowledgeGraph.vue | `errorMessage` + CSS | `useToast().error()` |
| TimelineTree.vue | `errorMessage` + CSS | `useToast().error()` |
| CheckpointPanel.vue | `errorMessage` + CSS | `useToast().error()` |

---

## PR 提交检查清单

- [ ] 创建 `composables/useToast.ts`
- [ ] 扩展 `ErrorToast.vue` 组件
- [ ] 创建 `ToastContainer.vue`
- [ ] App.vue 集成 `<ToastContainer />`
- [ ] 简化 WorldDetail.vue（移除本地 showError）
- [ ] 简化 Worlds.vue（移除本地 showError）
- [ ] 简化 Home.vue（移除本地 errorMessage）
- [ ] 简化 KnowledgeGraph.vue
- [ ] 简化 TimelineTree.vue
- [ ] 简化 CheckpointPanel.vue
- [ ] **提供截图**：
  - 统一 Toast 样式截图
  - 多页面切换 Toast 保持截图

## 关联

- 此 PR 同时解决 #27（alert vs Toast）
- PR body 中使用 `Closes #27` 和 `Closes #33`
