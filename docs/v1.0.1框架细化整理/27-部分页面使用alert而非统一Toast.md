# 问题 27: 部分页面使用 `alert()` 而非统一的 Toast 通知

## ⚠️ 未解决

**说明**: CoursePage.vue 和 Settings.vue 仍使用 alert()

## 问题类型
UX 不一致（前端）

## 涉及文件
- `frontend/src/views/CoursePage.vue`（2 处）
- `frontend/src/views/Settings.vue`（1 处）

## 具体内容

**CoursePage.vue：**
```typescript
alert('请先添加知者')
alert('启动学习会话失败')
```

**Settings.vue：**
```typescript
alert('数据导出功能开发中')
```

而其他页面使用自定义的 `.error-toast` 组件：
- `WorldDetail.vue`：`<p v-if="errorMessage" class="error-toast">`
- `Worlds.vue`：`<p v-if="errorMessage" class="error-toast">`
- `Home.vue`：类似模式

## 影响分析

1. **视觉不统一**：`alert()` 使用浏览器原生弹窗（外观取决于操作系统），与项目自定义的统一 Toast 完全不同
2. **阻塞式 UI**：`alert()` 会暂停 JS 执行并阻塞用户操作，直到点击确认
3. **破坏沉浸感**：统一的 UI 风格中突然出现系统弹窗，体验割裂

---

## 统一解决方案（#27 + #33）

> **注意**：此问题与 #33（error-toast 重复实现）需统一解决，合并为一个 PR

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

#### 4. App.vue 集成

```vue
<!-- App.vue -->
<script setup>
import ToastContainer from '@/components/ToastContainer.vue'
</script>

<template>
  <ToastContainer />
  <router-view v-slot="{ Component }">
    <Transition name="page-fade" mode="out-in">
      <component :is="Component" />
    </Transition>
  </router-view>
</template>
```

#### 5. 修复 CoursePage.vue

```typescript
// 移除 alert()
import { useToast } from '@/composables/useToast'

const toast = useToast()

// 替换前
alert('请先添加知者')

// 替换后
toast.warning('请先添加知者')
```

#### 6. 修复 Settings.vue

```typescript
import { useToast } from '@/composables/useToast'

const toast = useToast()

// 替换前
alert('数据导出功能开发中')

// 替换后
toast.info('数据导出功能开发中')
```

---

## PR 提交检查清单

- [ ] 创建 `composables/useToast.ts`
- [ ] 扩展 `ErrorToast.vue` 组件
- [ ] 创建 `ToastContainer.vue`
- [ ] App.vue 集成 `<ToastContainer />`
- [ ] 替换 CoursePage.vue 的 `alert()` → `toast.warning()`
- [ ] 替换 Settings.vue 的 `alert()` → `toast.info()`
- [ ] **提供截图**：
  - Toast 正常显示截图
  - Toast 自动消失动画截图
  - 页面切换时 Toast 保持截图

## 关联

- 此 PR 同时解决 #33（error-toast 重复实现）
- PR body 中使用 `Closes #27` 和 `Closes #33`
