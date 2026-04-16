# 问题 25: `page-fade` 过渡样式在两处 CSS 重复定义且值冲突

## ⚠️ 未解决

**说明**: 过渡样式仍分散在 main.css 中

## 问题类型
样式重复定义 / 值冲突

## 涉及文件
- `frontend/src/styles/galgame.css`（enter: 0.4s, leave: **0.4s**，时间戳：04-15 12:18）
- `frontend/src/assets/main.css`（enter: 0.4s, leave: **0.3s**）

## 重复内容

**galgame.css：**
```css
.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
}
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.4s ease;
}
```

**main.css：**
```css
.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
}
.page-fade-enter-active {
  transition: opacity 0.4s ease;
}
.page-fade-leave-active {
  transition: opacity 0.3s ease;  /* ← 与 galgame.css 的 0.4s 不一致 */
}
```

## ⚠️ 惯性偏好提醒

**不要假设 galgame.css 是最新版**。根据时间戳：
- `galgame.css`（04-15 12:18）比 `theme.css`（04-09 17:46）**更新 6 天**
- galgame.css 是最新样式，但建议统一为一套样式文件

## 影响分析

1. **最终生效值取决于 CSS 加载顺序**：`galgame.css` 和 `main.css` 都被引入，后者覆盖前者
2. **维护困惑**：修改过渡时间时不知道该改哪个文件
3. **leave 动画不一致**：0.3s vs 0.4s，可能导致页面切换体验微妙不同

## 建议修复方向

1. **统一保留位置**：建议统一使用 `theme.css`（最新样式基准）
2. 删除 `main.css` 和 `galgame.css` 中的 `page-fade` 定义
3. 在 `theme.css` 中统一 enter/leave 时间为相同值（推荐 0.3s）
