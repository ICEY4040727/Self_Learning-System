# 问题 08: 前端关系阶段标签在 `types/index.ts` 和 `constants/courseLevels.ts` 中重复定义

## ✅ 已解决

**解决方案**: 删除 `types/index.ts` 中的 `STAGE_LABELS`，仅保留 `constants/courseLevels.ts` 中的 `RELATIONSHIP_STAGE_LABELS`
**PR**: #213 → #220

## 问题类型
重复定义（前端）

## 涉及文件
- `frontend/src/types/index.ts` — `STAGE_LABELS` 常量
- `frontend/src/constants/courseLevels.ts` — `RELATIONSHIP_STAGE_LABELS` 常量

## 重复内容

**`types/index.ts`:**
```typescript
export const STAGE_LABELS: Record<RelationshipStage, string> = {
  stranger:     '陌生人',
  acquaintance: '相识',
  friend:       '朋友',
  mentor:       '导师',
  partner:      '伙伴',
}
```

**`constants/courseLevels.ts`:**
```typescript
export const RELATIONSHIP_STAGE_LABELS: Record<string, string> = {
  stranger: '陌生人',
  acquaintance: '相识',
  friend: '朋友',
  mentor: '导师',
  partner: '伙伴',
}
```

两个常量内容完全一致，仅命名不同（`STAGE_LABELS` vs `RELATIONSHIP_STAGE_LABELS`）。

此外，后端 `save.py` 和 `archive.py` 也各自定义了 `stage_map`（见问题 01），**同样的映射关系在前后端共出现 4 次**。

## 影响分析

1. **跨文件一致性问题**：如果新增关系阶段，前端至少需要修改 2 处
2. **命名不一致增加困惑**：`STAGE_LABELS` vs `RELATIONSHIP_STAGE_LABELS`，使用者不知道该引用哪个
3. **类型安全性差异**：`STAGE_LABELS` 使用了 `Record<RelationshipStage, string>` 有类型约束，而 `RELATIONSHIP_STAGE_LABELS` 使用了 `Record<string, string>` 没有类型约束

## 建议修复方向

1. 保留 `types/index.ts` 中的 `STAGE_LABELS`（有类型约束，更好），删除 `constants/courseLevels.ts` 中的 `RELATIONSHIP_STAGE_LABELS`
2. 全局搜索替换引用 `RELATIONSHIP_STAGE_LABELS` 的地方改为 `STAGE_LABELS`
3. `RELATIONSHIP_STAGE_ICONS` 可以保留在 `courseLevels.ts` 中，或者也迁移到 `types/index.ts`