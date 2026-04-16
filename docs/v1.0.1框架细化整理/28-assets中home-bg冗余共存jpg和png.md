# 问题 28: `assets` 中 `home-bg.jpg` 和 `home-bg.png` 冗余共存

## ⚠️ 未解决

**说明**: 两版本背景图冗余共存

## 问题类型
冗余资源文件

## 涉及文件
- `frontend/src/assets/home-bg.jpg`（冗余）
- `frontend/src/assets/home-bg.png`（实际使用）

## 具体内容

```
frontend/src/assets/
  home-bg.jpg    ← 冗余
  home-bg.png    ← 实际被引用
```

代码中引用的是 `home-bg.png`（在 Home.vue 或相关视图中 import），`.jpg` 版本无任何引用。

## 影响分析

1. **包体积浪费**：未使用的图片增加构建产物大小
2. **开发者困惑**：看到两个同名不同格式文件，不确定该使用哪个
3. **维护冗余**：更新背景图时可能误改错误文件

## 建议修复方向

1. 确认 `home-bg.jpg` 无任何引用后删除
2. 建议在 `.gitignore` 或构建流程中加入对未使用资源的检查