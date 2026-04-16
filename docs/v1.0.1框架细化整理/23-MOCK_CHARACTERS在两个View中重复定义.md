# 问题 23: `MOCK_CHARACTERS` 在 WorldDetail.vue 和 Character.vue 中重复定义且数据不同步

## ⚠️ 未解决

**说明**: 两处仍各自定义 MOCK_CHARACTERS

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

### 方案 A：删除 mock 数据（推荐）

如果后端 API 已完善，直接删除 mock 数据和 fallback 逻辑：

```typescript
// 删除前
const characters = ref<Character[]>([])
onMounted(async () => {
  characters.value = await api.getCharacters() || MOCK_CHARACTERS  // ❌ fallback 到假数据
})

// 改为
const characters = ref<Character[]>([])
const hasError = ref(false)
onMounted(async () => {
  try {
    characters.value = await api.getCharacters()
    if (!characters.value.length) hasError.value = true
  } catch (e) {
    hasError.value = true
  }
})
```

### 方案 B：统一到 constants（保留 fallback）

1. 创建 `frontend/src/constants/mockCharacters.ts`：
```typescript
export const MOCK_CHARACTERS: Character[] = [
  { id: 10, name: '苏格拉底', title: '哲学之父', type: 'sage', color: 'rgba(245, 158, 11, 0.35)' },
  { id: 11, name: '柏拉图', title: '理念论者', type: 'sage', color: 'rgba(139, 92, 246, 0.35)' },
  // ...
]

// 导出统一的类型定义
export interface MockCharacter {
  id: number
  name: string
  title: string
  type: 'sage' | 'traveler'
  color: string
  is_builtin?: boolean
}
```

2. 两处 View 统一引用：
```typescript
import { MOCK_CHARACTERS } from '@/constants/mockCharacters'
```

3. fallback 时显示提示：
```vue
<div v-if="isOfflineMode" class="offline-notice">
  ⚠️ 离线模式，显示示例数据
</div>
```

## 修复完成要求

### PR 提交检查清单

- [ ] 删除两处重复的 `MOCK_CHARACTERS` 定义
- [ ] 统一引用来源（方案 A 或 B）
- [ ] API 失败时正确处理（显示错误而非静默 fallback）
- [ ] **提供前端样式截图**（修复后的页面截图）
- [ ] 更新相关常量导出文件（如有）

### 截图要求

修复完成后在 PR 中提供：
1. WorldDetail 页面正常显示截图
2. Character 页面正常显示截图
3. API 错误情况下的提示截图（如果采用方案 A）
