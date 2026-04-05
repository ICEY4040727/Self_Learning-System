# 知遇 Vue 3 迁移实现指引

## 目录结构

```
src/
├── main.ts
├── App.vue
├── router/index.ts
├── api/client.ts              ← axios 实例 + Bearer 拦截
├── types/index.ts             ← 全部 TypeScript 类型 + 常量
├── stores/
│   ├── auth.ts                ← POST /api/auth/login|register, GET /api/auth/me
│   ├── world.ts               ← GET/POST /api/worlds, /courses, /checkpoints, /timelines
│   ├── learning.ts            ← 对话状态机 + 真实 API 联调
│   └── settings.ts            ← GET/PUT /api/settings
├── components/
│   ├── ParticleBackground.vue
│   ├── CharacterSprite.vue
│   ├── DialogBox.vue          ← 三模式状态机 + 打字机
│   ├── HudBar.vue
│   ├── BacklogPanel.vue
│   ├── RelationshipStageOverlay.vue
│   ├── SaveLoadPanel.vue
│   └── KnowledgeGraphModal.vue
├── pages/
│   ├── LoginPage.vue
│   ├── MainMenuPage.vue       ← 5阶段状态机
│   ├── LearningPage.vue       ← 四层布局 + backdrop-filter 安全动画
│   ├── ArchivesPage.vue       ← vue-chartjs 图表
│   └── SettingsPage.vue
└── styles/
    ├── fonts.css              ← 与 React 版完全相同，直接复制
    ├── galgame.css            ← 与 React 版完全相同，直接复制
    └── index.css              ← Tailwind base + components + utilities
```

## 安装依赖

```bash
# 核心
npm install vue@^3 vue-router@^4 pinia axios

# 图标（lucide 的 Vue 版）
npm install lucide-vue-next

# 图表（替代 recharts）
npm install vue-chartjs chart.js

# 可选：@vueuse/core（滚动/防抖工具）
npm install @vueuse/core

# Tailwind CSS v4 + Vite
npm install -D tailwindcss @tailwindcss/vite
```

## vite.config.ts

```ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'url'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
})
```

## 环境变量（.env）

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

## CSS 复用说明

**直接复制无需修改的文件：**
- `src/styles/fonts.css`     — Google Fonts @import（与 React 版相同）
- `src/styles/galgame.css`   — 所有 @keyframes + .galgame-* 工具类（与 React 版相同）

**需要新建的文件：**
- `src/styles/index.css`

```css
/* index.css */
@import "tailwindcss";
@import "./fonts.css";
@import "./galgame.css";
```

## ⚠️ 关键注意事项

### 1. backdrop-filter 安全规则
`DialogBox.vue` 父层 wrapper **必须永远保持 `opacity:1`**。
`LearningPage.vue` 的 `<Transition name="dialog-slide">` 只驱动 `translateY`：

```css
.dialog-slide-enter-from { transform: translateY(36px); }
.dialog-slide-enter-active { transition: transform 0.35s ease-out; }
/* 绝对不要加 opacity */
```

### 2. jumpKey 机制
`CharacterSprite.vue` 用 `:key="jumpKey"` 驱动 CSS `jumpOnce` 动画重播。
在 `learning.ts` store 中，每次 `sendMessage` 或 `pushSpeaking` 时递增对应的 jumpKey：

```ts
sageJumpKey.value++    // sage 发言时
travelerJumpKey.value++ // 切换到 input 模式时
```

### 3. 路由守卫
`router/index.ts` 中 `beforeEach` 读取 `useAuthStore().isLoggedIn`。
Pinia store 在 `main.ts` 中必须在 `router` 之前注册（`app.use(createPinia())` 先于 `app.use(router)`）。

### 4. 图表库
`ArchivesPage.vue` 使用 `vue-chartjs` 替代 `recharts`（React 专属）。
情感轨迹数据映射：
- `valence`（效价）→ 折线图
- `arousal`（唤醒度）→ 折线图
- `emotion_type` 计数 → 饼图

