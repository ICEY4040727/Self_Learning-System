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

## 建议修复方向

1. 将 `alert()` 替换为项目已有的 `error-toast` 模式
2. 或提取统一的 `useToast` composable，全局共享通知逻辑