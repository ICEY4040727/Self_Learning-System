# 「知遇」Galgame 学习系统 — Vue 3 UI 迁移技术规范

> **版本**：v1.0  
> **基准代码分支**：React 实现（Figma Make 生成，当前运行版本）  
> **冻结日期**：2026-04-05  
> **迁移目标**：Vue 3 + Vue Router + Pinia + Tailwind CSS v4  
> **范围**：样式、交互、动效迁移；行为逻辑同步重构（见第 10 节）

---

## 目录

1. [视觉基线](#1-视觉基线)
2. [Design Tokens](#2-design-tokens)
3. [动效规范](#3-动效规范)
4. [响应式规则](#4-响应式规则)
5. [页面级交互流程（状态机）](#5-页面级交互流程状态机)
6. [组件契约](#6-组件契约)
7. [数据映射表](#7-数据映射表)
8. [资源清单](#8-资源清单)
9. [验收标准](#9-验收标准)
10. [范围边界](#10-范围边界)

---

## 1. 视觉基线

### 1.1 设计来源

| 项目 | 说明 |
|---|---|
| Figma 文件 | 暂无正式 Figma 链接；设计基准来源于 `/src/imports/design_UI.md`（Creator+Reviewer+Owner 三方讨论定稿）与 `/src/imports/galgame_visual_guide.md`（技术实现规划） |
| 参考素材 | Owner 提供的 5 张 Galgame 截图（图1-5，已体现在当前实现中）；核心 UI 模式：底部横跨式半透明对话框、全屏场景菜单、侧排 HUD |
| 基准代码 | 当前 React 实现，构成本文档所有样式/交互数值的唯一可信来源 |
| 系统名称 | **知遇**（全局统一；登录页、主菜单页、设置页均已同步） |

### 1.2 各页面目标截图说明（文字替代）

由于无法导出截图，以下为每页的精确视觉描述，作为 Vue 实现对比基准：

| 页面 | 路由 | 视觉关键特征 |
|---|---|---|
| 登录页 | `/` | 全屏暗色背景图 + 居中毛玻璃登录面板（无圆角）；「知遇」金色标题带呼吸光效；粒子背景（28粒子，60% 金色） |
| 主菜单 | `/menu` | 全屏场景图 + 底部渐变覆盖；右侧竖排金色菜单（5项）；世界卡片网格（圆角12px）；底部横向对话框（当 course-select 阶段激活时） |
| 学习场景 | `/learn` | 四层布局：场景背景→角色立绘→对话框→HUD；对话框为底部全宽毛玻璃横条（无圆角）；名称标签为平行四边形金色条 |
| 档案馆 | `/archives` | 暗色背景（8% 透明度背景图）；顶部 header；三列 Recharts 图表区域；日记侧栏 |
| 设置页 | `/settings` | 暗色背景；顶部 header；居中 600px 表单区；三个设置分组面板 |

---

## 2. Design Tokens

### 2.1 颜色（含透明度）

所有颜色值直接从当前 CSS/TSX 提取，迁移时**不得擅自调整**。

#### 基础色板

```css
/* 页面底色 */
--color-base-bg:         #0a0a1e;   /* 所有页面 body */
--color-base-bg-alt:     #1a1a2e;   /* 深色变体（登录页渐变终点） */

/* 强调金色 */
--color-gold:            #ffd700;
--color-gold-80:         rgba(255, 215, 0, 0.80);
--color-gold-60:         rgba(255, 215, 0, 0.60);
--color-gold-45:         rgba(255, 215, 0, 0.45);
--color-gold-22:         rgba(255, 215, 0, 0.22);
--color-gold-18:         rgba(255, 215, 0, 0.18);
--color-gold-15:         rgba(255, 215, 0, 0.15);
--color-gold-12:         rgba(255, 215, 0, 0.12);
--color-gold-10:         rgba(255, 215, 0, 0.10);
--color-gold-08:         rgba(255, 215, 0, 0.08);
--color-gold-04:         rgba(255, 215, 0, 0.04);

/* 情感色（HUD 状态指示器） */
--color-emotion-curious:      #60a5fa;   /* 好奇 */
--color-emotion-excited:      #ffd700;   /* 兴奋 */
--color-emotion-confused:     #f97316;   /* 困惑 */
--color-emotion-satisfied:    #4adf6a;   /* 满足 */
--color-emotion-frustrated:   #ef4444;   /* 沮丧 */
--color-emotion-anticipating: #a78bfa;   /* 期待 */
--color-emotion-thinking:     #94a3b8;   /* 思考 */
--color-emotion-neutral:      #aaaaaa;   /* 中性 */

/* 关系阶段色 */
--color-stage-stranger:     #94a3b8;
--color-stage-acquaintance: #60a5fa;
--color-stage-friend:       #ffd700;
--color-stage-mentor:       #a78bfa;
--color-stage-partner:      #4adf6a;

/* 知识节点色 */
--color-knowledge-mastered:  #4adf6a;   /* mastery ≥ 0.65 */
--color-knowledge-learning:  #ffd700;   /* mastery ≥ 0.40 */
--color-knowledge-initial:   #f97316;   /* mastery ≥ 0.20 */
--color-knowledge-unknown:   #94a3b8;   /* mastery < 0.20 */
--color-knowledge-error:     #ef4444;   /* type = misconception */

/* 文字层级 */
--color-text-primary:   #f0f0ff;                  /* 对话正文 */
--color-text-ui:        rgba(240, 240, 255, 0.72); /* UI 文字 */
--color-text-secondary: rgba(255, 255, 255, 0.55); /* 次级 */
--color-text-muted:     rgba(255, 255, 255, 0.35); /* 弱化 */
--color-text-faint:     rgba(255, 255, 255, 0.20); /* 极弱 */

/* 角色 avatar 色 */
--color-sage-socrates-bg:    #4c1d95;
--color-sage-socrates-acc:   #7c3aed;
--color-sage-plato-bg:       #1e3a5f;
--color-sage-plato-acc:      #2563eb;
--color-sage-einstein-bg:    #064e3b;
--color-sage-einstein-acc:   #059669;
--color-sage-sunzi-bg:       #7c2d12;
--color-sage-sunzi-acc:      #b45309;
--color-traveler-bg:         #1e293b;
--color-traveler-acc:        #475569;
```

#### 组件级背景

```css
/* 毛玻璃对话框（galgame-dialog）*/
--dialog-bg-top:    rgba(5, 5, 20, 0.18);
--dialog-bg-mid:    rgba(5, 5, 20, 0.52);
--dialog-bg-bottom: rgba(5, 5, 20, 0.78);

/* 深色面板（galgame-panel）*/
--panel-bg:         rgba(8, 8, 28, 0.94);

/* HUD 条（galgame-hud）*/
--hud-bg:           rgba(0, 0, 0, 0.88);

/* 输入框（galgame-input）*/
--input-bg:         rgba(255, 255, 255, 0.07);
--input-bg-focus:   rgba(255, 255, 255, 0.10);

/* 登录面板（galgame-login-panel）*/
--login-bg-top:     rgba(5, 5, 20, 0.22);
--login-bg-mid:     rgba(5, 5, 20, 0.62);
--login-bg-bottom:  rgba(5, 5, 20, 0.88);

/* 选项卡片（galgame-choice）*/
--choice-bg:        rgba(255, 215, 0, 0.04);
--choice-bg-hover:  rgba(255, 215, 0, 0.12);

/* 发送按钮 */
--send-btn-bg:       rgba(255, 215, 0, 0.85);
--send-btn-bg-hover: #ffd700;
--send-btn-bg-disabled: rgba(255, 215, 0, 0.30);
```

### 2.2 字体族 / 字号 / 字重 / 行高

#### 字体族（3族）

```css
/* 对话正文 — 宋体气质，书卷感 */
.font-dialogue {
  font-family: 'Noto Serif SC', 'Songti SC', 'SimSun', serif;
}

/* UI 元素 — 黑体清晰 */
.font-ui {
  font-family: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* 代码/等宽 */
.font-mono-code {
  font-family: 'JetBrains Mono', monospace;
}
```

加载来源：Google Fonts CDN（见第 8 节）

#### 字号规格表

| 用途 | class | 字族 | px | 字重 | 行高 | 字间距 |
|---|---|---|---|---|---|---|
| 对话正文（speaking） | `.font-dialogue` | serif | 19 | 400 | 1.9 | — |
| 对话正文（choices） | `.font-dialogue` | serif | 18 | 400 | 1.85 | — |
| 用户输入框 | `.font-dialogue` + `.galgame-input` | serif | 17 | 400 | 1.8 | — |
| 菜单项 | `.galgame-menu-item` | sans | 17 | 400 | — | 7px |
| 名称标签 | `.galgame-name-tag` | sans | 14 | 600 | — | 3px |
| HUD 按钮 | `.galgame-hud-btn` | sans | 12 | 400 | — | — |
| HUD 状态文字 | font-ui | sans | 12 | 400 | — | — |
| 角色名（立绘底部） | font-ui | sans | 14 | 500 | — | 2px |
| 角色职称（立绘底部） | font-ui | sans | 11 | 400 | — | 1px |
| 卡片标题 | font-ui | sans | 13 | — | — | 2px |
| 页面大标题（档案/设置） | font-ui | sans | 16 | — | — | 4px |
| 系统主标题（登录） | font-dialogue | serif | 28+ | 400 | — | 8px |
| 等待点（·····） | font-dialogue | serif | 24 | 400 | — | 8px |
| 选项提示箭头（▸） | font-ui | sans | 11 | — | — | — |
| 世界卡片描述 | font-ui | sans | 12 | 400 | 1.5 | — |
| 小角标/Badge | font-ui | sans | 9 | — | — | 1px |

### 2.3 间距体系

项目使用**行内 style** 为主，无统一间距变量，但呈现以下规律：

```
页面内边距（外层容器）:  24px (左右)
对话框内边距:           16px (上下) × 28px (左右)
HUD 高度:              44px
HUD 内边距:            0 16px
面板内边距:            14-22px
卡片网格间距:           12-16px (gap)
名称标签距对话框顶部:   -34px (absolute top)
对话框距 HUD 顶部:      54px (bottom)
角色立绘底部距 HUD:     calc(230px + 44px)
世界卡片最小高度:       180px
字符精灵宽度（Sage）:  170px
字符精灵高度（Sage）:  340px
字符精灵宽度（Traveler）: 140px
字符精灵高度（Traveler）: 280px
```

### 2.4 圆角

```
galgame-dialog:      border-radius: 0  (无圆角，直角横条)
galgame-panel:       border-radius: 0  (无圆角，但 SaveLoadPanel/KnowledgeGraphModal 使用 16px)
galgame-login-panel: border-radius: 0
galgame-choice:      border-radius: 0
galgame-input:       border-radius: 0
galgame-send-btn:    border-radius: 0
galgame-name-tag:    border-radius: 0 + clipPath polygon（平行四边形裁切）
galgame-hud-btn:     border-radius: 5px  ← 唯一例外
world-card:          border-radius: 12px
角色 Avatar 圆:      border-radius: 50%
SaveLoadPanel 面板:  border-radius: 16px
KnowledgeGraphModal: border-radius: 16px
```

### 2.5 边框

```css
/* 标准金框 */
border: 1px solid rgba(255, 215, 0, 0.22);  /* dialog 主边 */
border-top: 1px solid rgba(255, 215, 0, 0.10); /* dialog 顶部更浅 */

/* 面板框 */
border: 1px solid rgba(255, 215, 0, 0.18);

/* HUD 顶线 */
border-top: 1px solid rgba(255, 215, 0, 0.12);

/* 选项框 */
border: 1px solid rgba(255, 215, 0, 0.12); /* 默认 */
border: 1px solid rgba(255, 215, 0, 0.55); /* hover */

/* 输入框 */
border: 1px solid rgba(255, 215, 0, 0.25); /* 默认 */
border: 1px solid rgba(255, 215, 0, 0.60); /* focus */

/* 世界卡片 */
border: 1px solid rgba(255, 215, 0, 0.15); /* 默认 */
border: 1px solid rgba(255, 215, 0, 0.55); /* hover */
border: 1px solid rgba(255, 215, 0, 0.80); /* selected */

/* HUD 按钮 */
border: 1px solid rgba(255, 255, 255, 0.10); /* 默认 */
border: 1px solid rgba(255, 215, 0, 0.45);   /* hover/active */
```

### 2.6 阴影

```css
/* 名称标签 */
box-shadow: 0 2px 12px rgba(255, 215, 0, 0.3);

/* 世界卡片 hover */
box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5), 0 0 20px rgba(255, 215, 0, 0.15);

/* 世界卡片 selected */
box-shadow: 0 0 30px rgba(255, 215, 0, 0.25);

/* 选项 hover（左侧光条） */
box-shadow: -3px 0 12px rgba(255, 215, 0, 0.2);

/* 输入框 focus */
box-shadow: 0 0 12px rgba(255, 215, 0, 0.15);

/* 发送按钮 hover */
box-shadow: 0 0 20px rgba(255, 215, 0, 0.45);

/* HUD 按钮 hover 与 active — 无 box-shadow，用颜色区分 */

/* 角色立绘 active drop-shadow */
filter: drop-shadow(0 0 18px {accentColor}80) drop-shadow(0 0 36px {accentColor}30);

/* 角色立绘 inactive drop-shadow */
filter: drop-shadow(0 4px 16px rgba(0,0,0,0.7));

/* 角色立绘 active box-shadow（portrait frame） */
box-shadow: 0 0 20px {accentColor}40, inset 0 0 20px {accentColor}10;

/* 场景背景微光（radial，非 box-shadow） */
radial-gradient(ellipse at 30% 40%, rgba(255,215,0,0.025) 0%, transparent 55%)
radial-gradient(ellipse at 70% 60%, rgba(96,165,250,0.025) 0%, transparent 55%)
```

### 2.7 模糊（backdrop-filter）

```css
galgame-dialog:       backdrop-filter: blur(20px) saturate(1.5);
galgame-panel:        backdrop-filter: blur(22px);
galgame-hud:          backdrop-filter: blur(12px);
galgame-login-panel:  backdrop-filter: blur(22px);
```

> ⚠️ **关键约束**：所有 `backdrop-filter` 组件的**直接祖先元素必须保持 `opacity: 1`**。在 Vue `<Transition>` 动画中，禁止对包含 `backdrop-filter` 的组件的父元素使用 `opacity` 过渡——改用 `transform: translateY()` 单独驱动（见第 3 节）。

### 2.8 z-index 层级

```
Layer 0: 场景背景图          z-index: auto (文档流)
Layer 1: 背景渐变遮罩        z-index: auto
Layer 2: 粒子背景            z-index: auto (pointer-events: none)
Layer 3: 角色立绘层          z-index: auto (pointer-events: none)
Layer 4: 对话框              z-index: auto
Layer 5: HUD 条              z-index: auto
Layer 10: Backlog 面板        z-index: 30
Layer 10: SaveLoad 面板       z-index: 40
Layer 10: KnowledgeGraph 弹窗 z-index: 40
Layer 11: 关系阶段 Overlay    z-index: 50
```

---

## 3. 动效规范

### 3.1 关键帧动画清单

以下关键帧来自 `/src/styles/galgame.css`，迁移时原样复制到 Vue 项目的全局 CSS：

| 动画名 | 时长 | easing | 用途 |
|---|---|---|---|
| `jumpOnce` | 0.35s | ease-out | 角色立绘发言跳动（key 变化触发重绘） |
| `breatheGlow` | 3.5s | ease-in-out | 系统标题金色呼吸光效（infinite） |
| `floatParticle` | 6-16s（随机）| ease-in-out | 粒子浮动（infinite） |
| `bounceDown` | 0.8s | ease-in-out | 打字机游标闪烁；▼ 点击继续指示器（1.3s） |
| `ambientPulse` | 18s | ease-in-out | 场景环境光晕脉冲（infinite alternate） |
| `stageReveal` | 0.8s | ease-out | 关系阶段升级中央内容出现（both） |
| `goldRipple` | 2.5s | ease-out | 关系阶段升级同心圆波纹（infinite） |
| `slideInRight` | — | — | 面板右侧滑入（opacity+translateX） |
| `slideInUp` | — | ease-out | 通用向上滑入 |
| `slideInLeft` | — | — | 通用向左滑入 |
| `fadeIn` | — | — | 通用淡入 |
| `choiceStagger` | 0.3s | ease-out | 选项逐条飞入（translateX 16px→0） |
| `dotFlash` | 1.5s | ease-in-out | 等待状态点点闪烁（每点延迟 0.25s） |
| `borderGlow` | — | — | 边框脉冲发光 |
| `menuItemIn` | — | — | 菜单项左侧飞入 |
| `panelIn` | 0.3s | ease-out | 面板出现（scale 0.96→1 + translateY 8→0） |
| `worldCardIn` | — | ease-out | 世界卡片入场（translateY 20→0 + scale 0.97→1） |

### 3.2 Motion 组件动效规范（React → Vue 对照）

#### 页面切换

```
触发：路由跳转
React: motion.div initial/animate/exit on RouterProvider
Vue 对应:
  <RouterView v-slot="{ Component }">
    <Transition name="page-fade" mode="out-in">
      <component :is="Component" />
    </Transition>
  </RouterView>

CSS:
  .page-fade-enter-from { opacity: 0; }
  .page-fade-enter-active { transition: opacity 0.4s ease; }
  .page-fade-leave-to { opacity: 0; }
  .page-fade-leave-active { transition: opacity 0.3s ease; }
```

#### 对话框出现 / 消失

```
触发：!hideUI && !anyPanelOpen 变为 true/false
⚠️ 禁止使用 opacity 动画（破坏 backdrop-filter）
只做 translateY 位移：

CSS:
  .dialog-slide-enter-from { transform: translateY(36px); }
  .dialog-slide-enter-active { transition: transform 0.35s ease-out; }
  .dialog-slide-leave-to { transform: translateY(36px); }
  .dialog-slide-leave-active { transition: transform 0.35s ease-out; }
```

#### 角色立绘入场

```
触发：!hideUI 变为 true
时长: 0.5s
属性: opacity 0→1（父层整体，不影响子层 backdrop-filter）

⚠️ 角色层 wrapper 整体做 opacity 动画是安全的，
   因为对话框位于独立的同级 DOM 节点，不是角色层的子元素。
```

#### 选项列表逐条飞入

```
触发：mode 切换为 'choices'
动画：choiceStagger（translateX 16px→0, opacity 0→1）
每项延迟：i * 0.09s（第0项0s，第1项0.09s，第2项0.18s，第3项0.27s）
```

#### 面板弹窗出现

```
触发：isOpen = true
动画：panelIn（scale 0.96→1, translateY 8→0, opacity 0→1）
时长：0.3s ease-out
```

#### 关系阶段升级 Overlay

```
���发：stageEventOpen = true
同心圆：goldRipple 2.5s × 3圈，延迟 0s / 0.6s / 1.2s，infinite
中央内容：stageReveal 0.8s ease-out both
```

#### HUD 出现

```
触发：页面初始化
时长：0.4s，延迟 0.2s（晚于对话框）
属性：opacity 0→1, translateY 20→0
⚠️ HUD 自身无 backdrop-filter，可安全使用 opacity 动画
```

#### 场景背景初始缩放

```
触发：LearningPage 挂载
时长：1.5s
属性：scale 1.05→1, opacity 0→1
```

#### 角色发言跳动

```
触发：每次 stepIndex 变化（且对应发言方切换）
方式：Vue 中用 :key="jumpKey" + CSS animation jumpOnce
时长：0.35s ease-out（当前实现），0.3s ease-out（原规范）
```

#### 自动模式延迟

```
触发：autoMode = true 且 mode = 'speaking'
延迟：2800ms 后自动推进（settingsPage 中可配置为 1000-5000ms）
```

### 3.3 CSS 类动画附加规范

| 类名 | 动效 | 时长 |
|---|---|---|
| `.breathe-glow` | breatheGlow infinite | 3.5s |
| `.bounce-indicator` | bounceDown infinite | 1.3s |
| `.galgame-menu-item:hover` | translateX(10px) | 0.3s ease |
| `.galgame-choice:hover` | translateX(6px) | 0.2s ease |
| `.world-card:hover` | translateY(-4px) scale(1.02) | 0.3s ease |
| `.galgame-hud-btn:hover` | color + border 变金色 | 0.15s ease |

---

## 4. 响应式规则

### 4.1 断点

项目当前**不使用 Tailwind 断点媒体查询**（所有布局为全屏绝对定位），但参考文档定义了以下断点意图：

| 断点 | 宽度 | 策略 |
|---|---|---|
| Desktop | ≥ 1024px | 默认布局，所有功能完整 |
| Tablet | 768–1023px | 角色立绘缩小到 75%，对话框 left/right 从 16px 增至 24px |
| Mobile | < 768px | 见 4.2 节 |

### 4.2 移动端缩放策略

参考 `/src/imports/galgame_visual_guide.md` Phase A5：

```css
/* 角色立绘层 — 移动端 */
@media (max-width: 768px) {
  /* 不隐藏，缩小并半透明 */
  .character-layer {
    bottom: 220px;
    transform-origin: bottom center;
    transform: scale(0.6);
    opacity: 0.8;
  }
}

/* 对话框 — 移动端字号 */
@media (max-width: 768px) {
  .galgame-dialog .font-dialogue { font-size: 16px; }
}

/* HUD — 移动端 */
@media (max-width: 768px) {
  .galgame-hud-btn span { display: none; } /* 只显示图标 */
}
```

### 4.3 双角色布局在小屏下的精确行为

学习场景存在「Sage（左）+ Traveler（右）」双立绘布局：

| 状态 | 桌面 | ≤ 768px |
|---|---|---|
| Sage 发言 | Sage scale(1.0) 左侧 8%；Traveler scale(0.62) 右侧 8% | Sage scale(0.6) 左侧 2%；Traveler scale(0.37) 右侧 2% |
| Traveler 发言（input mode）| Traveler scale(1.214) 右侧 8%；Sage scale(0.68) 左侧 8% | Traveler scale(0.73) 右侧 2%；Sage scale(0.41) 左侧 2% |
| 面板打开（anyPanelOpen）| 双角色 filter: brightness(0.4) | 同左，额外 opacity: 0.3 |
| HideUI 模式 | 对话框+HUD 消失，角色全亮 | 同左 |

scale 变化使用 `transition: transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)`（弹性效果）。

### 4.4 主菜单世界卡片网格

```css
/* 世界选择 — 卡片网格 */
grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
gap: 16px;

/* 移动端强制单列 */
@media (max-width: 640px) {
  grid-template-columns: 1fr;
}
```

---

## 5. 页面级交互流程（状态机）

### 5.1 LoginPage（`/`）

```
状态: mode('login' | 'register'), loading(bool), error(string), showPw(bool)

[初始] mode=login
  │
  ├─ 点击"注册" → mode=register (AnimatePresence 切换表单)
  ├─ 填写 username + password → 表单校验
  │     ├─ 空值 → error='请填写用户名和密码'（红色淡入，3s 消失）
  │     ├─ 注册时 password≠confirmPw → error='两次密码不一致'
  │     └─ 通过 → loading=true → 模拟延迟 800ms → navigate('/menu')
  ├─ 点击密码眼睛图标 → showPw toggle
  └─ loading=true 期间: 按钮显示"进入中…"，禁用重复提交
```

**空态**：初始字段为空，error 为空，提交按钮为 #ffd700 背景  
**错误态**：error 字符串非空，显示红色 `#df4a4a` 文字，3s 后自动清除  
**加载态**：按钮文字改变，pointer-events: none

### 5.2 MainMenuPage（`/menu`）

五阶段流程状态机：

```
type MenuPhase = 'main' | 'world-select' | 'course-select' | 'memory-vault' | 'character-manage'

[main] 主菜单
  ├─ 点击"开始学习" → phase='world-select'
  ├─ 点击"档案管理" → navigate('/archives')
  ├─ 点击"角色管理" → phase='character-manage'
  └─ 点击"系统设置" → navigate('/settings')

[world-select] 世界选择
  ├─ 点击世界卡片 → selectedWorld = world → phase='course-select'
  ├�� 点击"+ 新建世界" → showCreateWorld=true → 弹 CreateWorldModal
  │     └─ 确认创建 → worlds 追加 → showCreateWorld=false
  └─ 点击"← 返回" → phase='main'

[course-select] 课程选择（显示 selectedWorld 的 sage 对话框）
  ├─ 点击课程选项（选项列表模式） →
  │     ├─ world.activeCheckpoints.length > 0 → phase='memory-vault'
  │     └─ 否则 → navigate('/learn?worldId=X&courseId=Y')
  ├─ 点击"+ 新增课程" → showAddCourse=true → 弹 AddCourseModal
  │     └─ 确认 → worlds/selectedWorld 追加课程 → showAddCourse=false
  └─ 点击"← 返回" → phase='world-select'

[memory-vault] 记忆库（选择存档分叉）
  ├─ 点击存档槽 → navigate('/learn?...&checkpointId=Z')
  ├─ 点击"全新旅途" → navigate('/learn?worldId=X&courseId=Y')
  └─ 点击"← 返回" → phase='course-select'

[character-manage] 角色管理
  ├─ 点击"+ 新建知者" → createCharInitType='sage' → showCreateChar=true
  ├─ 点击"+ 新建旅者" → createCharInitType='traveler' → showCreateChar=true
  │     └─ CreateCharacterModal 确认 → customCharacters 追加
  ├─ 点击卡片删除（自定义角色） → customCharacters 过滤移除
  └─ 点击"← 返回" → phase='main'
```

**AnimatePresence 注意**：phase 变化时旧内容 exit，新内容 enter，使用 `mode="out-in"`（Vue: `<Transition mode="out-in">`）。

### 5.3 LearningPage（`/learn`）

对话流状态机（核心）：

```
状态: stepIndex(number), skipSignal(number), autoMode(bool), hideUI(bool)
      backlogOpen, saveOpen, knowledgeOpen, stageEventOpen(bool)
      sageJumpKey, travelerJumpKey(number)
      sageExpression(Expression)
      currentEmotion(string), masteryPercent(number)
      pendingStageEvent(RelationshipStage | null)

anyPanelOpen = backlogOpen || saveOpen || knowledgeOpen || stageEventOpen

[每次 stepIndex 变化]
  1. 更新 sageExpression = currentStep.expression
  2. 更新 currentEmotion = currentStep.emotion
  3. 触发对应角色 jumpKey += 1（sage/traveler）
  4. 若 mode='speaking' 且 text 非空 → 追加 messages[]

[mode='speaking'] 打字机模式
  ├─ 点击对话框 / 按空格
  │     ├─ isTyping=true → skipTyping()（立即显示全文）
  │     └─ isTyping=false → advanceStep()
  ├─ autoMode=true → 2800ms 后自动 advanceStep()
  └─ skipSignal 变化 → skipTyping()（HUD 跳过按钮）

[mode='choices'] 选项模式
  └─ 点击选项 i → 追加 message（我） → advanceStep()

[mode='input'] 输入模式
  └─ 发送文字 → 追加 message（我）
              → 跳至下一个 waiting step（若存在）
              → 1500ms 后再推进一步（模拟 LLM 延迟）
              → masteryPercent += 3（上限 100）

[mode='waiting'] 等待模式
  └─ 无交互（dotFlash 动画，自动等待 handleInputSend 回调推进）

[advanceStep]
  ├─ currentStep.triggerStageEvent && nextStageLabel && !pendingStageEvent
  │     → setPendingStageEvent(label) → stageEventOpen=true (中断推进)
  └─ stepIndex < script.length-1 → stepIndex += 1

[stageEventOpen=true] 关系阶段升级 Overlay
  └─ 点击任意处 → stageEventOpen=false, pendingStageEvent=null → stepIndex += 1

[HUD 按钮]
  存档 → saveMode='save', saveOpen=true
  读档 → saveMode='load', saveOpen=true
  跳过 → skipSignal += 1
  自动 → autoMode toggle
  回忆 → backlogOpen=true
  知识图谱 → knowledgeOpen=true
  设置 → navigate('/settings')
  返回主页 → navigate('/menu')

[hideUI]
  点击场景（当 hideUI=false 且无面板时）→ setHideUI(true)
  点击任意处（当 hideUI=true）→ setHideUI(false)
```

### 5.4 ArchivesPage（`/archives`）

```
状态: diaryOpen(bool), newEntry(string)

[初始] 显示四栏：情感轨迹折线图 / 情感分布饼图 / 概念掌握进度 / 日记列表
  ├─ 点击"写日记" → diaryOpen=true
  │     ├─ 输入 newEntry → 点击提交 → 追加 DIARY_ENTRIES（本地，无持久化）
  │     └─ 点击取消 → diaryOpen=false
  └─ 点击"← 返回" → navigate('/menu')
```

**数据**：所有数据来自 `mockData.ts` 静态常量（EMOTION_HISTORY、EMOTION_PIE、CONCEPT_PROGRESS、DIARY_ENTRIES）

### 5.5 SettingsPage（`/settings`）

```
状态: provider('claude'|'openai'|'ollama'), apiKey(string), showKey(bool),
      typewriterOn(bool), autoScrollOn(bool), particlesOn(bool),
      autoModeDelay(number), saved(bool)

[操作]
  切换 provider → setProvider (radio group)
  输入 apiKey → setApiKey
  点击眼睛 → showKey toggle
  点击"保存" → saved=true → 2000ms → saved=false（Toast 反馈）
  toggles → 各自 setState
  slider → setAutoModeDelay (1.0-5.0, step 0.5)
  点击"← 返回" → navigate('/menu')

[保存成功态]
  按钮文字变为"✓ 已保存"，颜色变为 #4adf6a，2s 后复原
```

---

## 6. 组件契约

### 6.1 DialogBox

**Vue 文件**：`components/DialogBox.vue`

#### Props

```typescript
interface DialogBoxProps {
  mode: 'speaking' | 'input' | 'choices' | 'waiting';
  speakerName: string;       // 名称标签文字（input mode 时固定显示"我"）
  fullText: string;          // 完整文字（speaking/choices 模式）
  choices?: string[];        // 选项列表（choices 模式）
  placeholder?: string;      // 输入框占位文字（input 模式）
  skipTypingSignal: number;  // 递增时触发跳过打字机
}
```

#### Emits

```typescript
emits: {
  continue: () => void;           // speaking 模式点击/打字完成后
  choiceSelect: (index: number) => void;
  inputSend: (text: string) => void;
}
```

#### 内部状态

| 状态 | 类型 | 说明 |
|---|---|---|
| `displayedText` | string | 打字机当前显示文字 |
| `isTyping` | boolean | 打字机进行中 |
| `inputValue` | string | 用户输入框内容 |
| `typingTimer` | ref | setInterval 句柄 |

#### 状态→样式映射

| 状态 | 视觉变化 |
|---|---|
| speaking + isTyping | 游标闪烁（bounceDown 0.8s） |
| speaking + !isTyping | 显示"▼ 点击继续"（bounce-indicator 1.3s） |
| speaking | cursor: pointer |
| input | cursor: default；名称标签显示"我" |
| choices | 选项 choiceStagger 飞入；choices[i].startsWith('💡') 时蓝色 |
| waiting | 5个点 dotFlash 动画，每点延迟 0.25s |

#### 约束

- 打字机间隔：38ms/字符
- 发送按钮：`disabled` 当 inputValue.trim() 为空
- Enter 发送，Shift+Enter 换行
- `backdrop-filter` 在 `.galgame-dialog` 上；父层**不得**有 opacity 动画

---

### 6.2 HudBar

**Vue 文件**：`components/HudBar.vue`

#### Props

```typescript
interface HudBarProps {
  emotion: string;          // 情感标签（映射到 EMOTION_COLORS）
  relationshipStage: string; // 如"朋友"
  masteryPercent: number;   // 0-100
  autoMode: boolean;        // 自动模式是否激活
}
```

#### Emits

```typescript
emits: {
  save: () => void;
  load: () => void;
  skip: () => void;
  autoToggle: () => void;
  backlog: () => void;
  settings: () => void;
  home: () => void;
  knowledgeGraph: () => void;
}
```

#### 状态→样式映射

| 元素 | 默认 | hover | active（autoMode） |
|---|---|---|---|
| `.galgame-hud-btn` | color: rgba(200,200,220,0.75)，border 白色10% | color: #ffd700，border 金色45% | color: #ffd700，border 金色45%，bg 金色10% |
| 自动按钮激活指示 | 无 | — | 绿点 #4adf6a（fontSize:9） |
| 情感点 | 6px 圆，emotionColor | — | — |
| 掌握度条 | 60px × 4px，白色10%背景 | — | — |
| 掌握度填充 | 渐变 #ffd700→#4adf6a，width: {n}% | — | — |

---

### 6.3 KnowledgeGraphModal

**Vue 文件**：`components/KnowledgeGraphModal.vue`

#### Props

```typescript
interface KnowledgeGraphModalProps {
  isOpen: boolean;
  worldName: string;
}
```

#### Emits

```typescript
emits: { close: () => void }
```

#### 内部状态

| 状态 | 类型 | 说明 |
|---|---|---|
| `selectedNode` | KnowledgeNode \| null | 点击节点后显示详情 |

#### 节点样式规则

```
type='misconception' → fill: #ef4444, label: '⚠ 误解'
mastery ≥ 0.65 → fill: #4adf6a, label: '已掌握'
mastery ≥ 0.40 → fill: #ffd700, label: '学习中'
mastery ≥ 0.20 → fill: #f97316, label: '初识'
mastery < 0.20 → fill: #94a3b8, label: '未接触'

节点半径：10px（未选中）/ 14px（selected）
边：1px rgba(255,215,0,0.3) stroke，带中文 label
SVG 视口：800×460
容器最大宽度：860px（95vw），最大高度：90vh
面板动画：panelIn 0.3s ease-out
```

#### 状态列表

| 状态 | 视觉 |
|---|---|
| 默认 | 所有节点可点击 |
| selectedNode 非空 | 右侧详情面板显示节点名/类型/掌握度 |
| 节点 hover | 光标 pointer |

---

### 6.4 SaveLoadPanel（CheckpointPanel）

**Vue 文件**：`components/SaveLoadPanel.vue`

#### Props

```typescript
interface SaveLoadPanelProps {
  isOpen: boolean;
  mode: 'save' | 'load';
  checkpoints: Checkpoint[];   // 最多展示 6 个槽位
}
```

#### Emits

```typescript
emits: {
  close: () => void;
  save: (slot: number) => void;    // slot index 0-5
  load: (checkpoint: Checkpoint) => void;
  delete: (id: number) => void;
}
```

#### 槽位状态

| 状态 | 视觉 |
|---|---|
| 有存档 | 渐变缩略图背景 + 存档名 + 日期 + 阶段 + 掌握度 + 预览文本 |
| 空���位 | "+" 虚线框 |
| 存档模式 hover | 金色边框 |
| 读档模式 hover | 金色边框 + "读取"按钮 |
| 有存档 + 存档模式 | 显示"覆盖"按钮 |
| 有存档 + 读档模式 | 显示"读取"+"删除"按钮 |

**场景渐变映射**：

```javascript
const SCENE_GRADIENTS = {
  academy: 'linear-gradient(135deg, #1e3a5f 0%, #4c1d95 100%)',
  garden:  'linear-gradient(135deg, #064e3b 0%, #1e3a5f 100%)',
  market:  'linear-gradient(135deg, #7c2d12 0%, #1e3a5f 100%)',
  default: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
}
```

---

### 6.5 CharacterSprite

**Vue 文件**：`components/CharacterSprite.vue`

#### Props

```typescript
interface CharacterSpriteProps {
  character: Character;
  expression: 'default' | 'happy' | 'thinking' | 'concerned' | 'surprised';
  position: 'left' | 'right';
  jumpKey: number;    // 变化时重新触发 jumpOnce 动画
  isActive: boolean;  // 是否为当前说话方
  scale?: number;     // 默认 1.0
}
```

#### 无 emits（纯展示组件）

#### 状态→样式映射

| 状态 | 视觉 |
|---|---|
| `isActive=true` | drop-shadow 双层发光，border 金色80%，inset glow，顶部3点 dotFlash，底部名称 #ffd700 + text-shadow |
| `isActive=false` | drop-shadow 暗色，border 白色8%，名称 rgba(255,255,255,0.8) |
| `jumpKey` 变化 | :key 重置 → jumpOnce 0.35s 重播 |
| `expression` 变化 | 表情文字 + 颜色 transition 0.3s |

#### 尺寸规则

```
Sage:     width=170px, height=340px
Traveler: width=140px, height=280px
大 symbol 字号 = width * scale * 0.45
symbol 颜色 = accentColor + '50'（约 31% 透明度）
```

#### 表情映射

```javascript
const EXPRESSION_SYMBOLS = {
  default:   '◡‿◡',
  happy:     '＾‿＾',
  thinking:  '（－_－）',
  concerned: '(ó_ò)',
  surprised: '( ꒪⌓꒪ )',
}
const EXPRESSION_COLORS = {
  default:   'rgba(255,255,255,0.7)',
  happy:     'rgba(74, 223, 106, 0.9)',
  thinking:  'rgba(96, 165, 250, 0.9)',
  concerned: 'rgba(249, 115, 22, 0.9)',
  surprised: 'rgba(255, 215, 0, 0.9)',
}
```

---

### 6.6 RelationshipStageOverlay

**Vue 文件**：`components/RelationshipStageOverlay.vue`

#### Props

```typescript
interface RelationshipStageOverlayProps {
  isOpen: boolean;
  newStage: RelationshipStage;
  sageName: string;
  specialDialogue: string;
}
```

#### Emits

```typescript
emits: { continue: () => void }
```

#### 内部无状态（纯展示）

点击任意区域触发 `continue`。

---

### 6.7 ParticleBackground

**Vue 文件**：`components/ParticleBackground.vue`

#### Props

```typescript
interface ParticleBackgroundProps {
  count?: number;      // 默认 28
  goldRatio?: number;  // 0-1，金色粒子比例，默认 0.6
}
```

#### 无 emits

粒子参数在 `setup()` 中用 `useMemo`（Vue: `computed`）一次性生成，避免响应式重算：

```javascript
// 每粒子属性
{
  left: `${Math.random() * 100}%`,
  top:  `${Math.random() * 100}%`,
  size: Math.random() * 2.5 + 1,      // px
  duration: Math.random() * 10 + 6,   // s
  delay: Math.random() * 8,           // s
  opacity: Math.random() * 0.4 + 0.15,
}
// 金色：rgba(255, 215, 0, opacity)，boxShadow 半径 size*3
// 蓝色：rgba(147, 197, 253, opacity*0.7)，boxShadow 半径 size*2
```

各页面粒子参数：

| 页面 | count | goldRatio |
|---|---|---|
| LoginPage | 28（默认） | 0.6（默认） |
| MainMenuPage | — | — |
| ArchivesPage | 16 | 0.5 |
| SettingsPage | 14 | 0.5 |
| LearningPage | 无（使用 ambientPulse 微光代替） | — |

---

## 7. 数据映射表

### 7.1 核心类型定义（mockData → 后端 API）

| Mock 字段（TypeScript） | 对应后端 API 字段（预期） | 类型 | 转换规则 | 缺失时兜底 |
|---|---|---|---|---|
| `Character.id` | `character.id` | number | 直接映射 | — |
| `Character.name` | `character.name` | string | 直接映射 | — |
| `Character.type` | `character.type` | `'sage'\|'traveler'` | 直接映射 | `'sage'` |
| `Character.color` | `character.avatar_color` | CSS color string | hex → CSS | `'#4c1d95'` |
| `Character.accentColor` | `character.accent_color` | CSS color string | hex → CSS | `'#7c3aed'` |
| `Character.symbol` | `character.symbol` | string | 直接映射 | `'？'` |
| `Character.title` | `character.title` | string | 直接映射 | `''` |
| `Character.description` | `character.description` | string | 直接映射 | `''` |
| `World.id` | `world.id` | number | 直接映射 | — |
| `World.name` | `world.name` | string | 直接映射 | `'未命名世界'` |
| `World.sceneUrl` | `world.scene_background` | URL string | 直接映射 | Unsplash fallback |
| `World.menuSceneUrl` | `world.menu_scene_background` | URL string | 若无则用 sceneUrl | `sceneUrl` |
| `World.relationship.stage` | `relationship.stage` | RelationshipStage | 直接映射 | `'stranger'` |
| `World.relationship.dimensions` | `relationship.dimensions` | `{trust,familiarity,respect,comfort}` | 小数 0-1 | 全 0 |
| `Course.progress` | `course.mastery_progress` | number 0-1 | 直接映射 | `0` |
| `Course.nextReview` | `course.next_review_at` | ISO 日期字符串 | 格式化为"今天/明天/N天后" | `'—'` |
| `Checkpoint.stage` | `checkpoint.relationship_stage` | RelationshipStage | 直接映射 | `'stranger'` |
| `Checkpoint.sceneKey` | `checkpoint.scene_key` | string | 映射到 SCENE_GRADIENTS | `'default'` |
| `ConversationStep.mode` | `message.type` | DialogMode | `'assistant'→'speaking'`, `'user'→'input'` | `'speaking'` |
| `ConversationStep.expression` | `message.emotion_expression` | Expression | 映射表（见下） | `'default'` |
| `ConversationStep.emotion` | `message.emotion_label` | string | 直接映射 | `'中性'` |
| `ConversationStep.text` | `message.content` | string | 直接映射 | `''` |
| `ConversationStep.choices` | `message.choices` | string[] | 直接映射 | `[]` |
| `ConversationStep.triggerStageEvent` | `message.trigger_stage_event` | boolean | 直接映射 | `false` |
| `ConversationStep.nextStageLabel` | `message.next_stage` | RelationshipStage | 直接映射 | `null` |
| `KnowledgeNode.mastery` | `concept.mastery_score` | number 0-1 | 直接映射 | `0` |
| `KnowledgeNode.bloomLevel` | `concept.bloom_level` | BloomLevel | 直接映射 | `'remember'` |
| `EmotionDataPoint` | `session.emotion_history[i]` | object | 字段名一致 | 空数组 |

### 7.2 表情映射（emotion_expression → Expression）

```javascript
const EMOTION_TO_EXPRESSION = {
  '满足': 'happy',
  '兴奋': 'happy',
  '期待': 'happy',
  '好奇': 'default',
  '中性': 'default',
  '……':  'default',
  '思考': 'thinking',
  '困惑': 'thinking',
  '沮丧': 'concerned',
  '担忧': 'concerned',
}
// 兜底：未匹配 → 'default'
```

### 7.3 缺失字段与兜底策略

| 场景 | 缺失字段 | 兜底行为 |
|---|---|---|
| 后端未返回 `scene_background` | `World.sceneUrl` | 使用 Unsplash 默认图（见资源清单） |
| 后端未返回 `next_review_at` | `Course.nextReview` | 显示"—" |
| 后端未返回 `emotion_label` | `ConversationStep.emotion` | 显示"中性"，灰色指示点 |
| 后端返回空 `choices` 数组 | ���制 mode='speaking' | 不显示选项区域 |
| 后端返回未知 `stage` | RelationshipStage | 降级为 `'stranger'` |
| API 超时（>5s）| 所有请求 | `mode='waiting'` 持续，显示错误 toast |
| 知识图谱无节点 | KNOWLEDGE_GRAPH.nodes=[] | 显示"暂无知识节点"空态提示 |

---

## 8. 资源清单

### 8.1 字体

| 字体名 | 字重 | 用途 | 加载方式 | 授权 |
|---|---|---|---|---|
| Noto Serif SC | 400, 500, 700 | 对话正文 | Google Fonts CDN | OFL 1.1（开源，商用允许） |
| Noto Sans SC | 300, 400, 500, 700 | UI 元素 | Google Fonts CDN | OFL 1.1 |
| JetBrains Mono | 400（正斜）, 500 | 代码/等宽 | Google Fonts CDN | OFL 1.1 |

**import URL**（复制到 Vue 项目 `src/styles/fonts.css`）：
```css
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;700&family=Noto+Sans+SC:wght@300;400;500;700&family=JetBrains+Mono:ital,wght@0,400;0,500;1,400&display=swap');
```

### 8.2 背景图（Unsplash 外链）

| 用途 | URL | 页面 |
|---|---|---|
| 登录页背景 | `https://images.unsplash.com/photo-1663318971958-8e9e1cead755?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&...&w=1080` | LoginPage |
| 档案/设置背景 | `https://images.unsplash.com/photo-1675371708731-50d9c04eb530?w=1920&q=80` | ArchivesPage, SettingsPage |
| 雅典学院场景 | `https://images.unsplash.com/photo-1629639057315-410edca4fa89?w=1920&q=80` | World ID=1 |
| 星际研究院场景 | `https://images.unsplash.com/photo-1736231182175-c3202ce807c0?w=1920&q=80` | World ID=2 |
| 幕府学堂场景 | `https://images.unsplash.com/photo-1709011399070-90601cac77c9?w=1920&q=80` | World ID=3 |

**授权说明**：Unsplash 免费授权（Unsplash License），允许商业使用，不需署名但建议保留。迁移时保持原 URL 不变，或下载后转存到项目 `public/assets/scenes/` 以避免 CDN 依赖。

### 8.3 图标库

- **lucide-react** → Vue 对应：`lucide-vue-next`（`npm install lucide-vue-next`）
- 当前使用图标：`Save, BookOpen, SkipForward, Play, Clock, Settings, Home, Upload, BarChart2, X, ArrowLeft, Eye, EyeOff, Check, Key, Monitor, Info, Send, Plus, Trash2, PenLine, TrendingUp, Calendar`

### 8.4 动画/图表库

| 当前库 | Vue 等价 | 安装 |
|---|---|---|
| `motion/react` | `@vueuse/motion` 或 `@formkit/auto-animate` | `npm install @vueuse/motion` |
| `recharts` | `vue-echarts` + `echarts` 或 `vue-chartjs` | 按选定方案安装 |

> **推荐**：recharts 无 Vue 3 官方版，改用 **vue-chartjs**（Chart.js 封装）；情感折线图和饼图均可实现。

### 8.5 SVG / 插画

当前项目无本地 SVG 文件，所有角色图形由纯 CSS + 字符（symbol）实现。迁移时无需处理图形资产。

---

## 9. 验收标准

### 9.1 逐页验收清单

#### LoginPage

| 检查点 | 要求 | 允许偏差 |
|---|---|---|
| 背景图 | 正确加载暗色图，8% 透明度 | ±2% 透明度 |
| 粒子 | 28粒子，60%金色，浮动动画 | 粒子数 ±2 |
| 面板 | 无圆角，毛玻璃 blur(22px)，金色顶边 | — |
| 标题 | 「知遇」金色，breatheGlow 动画 | — |
| 错误提示 | 红色 #df4a4a，3s 自动消失 | 消失时间 ±500ms |
| 加载态 | 按钮文字变化，禁用点击 | — |
| 空态 | 字段为空，提交按钮可见 | — |

#### MainMenuPage

| 检查点 | 要求 | 允许偏差 |
|---|---|---|
| 背景过渡 | phase 切换时背景图渐变 | — |
| 菜单项 | hover 右移 10px，金色，letter-spacing 7px | ±1px |
| 世界卡片 | hover 上移 4px + scale(1.02)，金色边框 | ±1px |
| 选中卡片 | 金色边框0.8 + glow | — |
| phase 动画 | out-in，旧内容先退出 | — |
| 对话框（course-select）| 毛玻璃，无圆角，名称标签平行四边形 | — |

#### LearningPage

| 检查点 | 要求 | 允许偏差 |
|---|---|---|
| 场景背景 | scale 1.05→1 初始动画，1.5s | ±200ms |
| 对话框毛玻璃 | backdrop-filter blur(20px) saturate(1.5)，**全程不闪烁** | — |
| 对话框动画 | 仅 translateY，无 opacity | — |
| 打字机 | 38ms/字符，游标 bounceDown | ±5ms |
| 角色跳动 | :key 变化触发，0.35s | — |
| 选项飞入 | 每项延迟 0.09s | ±0.01s |
| 等待点 | 5点，每点延迟 0.25s，dotFlash | — |
| 关系升级 | 3个同心圆 goldRipple，中央内容 stageReveal | — |
| HUD | 44px 高，8项按钮，右侧状态区 | — |
| 空态（无消息）| backlog 面板显示"暂无对话记录" | — |
| anyPanelOpen | 角色 brightness(0.4)，对话框隐藏 | — |

#### ArchivesPage

| 检查点 | 要求 | 允许偏差 |
|---|---|---|
| 折线图 | 4条情感线，各色正确 | — |
| 饼图 | 5个情感分区，颜色正确 | — |
| 进度条 | 每个概念准确的掌握度宽度 | ±2% |
| 日记列表 | 按日期降序 | — |
| 写日记弹窗 | panelIn 动画，输入后追加 | — |
| 空态 | 无情感数据时显示"暂无记录" | — |

#### SettingsPage

| 检查点 | 要求 | 允许偏差 |
|---|---|---|
| 保存成功 | 按钮变绿 ✓，2s 后复原 | ±200ms |
| API Key 遮盖 | showKey=false 时显示 ●●●●●● | — |
| Provider 切换 | radio 选项视觉联动 | — |
| 滑块 | 1.0-5.0，步长0.5，实时反馈 | — |

### 9.2 全局验收要求

1. **backdrop-filter 稳定性**：在 Chrome 120+、Safari 17+、Firefox 128+ 中，对话框全程显示毛玻璃效果（不因 Transition 动画闪烁为纯色背景）
2. **字体加载**：Noto Serif SC / Noto Sans SC 加载完成前不得出现明显 FOUT（推荐 `font-display: swap`）
3. **颜色一致性**：所有 `#ffd700` 不得替换为其他黄色；所有 `rgba(5,5,20,...)` 不得改用 oklch
4. **圆角规范**：对话框、输入框、名称标签、选项卡片、发送按钮**严格无圆角**；world-card 12px；hud-btn 5px
5. **动画性能**：所有动画使用 `transform`/`opacity`（GPU 加速），不使用 `width`/`height`/`top` 等触发 layout 的属性（掌握度条宽度变化例外，使用 `transition: width 1s ease`）

---

## 10. 范围边界

### 10.1 本次迁移包含

| 类别 | 说明 |
|---|---|
| ✅ 样式迁移 | 所有 CSS class（galgame-\*、world-card、font-\* 等）、Tailwind 工具类、inline style 转换为 Vue `<style>` + Tailwind |
| ✅ 动效迁移 | 所有 @keyframes、Transition、AnimatePresence → Vue `<Transition>`/`<TransitionGroup>` |
| ✅ 组件结构迁移 | React 组件 → Vue SFC（setup + template），props/emits 1:1 映射 |
| ✅ 路由迁移 | React Router → Vue Router（路由表结构相同）|
| ✅ 状态管理迁移 | useState/useEffect → Pinia store 或 `<script setup>` + `ref/reactive` |
| ✅ 交互行为迁移 | 打字机、跳过、自动模式、jumpKey 机制 |
| ✅ Mock 数据迁移 | mockData.ts → stores/mock.ts（Pinia）|

### 10.2 本次迁移**不包含**

| 类别 | 说明 | 计划阶段 |
|---|---|---|
| ❌ LLM API 接入 | 对话依然使用 PHILOSOPHY_SCRIPT 静态脚本 | Phase 2 |
| ❌ FSRS 调度器 | 无真实间隔复习计算 | Phase 2 |
| ❌ 后端 API 联调 | 数据全部来自 mock | Phase 2 |
| ❌ 用户认证 | 登录表单不联调真实 Auth | Phase 2 |
| ❌ 数据持久化 | Checkpoint 存档不写��数据库 | Phase 2 |
| ❌ 存档截图缩略图 | SaveLoadPanel 缩略图区域为渐变占位 | Phase 3 |
| ❌ Live2D 角色 | 继续使用字符+CSS 立绘 | Phase 3+ |
| ❌ 场景 AI 生成 | 继续使用 Unsplash 固定图 | Phase 3+ |
| ❌ 移动端全适配 | 保证可用但不做像素级优化 | Phase 3 |

### 10.3 判定规则（避免范围漂移）

- **收到"能不能顺便加 XX 功能"** → 记录到 Phase 2 backlog，本次不实施
- **收到"这个样式感觉不对"** → 对照本文档第 2 节数值，数值内允许修改，数值外须 Owner 确认
- **收到"重构这个组件的逻辑"** → 若不影响视觉输出，记录到 Phase 2；若影响视觉（如改变 props 结构），须更新本文档第 6 节后再实施
- **backdrop-filter 闪烁问题** → 属于本次必须修复范围（见第 3.2 节约束）

---

*本文档由代码库完整扫描生成，基准为 React 实现 v12 冻结版本（2026-04-05）。Vue 3 迁移过程中如发现本文档与实际代码存在出入，以当前运行的 React 版本为准，并同步更新本文档。*
