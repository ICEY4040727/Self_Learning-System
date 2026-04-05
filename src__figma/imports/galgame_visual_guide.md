# Galgame 风格前端实现技术指导

> **文档类型**：Reviewer 技术规划（供 Creator 实施参考）
> **关联 Issue**：#118
> **日期**：2026-03-29
> **基于**：与 paper2galgame 的详细对比分析

---

## 〇、当前状态 vs 目标

我们的前端**功能层**已完成 Galgame 交互（4 层布局、DialogBox 状态机、打字机分段、键盘推进、立绘表情切换、HUD 7 按钮、BacklogPanel、SaveLoad）。但**视觉层**距离真正的 Galgame 感有明显差距。

本文档提供分阶段的技术方案，让前端从"功能正确"演进到"视觉沉浸"。

### 对比速览

```
当前：                              目标：
┌─────────────────────┐            ┌─────────────────────┐
│ ▓▓▓ 纯色渐变背景 ▓▓▓│            │ 🏫 场景背景图（教室） │
│                     │            │                     │
│      ┌──┐           │            │         ┌────┐      │
│      │??│ ← 占位圆   │            │         │角色│←立绘  │
│      └──┘           │            │         │弹跳│      │
│ ┌───────────────┐   │            │ ┌───────────────┐   │
│ │████ 85%黑底 ███│   │            │ │░░ 毛玻璃60% ░░│   │
│ │████ 对话框 ████│   │            │ │░░ 透出背景 ░░░│   │
│ └───────────────┘   │            │ └───────────────┘   │
│ [存档][读档]...[主页]│            │ [存档][读档]...[主页]│
└─────────────────────┘            └─────────────────────┘
```

---

## 一、Phase A — CSS 调整，一行改观感

> **目标**：不改架构，不加新组件，仅通过 CSS 调整提升视觉质量。
> **预计改动**：~30 行 CSS + ~10 行 JS

### A1: 对话框半透明毛玻璃

**当前**（DialogBox.vue）：
```css
.dialog-box {
  background: var(--bg-panel);  /* rgba(0,0,0,0.85) — 几乎不透明 */
  border: 1px solid var(--border-accent);
  border-radius: 4px;
}
```

**改为**：
```css
.dialog-box {
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);  /* Safari 兼容 */
  border: 1px solid rgba(255, 215, 0, 0.3);  /* 金边降低不透明度 */
  border-radius: 12px;
}
```

**原理**：
- `backdrop-filter: blur()` 创建毛玻璃效果——对话框后面的场景/角色变得模糊可见
- 透明度从 0.85 降到 0.55，让层次感显现
- 圆角从 4px 加到 12px，更温和更 VN
- 金色边框降低到 0.3 不透明度，不再那么硬

**注意**：`backdrop-filter` 在 Firefox < 103 不支持。我们的目标用户群（现代浏览器）覆盖率 >95%。不需要 polyfill，自然降级为普通半透明。

**同步更新 main.css**：
```css
:root {
  --bg-panel: rgba(0, 0, 0, 0.55);          /* 更新 */
  --bg-panel-blur: blur(16px);               /* 新增 */
  --border-accent-soft: rgba(255, 215, 0, 0.3);  /* 新增 */
}
```

### A2: 对话字号和行高

**当前**：`font-size: 17px; line-height: 1.9`

**改为**：`font-size: 19px; line-height: 1.8`

paper2galgame 用 20-24px bold。我们不需要那么大（我们有更多文字内容——苏格拉底式长回复），但 19px 是合理的中间值。移动端从 15px 提到 16px。

### A3: Name Tag 优化

**当前**：skewX(-8deg) 平行四边形 + 金橙渐变

保留当前设计，但加 `box-shadow` 增加悬浮感：
```css
.name-tag {
  /* 保留现有样式 */
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}
```

### A4: 角色逐句弹跳动画 ⭐

这是 paper2galgame 中**感知最强、成本最低**的效果。

**原理**：每次新对话显示时，角色立绘做一个微小的向上弹跳。这给静态立绘注入了"生命感"——角色在"说话"。

**实现**：

1. 在 `main.css` 新增关键帧：
```css
@keyframes jumpOnce {
  0%   { transform: translateY(0); }
  40%  { transform: translateY(-12px); }
  100% { transform: translateY(0); }
}
```

2. CharacterDisplay.vue 接收 `jumpKey` prop：
```vue
<div class="character-display" :class="position" :key="jumpKey">
  <!-- 内容不变 -->
</div>
```

```css
.character-display {
  animation: jumpOnce 0.3s ease-out;
}
```

3. Learning.vue 传递 `jumpKey`——每次新对话时递增：
```js
const jumpKey = ref(0)

// 在 typeSegment 或 startTyping 中：
jumpKey.value++
```

```vue
<CharacterDisplay
  :name="teacherName"
  :sprites="characterSprites"
  :expression="currentExpression"
  :jump-key="jumpKey"
  position="center"
/>
```

