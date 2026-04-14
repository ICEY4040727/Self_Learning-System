# 问题 16: `buildTraitsPayload` 是无意义的恒等包装函数

## 问题类型
冗余函数 / 逻辑不清

## 涉及文件
- `frontend/src/constants/personaTemplates.ts` 第 86-88 行

## 具体描述

```typescript
export function buildTraitsPayload(sliders: Record<string, number>): Record<string, number> {
  return { ...sliders }
}
```

这个函数仅做了浅拷贝（`{ ...sliders }`），输入输出类型完全一致，没有任何数据转换、过滤或增强逻辑。函数名 `buildTraitsPayload` 暗示有"构建"过程，但实际是恒等操作。

## 影响分析

1. **误导性**：读者会以为函数内部有特殊处理逻辑
2. **不必要的抽象**：增加了调用链深度但没有带来任何价值
3. **维护浪费**：每次阅读代码都需要确认函数是否真的什么都不做

## 建议修复方向

1. 删除 `buildTraitsPayload` 函数
2. 在调用处直接使用 `{ ...sliders }` 或直接传递 `sliders`