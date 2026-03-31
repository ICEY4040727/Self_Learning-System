# Reviewer 技术方案指导：Galgame UI 重构

> **文档类型**：Reviewer 技术提案（供后续拆分为 Issue）
> **面向**：Creator
> **参考**：`docs/design_UI.md`（设计共识）、`paper2galgame/`（参考实现）、Issues #93 #96 #97 #98 #100
> **日期**：2026-03-26（更新：2026-03-27）

---

## 〇、当前项目实际状态

> **最近更新**：Phase 1（#107）和 Phase 2（#108）已合并。以下为 2026-03-27 更新后的状态。

### 后端

| 模块 | 状态 | 说明 |
|------|------|------|
| 13 张数据表 | ✅ 完成 | Character 已有 `sprites` JSON 字段，Subject 已有 `scene_background`（Migration 002） |
| 学习引擎 | ✅ 完成 | 双层 Prompt、ZPD 脚手架（5 级）、情感分析（8 类）、关系阶段（5 阶段）、记忆检索、知识图谱（可选） |
| Chat API | ✅ 完成 | 返回 `type` + `reply` + `emotion` + `relationship_stage` + `expression_hint` |
| `EXPRESSION_MAP` | ✅ 完成 | `learning.py:31-40`：8 种情绪 → 4 种表情名（default/happy/thinking/concerned） |
| 存档 API | ✅ 完成 | `/api/save` CRUD，JSON 文件持久化 |
| 情感轨迹 API | ✅ 完成 | `/api/sessions/{id}/emotion_trajectory` |
| 工具确认 API | ❌ STUB | `/api/chat/tool_confirm` 返回硬编码占位文本 |
| 立绘上传 API | ❌ 未实现 | #109：`POST /api/characters/{id}/sprites`，字段存在但无上传接口 |
| `start_learning` 返回 greeting | ❌ 未实现 | #100 议题：根据关系阶段返回不同开场白 |

### 前端 — Galgame 组件

| 组件 | 状态 | 说明 |
|------|------|------|
| `DialogBox.vue` | ✅ **已集成** | 四模式状态机 TEACHER_SPEAKING/USER_INPUT/CHOICES/WAITING（#107） |
| `HudBar.vue` | ✅ **新增已集成** | 7 按钮 + 状态显示（#107） |
| `BacklogPanel.vue` | ✅ **新增已集成** | 右侧滑入回忆面板（#107） |
| `CharacterDisplay.vue` | ❌ **未使用** | Learning.vue 仍是 120px 占位圆，待 #92 集成 |
| `ChoicePanel.vue` | 🗑️ 已删除 | 功能合并到 DialogBox CHOICES 模式（#107） |
| `EmotionIndicator.vue` | 🗑️ 已删除 | 功能合并到 HudBar 状态栏（#107） |
| `SaveLoad.vue` | ✅ 已集成 | 存读档功能完整 |
| `ToolConfirmDialog.vue` | ✅ 已集成 | 工具确认弹窗 |

### 前端 — Learning.vue 当前实际状态

**已有**：
- 四层布局骨架（#91）+ CSS 变量主题系统 + Google Fonts（#107）
- DialogBox 四模式状态机 + 输入框在对话框内部（#107）
- HudBar 7 按钮 + BacklogPanel 回忆面板（#107）
- Promise-based 打字机 + 点击推进 + 长回复分段 + 键盘 Space/Enter（#108）
- 三种响应类型处理 + Mermaid + DOMPurify + 会话恢复 + Save/Load
- Auto 模式（2s 延迟后切换 USER_INPUT）
- onUnmounted 清理定时器 + removeEventListener

**未有**：
- 角色立绘不切换表情（#92，待做）
- 没有关系进化事件覆盖层
- Settings 中的打字机开关和自动滚动开关**实际不生效**
- Ctrl 按住快进（#97 提到但未实现）

### Issue 规划（更新后）

| Issue | 内容 | 状态 |
|-------|------|------|
| #91 | 四层布局重构 | ✅ 已合并 |
| #96 | DialogBox 集成 + 三模式状态机 | ✅ 已合并（#107） |
| #98 | 回忆面板 + 底部 HUD | ✅ 已合并（#107） |
| #97 | 点击推进 + 分段 + 键盘 | ✅ 已合并（#108） |
| #92 | 角色立绘 + 情绪表情切换 | 🔜 下一个（前端），依赖 #109（后端） |
| #109 | 立绘上传 API | 🔜 新开（后端） |
| #104 | 前端易用性审计 | 📝 审计更新已发布（Issue comment） |
| #100 | 完整设计方案文档 | 待撰写 |
| #93 | 总规划 | 跟踪中 |