**关键**：`:key` 变化会让 Vue 重新渲染组件，从而重新触发 CSS animation。这是 paper2galgame 的原理（`key={jumpKey}`）。

### A5: 移动端角色缩小而非隐藏

**当前**：
```css
@media (max-width: 768px) {
  .character-layer { display: none; }
}
```

**改为**：
```css
@media (max-width: 768px) {
  .character-layer {
    bottom: 220px;
    transform: translateX(-50%) scale(0.6);
    opacity: 0.8;
  }
}
```

角色缩小到 60% 并略微透明，保持存在感但不挤占对话框空间。

---

## 二、Phase B — 场景背景

> **目标**：用真实/生成的场景图替换纯色渐变，实现视觉质变。
> **依赖**：Subject.scene_background 字段（已有），start_learning API 返回场景 URL

### B1: 默认场景背景

准备 2-3 张默认场景图：
- `default.jpg` — 暗色学院风教室/图书馆（适配暗色主题）
- `library.jpg` — 图书馆
- `starfield.jpg` — 星空（纯氛围）

**要求**：
- 分辨率 1920×1080（桌面）+ 720×1280（竖屏/移动端）
- 暗色调为主（配合我们的暗色主题和半透明对话框）
- 可以用 AI 生成（Midjourney/Stable Diffusion），注意许可证
- 存储在 `frontend/public/scenes/` 或通过后端 `/static/scenes/`

**Learning.vue 改动**：
```css
.scene-bg {
  width: 100%;
  height: 100%;
  background-image: url('/scenes/default.jpg');
  background-size: cover;
  background-position: center;
  transition: background-image 1s ease;
}
```

### B2: 动态场景切换

从 `start_learning` 响应中读取 `scene_background`：

后端（learning.py）：
```python
return {
    "session_id": ...,
    "teacher_persona": ...,
    "character_sprites": ...,
    "scene_background": subject.scene_background,  # 新增
}
```

前端（Learning.vue）：
```js
const sceneBackground = ref('/scenes/default.jpg')

// fetchActiveSession 中：
if (response.data.scene_background) {
  sceneBackground.value = response.data.scene_background
}
```

```vue
<div class="scene-bg" :style="{ backgroundImage: `url(${sceneBackground})` }"></div>
```

### B3: 场景过渡

两种方案：

**方案 A（简单）**：直接切换 + opacity 过渡
```css
.scene-bg {
  transition: opacity 0.5s ease;
}
```
切换时先设 opacity 0 → 换图 → opacity 1。

**方案 B（更好）**：双层交叉淡入
```vue
<div class="scene-layer">
  <Transition name="scene-fade" mode="out-in">
    <div class="scene-bg" :key="sceneBackground"
         :style="{ backgroundImage: `url(${sceneBackground})` }">
    </div>
  </Transition>
</div>
```

推荐方案 B，Vue Transition 自动处理交叉淡入。

---

## 三、Phase C — Home 页 VN 化

> **目标**：新用户第一次打开就感受到"这是 Galgame"。
> **当前 Home.vue**：CRUD 列表风格（header + grid cards）
> **目标 Home.vue**：全屏 VN 菜单 → 角色选择 → 科目选择

### C1: 全屏 VN 菜单

```
┌──────────────────────────────┐
│        ✦ 星空粒子背景 ✦       │
│                              │
│   苏 格 拉 底 学 习 系 统     │  ← 大标题 + 呼吸光效
│   基于苏格拉底教学法的 AI 学习 │  ← 副标题
│                              │
│        开 始 学 习            │  ← 竖排纯文字菜单
│        档 案 管 理            │     hover 金色 + 右移
│        角 色 设 定            │     字间距加大
│        系 统 设 置            │
│        退 出 登 录            │
│                              │
└──────────────────────────────┘
```

**设计要点**：
- 全屏 `100vw × 100vh`，与 Learning.vue 一致
- 背景：暗色渐变 + CSS 粒子动画（纯 CSS，不用 canvas）
- 标题：`font-family: var(--font-dialogue)`，字间距 `letter-spacing: 8px`，金色 `text-shadow` 呼吸光效
- 菜单项：竖排居中，纯文字，`font-size: 20px`，hover 时右移 8px + 变金色
- 无 header/nav bar

**CSS 粒子效果**（纯 CSS，无 JS）：
```css
.scene-particles span {
  position: absolute;
  width: 2px;
  height: 2px;
  background: rgba(255, 215, 0, 0.3);
  border-radius: 50%;
  animation: float var(--duration) ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0) translateX(0); opacity: 0.3; }
  50% { transform: translateY(-30px) translateX(10px); opacity: 0.8; }
}
```

用 `v-for="i in 20"` 生成 20 个粒子，每个随机位置和动画时长。

### C2: 角色选择场景化

点击"开始学习"→ 进入角色选择 phase：

