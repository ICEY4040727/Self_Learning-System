# 问题 30: `types/index.ts` 混合了类型定义和 UI 常量（460 行巨型文件）

## ⚠️ 未解决

**说明**: types/index.ts 仍存在

## 问题类型
文件职责不清 / 单文件过大

## 涉及文件
- `frontend/src/types/index.ts`（460 行）

## 具体分析

该文件同时包含以下完全不同性质的内容：

| 行范围 | 内容 | 应归属 |
|--------|------|--------|
| 1-15 | 类型别名（`CharacterType`, `Expression` 等） | ✅ types |
| 17-246 | 接口定义（`User`, `Character`, `World` 等） | ✅ types |
| 253-255 | 常量（`ALLOWED_SPRITE_STEMS`, `MAX_SPRITE_SIZE_BYTES`） | ❌ constants |
| 293-319 | UI 映射常量（`MSKT_LABELS`, `PREFERENCE_LABELS`, 颜色配置） | ❌ constants |
| 323-379 | UI 显示常量（`STAGE_LABELS`, `EMOTION_COLORS`, `EXPRESSION_SYMBOLS`） | ❌ constants |
| 386-460 | Report 接口 + 更多常量（`MILESTONE_TYPE_ICONS`） | 混合 |

共约 **170 行常量代码**混入了类型定义文件中。

## 影响分析

1. **导入污染**：只需要类型的组件被迫导入常量，只需要常量的组件被迫导入类型
2. **Tree-shaking 效率降低**：常量和类型耦合在同一模块
3. **认知负担**：460 行文件难以快速定位目标定义
4. **违反单一职责**：类型定义和 UI 常量的变更原因不同

## 建议修复方向

1. 将 UI 常量提取到 `constants/uiConstants.ts` 或拆分到现有常量文件中
2. `types/index.ts` 只保留纯类型定义（interface、type）
3. 数值常量（如 `MAX_SPRITE_SIZE_BYTES`）归入相关常量文件