---

## 一、paper2galgame 参考分析

### 1.1 值得借鉴的技术模式

| 技术点 | paper2galgame 做法 | 对应我们的 Issue | 借鉴方式 |
|--------|-------------------|-----------------|---------|
| **分层 z-index 渲染** | `z-0` 背景 → `z-10` 角色 → `z-20` UI，absolute 叠加 | #91 ✅ 已采纳 | 已在 Learning.vue 实现 |
| **情绪→立绘字典映射** | `CHARACTER_IMAGES: Record<string, string>`，`getSpriteUrl(emotion)` 一行切换 | #92 | 直接采纳此模式：`{ normal: url, happy: url, ... }` |
| **打字机 + 跳过统一处理** | `handleNext()`: 打字中→显示全文；打字完→下一句。单函数两行为 | #97 | 直接采纳。paper2galgame 用 `setInterval` + `useRef` 清理计时器，比我们当前 `setTimeout` 链更规范 |
| **Auto 模式** | `isAuto` flag + `setTimeout` 在打字完后自动推进 | #98 HUD「自动」按钮 | 直接采纳此 flag + timer 模式 |
| **Backlog 弹层** | 全屏遮罩 + 内容面板，显示 `script.slice(0, currentIndex+1)` | #98 | 数据逻辑借鉴（复用 messages 数组），但布局改为右侧滑入（design_UI.md 共识） |
| **对话框底部全宽** | `absolute bottom-0 left-0 right-0`，半透明底 + 名牌 tag | #96 | 方向一致。但 paper2galgame 是白底粉框，我们是暗底金框 |
| **点击推进游戏循环** | 整个游戏区 `onClick={handleNext}`，对话框在内部 | #97 | 采纳"点击任意位置推进"的模式，但需排除输入模式 |

### 1.2 需要规避的

| 问题 | paper2galgame | 我们已有的正确做法 |
|------|--------------|------------------|
| Tailwind CDN 运行时编译 | `<script src="cdn.tailwindcss.com">` | 已有 Vite 构建 + scoped CSS |
| importmap 远程模块 | esm.sh CDN 加载 React | npm + 本地构建 |
| API Key 前端硬编码 | `geminiService.ts:46` | 后端 `.env` + 加密存储 |
| 无持久化 | 刷新即丢 | 完整后端 + 存档 API |
| **无用户输入** | 纯"听讲"模式 | 我们需要三模式对话框（核心差异） |
| 单角色写死 | 只有"丛雨" | 动态角色系统 |
| 无动效规范 | 动画零散 | 需建立全局规范 |

### 1.3 关键结论

paper2galgame 是优秀的 **Galgame 播放器原型**——它验证了 Web 视觉小说的基础交互模式。但它**不是交互式学习系统**：

- 没有用户输入 → 我们需要三模式对话框状态机（#96）
- 没有选择反馈 → 我们已有 ChoicePanel + API 支持
- 没有持久化 → 我们已有完整存档系统

**借鉴层面在「呈现」而非「交互」**：立绘切换、打字机跳过、Auto 模式、Backlog 的实现模式可直接复用。

---

## 二、技术选型方案

> **2026-03-27 更新**：2.1–2.4 已实现并合并。保留作为已实施方案的记录，供后续 Issue 参考。

### 2.1 对话框四模式状态机（#96 — ✅ 已实现 #107）

已采纳方案 A（单组件 + v-if）。DialogBox.vue 四模式：TEACHER_SPEAKING / USER_INPUT / CHOICES / WAITING。输入框在对话框内部，`Enter` 发送，`@click.stop` 防止模式切换误触发。

### 2.2 打字机 + 点击推进 + 长回复分段（#97 — ✅ 已实现 #108）

已实现：
- `splitIntoSegments`：按双换行分段，单段 >250 字时在句号处切割，fallback 到逗号/分号
- `startTyping` 返回 Promise，全段完成后 resolve
- 键盘 Space/Enter 推进（CHOICES/USER_INPUT 模式不拦截）
- 视觉指示：`▼ 下一段` / `▶ 点击继续`

未实现：Ctrl 按住快进（可作 follow-up）。

### 2.3 HUD 栏（#98 — ✅ 已实现 #107）

HudBar.vue 已实现：7 按钮（存档/读档/跳过/自动/回忆/设置/返回主页）+ 右侧状态栏（情绪/关系阶段/掌握度）。`position: fixed; bottom: 0; height: 40px; z-index: 30`。EmotionIndicator 功能合并到 HudBar 内部 computed。

