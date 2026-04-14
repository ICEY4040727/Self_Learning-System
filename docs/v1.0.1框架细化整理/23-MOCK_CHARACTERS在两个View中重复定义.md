# 问题 23: `MOCK_CHARACTERS` 在 WorldDetail.vue 和 Character.vue 中重复定义且数据不同步

## 问题类型
重复定义（前端） / Mock 数据残留

## 涉及文件
- `frontend/src/views/WorldDetail.vue` 第 343-350 行
- `frontend/src/views/Character.vue`（类似位置）

## 重复内容

**WorldDetail.vue：**
```typescript
const MOCK_CHARACTERS: Character[] = [
  { id: 10, name: '苏格拉底', title: '哲学之父', type: 'sage', color: 'rgba(245, 158, 11, 0.35)' },
  { id: 11, name: '柏拉图', title: '理念论者', type: 'sage', color: 'rgba(139, 92, 246, 0.35)' },
  { id: 12, name: '亚里士多德', title: '百科全书', type: 'sage', color: 'rgba(16, 185, 129, 0.35)' },
  { id: 13, name: '孙子', title: '兵圣', type: 'sage', color: 'rgba(220, 38, 38, 0.35)' },
  { id: 110, name: '旅者', title: '求知者', type: 'traveler', color: 'rgba(59, 130, 246, 0.35)' },
  { id: 111, name: '行者', title: '探索者', type: 'traveler', color: 'rgba(6, 182, 212, 0.35)' },
]
```

**Character.vue：**
```typescript
const MOCK_CHARACTERS: Character[] = [
  { id: 1, name: '苏格拉底', title: '哲学之父', type: 'sage', is_builtin: true, color: COLORS[0] },
  // ... 数据结构与 WorldDetail 不同（id 不同、字段不同）
]
```

## 问题细节

1. **ID 不同步**：WorldDetail 用 id 10-13（匹配数据库 user_id=2），Character 用 id 1-4
2. **字段结构不同**：Character 多了 `is_builtin` 字段，WorldDetail 没有
3. **颜色取值方式不同**：WorldDetail 硬编码 rgba，Character 引用 `COLORS` 常量
4. **两处都作为 API 失败的 fallback**：如果 API 返回空数组，用户看到的是假数据而非错误提示

## 影响分析

1. **维护负担**：新增角色时需同步修改两处 mock 数据
2. **掩盖真实错误**：API 失败时静默降级到 mock 数据，用户不知道数据是假的
3. **数据不一致**：两个页面可能展示不同的角色 ID 和属性

## 建议修复方向

1. 如果 mock 数据不再需要（后端已完善），删除两处 `MOCK_CHARACTERS` 及 fallback 逻辑，改为显示"暂无数据"或错误提示
2. 如果仍需 fallback，提取到 `constants/mockCharacters.ts` 统一管理
3. 在 fallback 时至少显示一个提示（如"离线模式，显示示例数据"）