### 5. 后端接口对照（UI迁移书.md §2）
| Vue 操作 | 接口 |
|---|---|
| 登录 | `POST /api/auth/login`（FormData） |
| 注册 | `POST /api/auth/register`（JSON） |
| 获取世界列表 | `GET /api/worlds` |
| 启动学习会话 | `POST /api/courses/{id}/start` |
| 发送消息 | `POST /api/courses/{id}/chat` |
| 获取情感轨迹 | `GET /api/sessions/{id}/emotion_trajectory` |
| 创建存档 | `POST /api/checkpoints` |
| 分叉存档 | `POST /api/checkpoints/{id}/branch` |
| 保存设置 | `PUT /api/settings` |

## 迁移验收核查

- [ ] `DialogBox` 毛玻璃效果在 Chrome/Safari/Firefox 全程不闪烁
- [ ] 角色 `:key="jumpKey"` 触发 `jumpOnce` 动画
- [ ] `<Transition name="page-fade">` 页面切换淡入淡出
- [ ] `<Transition name="dialog-slide">` 对话框只做 translateY
- [ ] 选项 `choiceStagger` 逐条延迟 0.09s 飞入
- [ ] 关系升级 `RelationshipStageOverlay` 同心圆 + `stageReveal` 动画
- [ ] Pinia store reset 在离开 LearningPage 时触发（`onBeforeUnmount`）
- [ ] 所有 API 请求携带 `Authorization: Bearer <token>`
- [ ] 401 响应自动清除 token 并跳转 `/`

---

## 契约适配变更记录（vue3_migration_contract_adaptation.md）

| # | 文件 | 变更描述 |
|---|---|---|
| §2 | `stores/settings.ts` | `saveSettings()` 只 PUT `{default_provider, api_key}`；本地偏好通过 `localStorage` 持久化，不走后端 |
| §3 | `types/index.ts`, `stores/settings.ts`, `pages/SettingsPage.vue` | Provider 枚举从 `'ollama'` 改为 `'local'`（对齐后端 `elif provider == "local"`） |
| §4 | `types/index.ts` | `ChatRequest.message`（不是 `content`）；`ChatResponse.emotion` 改为 `Record<string,unknown>\|null`（dict）；`type` 扩展为 `'text'\|'tool_request'\|'choice'` |
| §4 | `stores/learning.ts` | `sendMessage` 请求体改为 `{ message }`；emotion 从 dict 提取 `.emotion_type` 经 `EMOTION_TYPE_ZH` 转中文；`type==='choice'` 分支处理 |
| §5 | `types/index.ts` | `StartLearningResponse.teacher_persona` 改为 `string\|null`（名称字符串）；`HistoryMessage` 独立类型仅含 4 字段（无 emotion/expression_hint） |
| §5 | `stores/learning.ts` | `loadHistory()` 映射 `HistoryMessage[]`，不补 emotion/expression_hint；`_sageName` 直接取 `teacher_persona` 字符串 |
| §6 | `types/index.ts` | 新增 `BranchResponse` 接口含 `session_id/course_id/world_id` |
| §6 | `stores/learning.ts` | `startSession` 分叉路径：`branch → 消费三字段 → start(branch.course_id) → loadHistory()`，覆盖调用方传入的 courseId/worldId |
| §6 | `pages/LearningPage.vue` | `handleLoadCheckpoint` 使用 store 的当前 worldId/courseId 传入 startSession，由 store 内部从 branch 响应重建状态 |
| §7 | `types/index.ts` | 新增 `DiaryCreatePayload` 接口含必填 `course_id`（int）和 `date`（ISO datetime） |
| §7 | `pages/ArchivesPage.vue` | 挂载时 `fetchCourses()`；写日记表单增加课程选择器；提交时携带 `course_id` + `new Date().toISOString()`（datetime 非 date-only） |
| §8 | `types/index.ts` | 导出 `ALLOWED_SPRITE_STEMS`, `ALLOWED_SPRITE_MIMES`, `MAX_SPRITE_SIZE_BYTES` 供上传组件复用 |