### 2.4 回忆面板 Backlog（#98 — ✅ 已实现 #107）

BacklogPanel.vue 已实现：右侧 40% 宽度滑入，复用 `messages[]` 数组，教师金色左边框/用户绿色左边框，打开时自动滚动到底部。

### 2.5 角色立绘 + 情绪切换（#92 — 🔜 下一个）

**后端现状更新**（2026-03-27 调研确认）：
- `Character.sprites` JSON 字段 ✅（Migration 002）
- `EXPRESSION_MAP` ✅（`learning.py:31-40`）：curiosity→thinking, confusion→concerned, frustration→concerned, excitement→happy, satisfaction→happy, boredom→default, anxiety→concerned, neutral→default
- `ChatResponse.expression_hint` ✅：已在 chat 响应中返回
- 立绘上传 API ❌：#109 待实现

**前端实施方案**（采纳 paper2galgame 字典映射模式）：
- `CharacterDisplay.vue` 已存在但未使用——需替换 Learning.vue 的 120px 占位圆
- 加 `expression` prop，从 `ChatResponse.expression_hint` 传入
- 通过 `Character.sprites` 字典查找对应 URL：`sprites[expression] || sprites['default']`
- 无立绘时：增强占位符（大首字母 + 情绪色圈 + CSS transition 过渡动画）

**4 种表情对应关系**：

| expression_hint | 视觉 | 情绪来源 |
|----------------|------|---------|
| `default` | 默认/平静 | boredom, neutral |
| `happy` | 开心/满足 | excitement, satisfaction |
| `thinking` | 思考/好奇 | curiosity |
| `concerned` | 关切/担忧 | confusion, frustration, anxiety |

### 2.6 CSS 主题系统（✅ 已实现 #107）

main.css `:root` 定义完整变量系统（背景/文字/强调色/情感色/边框/字体/动效时长）。各新组件已使用 `var(--xxx)` 引用。残留：`char-avatar-large` 的 `linear-gradient(135deg, #4a4a8a, #2a2a4a)` 待 #92 替换时顺便修复。

### 2.7 字体加载（✅ 已实现 #107）

`index.html` 引入 Google Fonts（`<link rel="preconnect">` + `<link rel="stylesheet">`），非阻塞加载。对话用 Noto Serif SC，UI 用 Noto Sans SC，代码用 JetBrains Mono。

### 2.8 动效规范（✅ 大部分已实现）

main.css 定义全局 `@keyframes`：blink, slideUp, slideInRight, fadeSlideIn, flash, breathe。各组件通过 CSS 变量引用时长。

| 动效 | 状态 |
|------|------|
| 对话框 slideUp | ✅ |
| 打字机 blink 光标 | ✅ |
| 角色 fadeSlideIn | ✅ |
| 选项 stagger 飞入 | ✅ slideInChoice |
| 回忆面板 slideInRight | ✅ |
| 等待呼吸 breathe | ✅ |
| 关系进化覆盖层 | ❌ 未实现 |

---

## 三、实施进度与后续计划

### 已完成

```
Phase 1: #91 布局 → #107 (DialogBox + HudBar + BacklogPanel + 主题)  ✅
Phase 2: #108 (点击推进 + 分段 + 键盘)                                ✅
```

### 下一步

```
Phase 3 (并行):
  ├─ #92  角色立绘前端集成（CharacterDisplay.vue → Learning.vue）
  └─ #109 角色立绘上传 API（后端，#92 可先用硬编码路径开发）

Phase 4 (易用性):
  ├─ #104 parseApiError 全覆盖（6 个文件）
  ├─ #104 Login.vue 输入校验 + 密码提示
  └─ #104 Character.vue 人格预设模板

后续:
  ├─ 关系进化覆盖层动效
  ├─ Ctrl 快进（#97 未实现部分）
  ├─ Settings 打字机/自动滚动开关生效
  └─ #100 完整设计文档
```

### Reviewer 审查重点

Creator 提交 PR 时，Reviewer 重点审查：
- `expression_hint` → 立绘切换的映射正确性（#92）
- 无立绘时降级方案的视觉质量
- CSS 变量覆盖率（不允许新增硬编码颜色）
- 动效规范一致性（使用全局 `@keyframes` + CSS 变量时长）
- parseApiError 覆盖完整性（#104）

---

*文档由 Reviewer 维护，随 PR 合并同步更新。*