```
┌──────────────────────────────┐
│          场景背景              │
│                              │
│   ┌───┐  ┌───┐  ┌───┐       │
│   │角1│  │角2│  │ + │       │  ← 角色立绘/占位符排列
│   │   │  │   │  │新建│       │     点击选中时放大
│   └───┘  └───┘  └───┘       │
│                              │
│ ┌──────────────────────────┐ │
│ │ 系统：选择你今天的学习伙伴  │ │  ← 对话框内提示
│ └──────────────────────────┘ │
└──────────────────────────────┘
```

选中角色后，该角色放大 + 弹跳，对话框显示角色台词（greeting）。

### C3: 科目选择对话化

角色选中后，对话框切换为 CHOICES 模式，显示该角色下的科目列表：

```
教师：「今天想学什么呢？」

  ▸ 高等数学
  ▸ 线性代数
  ▸ 概率论
```

选择后跳转到 Learning.vue。

---

## 四、Phase D — 氛围细节

### D1: 学习页背景微光效

在 Learning.vue 的 `.scene-layer` 上叠加一层微弱的浮动光斑：

```css
.scene-layer::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 30% 40%, rgba(255,215,0,0.03) 0%, transparent 60%),
              radial-gradient(circle at 70% 60%, rgba(96,165,250,0.03) 0%, transparent 60%);
  animation: ambientShift 20s ease-in-out infinite alternate;
}

@keyframes ambientShift {
  0% { opacity: 0.5; }
  100% { opacity: 1; transform: scale(1.05); }
}
```

极其微弱（3% 不透明度），但给静态背景注入了"呼吸"感。

### D2: "隐藏 UI" 按钮

HudBar 增加一个"隐藏"按钮：点击后对话框 + HUD 淡出，只留场景 + 角色。再点击屏幕恢复。这是 VN 标配功能，让用户欣赏立绘和场景。

```js
// Learning.vue
const hideUI = ref(false)
const toggleHideUI = () => { hideUI.value = !hideUI.value }
```

```vue
<div class="dialog-layer" v-show="!hideUI">
  <DialogBox ... />
</div>
<HudBar v-show="!hideUI" ... @hide-ui="toggleHideUI" />
<!-- 隐藏时点击任意处恢复 -->
<div v-if="hideUI" class="restore-overlay" @click="toggleHideUI"></div>
```

### D3: 对话框"下一段"指示器优化

当前用文字 `▶ 点击继续` / `▼ 下一段`。改为动画箭头：

```css
.next-indicator {
  /* 保留现有样式 */
}

.next-indicator::after {
  content: '▼';
  display: inline-block;
  animation: bounceDown 1s ease-in-out infinite;
}

@keyframes bounceDown {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(4px); }
}
```

---

## 五、实施顺序和依赖

```
Phase A（CSS 调整）← 无依赖，可立即开始
  A1 毛玻璃 + A2 圆角 + A3 字号  ← 一个 PR
  A4 弹跳动画                    ← 一个 PR（改 CharacterDisplay + Learning）
  A5 移动端                      ← 搭车 A4

Phase B（场景背景）← 需要场景图素材
  B1 默认场景图                   ← AI 生成 + 放到 public/scenes/
  B2 动态切换                    ← 后端返回 scene_background
  B3 过渡动画                    ← 搭车 B2

Phase C（Home VN 化）← 最大改动
  C1 全屏菜单                    ← 独立 PR
  C2+C3 场景化选择                ← 依赖 C1

Phase D（氛围）← 随时穿插
  D1-D3 各自独立
```

**建议 Creator 从 Phase A 开始**——改动量最小、视觉提升最明显。A1（毛玻璃）+ A4（弹跳）是性价比最高的两个改动。

---

## 六、CSS 变量扩展

Phase A-D 需要新增的 CSS 变量（加到 main.css `:root`）：

```css
:root {
  /* 现有变量保持不变 */

  /* 新增 — Galgame 视觉层 */
  --bg-panel-blur: blur(16px);
  --border-accent-soft: rgba(255, 215, 0, 0.3);
  --dialog-radius: 12px;
  --dialog-font-size: 19px;
  --dialog-font-size-mobile: 16px;

  /* 动画时长 */
  --anim-jump: 0.3s;
  --anim-scene-transition: 1s;
  --anim-ambient: 20s;
}
```

---

## 七、不做什么

以下方案评估后决定**不采用**：

| 不做 | 原因 |
|------|------|
| 改为亮色/粉色主题 | paper2galgame 是 bishoujo 粉色调，我们是暗色学院风，风格定位不同 |
| Canvas 粒子系统 | CSS 粒子够用，Canvas 增加复杂度且移动端性能风险 |
| GSAP/Anime.js | 当前所有动效纯 CSS 实现，无需引入 JS 动画库 |
| WebGL 背景 | 过度工程 |
| 角色 Live2D | 未来可考虑，当前静态立绘 + 弹跳 + 表情切换够用 |

---

*本文档由 Reviewer 维护，随实施进度更新。Creator 实施时 Reviewer 将在 PR 中重点审查：毛玻璃效果的跨浏览器兼容、弹跳动画的触发时机正确性、场景图加载性能、CSS 变量使用一致性。*
