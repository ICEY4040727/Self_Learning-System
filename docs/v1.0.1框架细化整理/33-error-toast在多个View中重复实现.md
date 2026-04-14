# 问题 33: error-toast 在多个 View/Component 中重复实现（loading + error + showError 模式）

## 问题类型
重复逻辑模式（前端）

## 涉及文件
- `frontend/src/views/WorldDetail.vue` — `showError()` + `.error-toast` CSS
- `frontend/src/views/Worlds.vue` — `showError()` + `.error-toast` CSS
- `frontend/src/views/Home.vue` — `errorMessage` + `.error-toast` CSS
- `frontend/src/components/KnowledgeGraph.vue` — `errorMessage` + `.error` CSS
- `frontend/src/components/TimelineTree.vue` — `errorMessage` + `.error` CSS
- `frontend/src/components/galgame/CheckpointPanel.vue` — `errorMessage` + `.error` CSS

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

## 建议修复方向

1. 提取为 `composables/useAsync.ts`：封装 `loading`、`error`、`showError` + 自动清除
2. 提取为全局 `<ErrorToast>` 组件：统一样式和行为
3. 或使用 Vue 3 的 `provide/inject` + 全局 toast 状态