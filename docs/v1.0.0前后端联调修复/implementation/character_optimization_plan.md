# 角色管理功能优化实现计划

> **最后更新**: 2026-04-08  
> **依据**: 2026-04-08 前后端代码全面调研

## Overview

优化角色管理的创建、编辑、删除流程，让前端使用统一的 `characterApi`，集成头像上传、角色等级等后端已实现但前端未调用的功能。

当前系统存在：
1. Character.vue 直接使用 `client` 而非 `characterApi`
2. 头像上传、角色升级等后端 API 前端未调用
3. 角色统计未展示

---

## 一、当前状态

### 1.1 后端 API（已完整实现）

| API | 路由 | 状态 |
|-----|------|------|
| 角色列表 | GET /character | ✅ |
| 创建角色 | POST /character | ✅ (自动创建 TeacherPersona) |
| 更新角色 | PUT /character/{id} | ✅ |
| 删除角色 | DELETE /character/{id} | ✅ |
| 头像上传 | POST /character/{id}/avatar | ✅ |
| 立绘上传 | POST /characters/{id}/sprites | ✅ |
| 角色升级 | POST /character/{id}/levelup | ✅ |
| 角色统计 | GET /character/stats | ✅ |
| 模板列表 | GET /character/templates | ❌ **未实现** |

### 1.2 前端 API（character.ts）

| 方法 | 状态 | 实际使用 |
|------|------|----------|
| list | ✅ 已定义 | ❌ 未使用 |
| create | ✅ 已定义 | ❌ 未使用 |
| get | ✅ 已定义 | ❌ 未使用 |
| update | ✅ 已定义 | ❌ 未使用 |
| delete | ✅ 已定义 | ❌ 未使用 |
| uploadAvatar | ✅ 已定义 | ❌ 未使用 |
| getStats | ✅ 已定义 | ❌ 未使用 |
| levelup | ✅ 已定义 | ❌ 未使用 |

### 1.3 前端组件

| 组件 | 状态 | 说明 |
|------|------|------|
| CharacterCard.vue | ✅ | 显示角色卡片 |
| StepCreateModal.vue | ✅ | 分步创建 |
| EditCharacterModal.vue | ✅ | 编辑角色 |

### 1.4 问题汇总

| # | 问题 | 类型 | 影响 |
|---|------|------|------|
| 1 | Character.vue 直接使用 client | P0 | 代码不一致，缺少统一 API 层 |
| 2 | 字段不一致 (description vs background) | P0 | 创建角色时数据丢失 |
| 3 | 头像上传功能未集成 | P1 | 用户无法上传头像 |
| 4 | 角色等级系统未展示 | P1 | 游戏化体验缺失 |
| 5 | 角色统计未展示 | P2 | 数据可视化缺失 |
| 6 | /character/templates 未实现 | P2 | 模板列表硬编码 |

---

## 二、Implementation Plan

### Phase 1: 统一 API 层 (P0)

#### 2.1 修改 Character.vue 使用 characterApi

**文件**: `frontend/src/views/Character.vue`

```typescript
// 移除直接 import client
// import client from '@/api/client'

// 改为 import characterApi
import { characterApi } from '@/api/character'

// 修改 fetchCharacters
const fetchCharacters = async () => {
  loading.value = true
  try {
    const data = await characterApi.list()
    characters.value = data.map((c: any) => ({
      ...c,
      avatar: c.avatar || c.avatar_url
    }))
    if (characters.value.length === 0) {
      characters.value = MOCK_CHARACTERS
    }
  } catch {
    characters.value = MOCK_CHARACTERS
  } finally {
    loading.value = false
  }
}

// 修改 handleCreate
const handleCreate = async (data: CharacterFormData) => {
  try {
    const newChar = await characterApi.create({
      name: data.name,
      type: data.type,
      template_name: data.template_name,
      avatar: data.avatar,
      personality: data.personality,
      background: data.background,
      speech_style: data.speech_style,
      tags: data.tags,
      title: data.title,
    })
    characters.value.push({
      ...newChar,
      avatar: newChar.avatar || newChar.avatar_url
    })
  } catch {
    // mock mode fallback
  }
  showModal.value = false
}

// 修改 handleUpdate
const handleUpdate = async (data: CharacterFormData) => {
  if (!editingCharacter.value) return
  try {
    const updated = await characterApi.update(editingCharacter.value.id, {
      name: data.name,
      type: data.type,
      avatar: data.avatar,
      personality: data.personality,
      background: data.background,
      speech_style: data.speech_style,
      tags: data.tags,
      title: data.title,
    })
    const idx = characters.value.findIndex(c => c.id === editingCharacter.value!.id)
    if (idx !== -1) {
      characters.value[idx] = { ...characters.value[idx], ...updated }
    }
  } catch {
    // mock mode fallback
  }
  showEditModal.value = false
}

// 修改 handleDelete
const handleDelete = async () => {
  if (!deleteTarget.value) return
  try {
    await characterApi.delete(deleteTarget.value.id)
    characters.value = characters.value.filter(c => c.id !== deleteTarget.value!.id)
  } catch {
    // mock mode fallback
  }
  showDeleteConfirm.value = false
  deleteTarget.value = null
}
```

---

### Phase 2: 头像上传集成 (P1)

#### 2.2 修改 CharacterCard.vue 添加头像上传

**文件**: `frontend/src/components/CharacterCard.vue`

```typescript
// 添加上传逻辑
import { characterApi } from '@/api/character'

const emit = defineEmits<{
  click: []
  edit: []
  delete: []
  uploadAvatar: [characterId: number]
}>()

// 在模板中添加上传按钮（hover 时显示）
// <button @click.stop="handleUpload" class="action-btn upload-btn">
```

**文件**: `frontend/src/components/EditCharacterModal.vue`

添加头像上传功能：
```typescript
const handleAvatarUpload = async (file: File) => {
  if (!editingCharacter.value) return
  try {
    const result = await characterApi.uploadAvatar(editingCharacter.value.id, file)
    editingCharacter.value.avatar = result.avatar
    emit('update', { ...props.character, avatar: result.avatar })
  } catch (error) {
    console.error('上传失败:', error)
  }
}
```

---

### Phase 3: 角色等级系统 (P1)

#### 2.3 修改 Character.vue 添加等级展示

**文件**: `frontend/src/views/Character.vue`

```typescript
// 在 Character interface 添加等级字段
interface Character {
  id: number
  name: string
  title?: string
  avatar?: string
  type: 'sage' | 'traveler'
  is_builtin: boolean
  color?: string
  tags?: string[]
  personality?: string
  level?: number           // 新增
  experience_points?: number  // 新增
}

// 修改 CharacterCard 显示等级
// 在 char-card 模板中添加等级徽章
```

#### 2.4 修改 CharacterCard.vue 显示等级

**文件**: `frontend/src/components/CharacterCard.vue`

```typescript
// 添加等级显示
const levelDisplay = computed(() => {
  const level = props.level || 1
  const exp = props.experience_points || 0
  return `Lv.${level} (${exp} exp)`
})

// 在模板中添加
// <div class="char-level">{{ levelDisplay }}</div>
```

---

### Phase 4: 角色统计展示 (P2)

#### 2.5 添加统计面板

**文件**: `frontend/src/views/Character.vue`

```typescript
// 添加统计数据
const stats = ref({
  total_characters: 0,
  sage_count: 0,
  traveler_count: 0,
  active_worlds: 0
})

const fetchStats = async () => {
  try {
    stats.value = await characterApi.getStats()
  } catch {
    // ignore
  }
}

// 在 onMounted 中调用
onMounted(async () => {
  await Promise.all([fetchCharacters(), fetchStats()])
})

// 在模板中添加统计面板
```

---

### Phase 5: 模板列表 API (P2)

#### 2.6 后端添加 /character/templates

**文件**: `backend/api/routes/archive.py`

```python
@router.get("/character/templates")
def get_character_templates():
    """返回可用的角色模板列表"""
    return [
        {"name": "苏格拉底型", "desc": "擅长通过反问引导思考", "traits": ["耐心", "追问型", "启发型"]},
        {"name": "爱因斯坦型", "desc": "鼓励大胆假设和实验", "traits": ["鼓励型", "探索型", "启发型"]},
        {"name": "亚里士多德型", "desc": "百科全书式讲解", "traits": ["严谨", "体系化", "百科全书"]},
        {"name": "孙子型", "desc": "策略性思考", "traits": ["策略性", "举一反三", "引导型"]},
        {"name": "默认", "desc": "通用模板", "traits": ["耐心", "启发型"]},
    ]
```

#### 2.7 前端添加 getTemplates API

**文件**: `frontend/src/api/character.ts`

```typescript
/**
 * 获取角色模板列表
 */
getTemplates: (): Promise<{
  name: string
  desc: string
  traits: string[]
}[]> =>
  client.get('/character/templates').then(res => res.data),
```

---

## 三、Files Summary

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/views/Character.vue` | 修改 | 使用 characterApi |
| `frontend/src/components/CharacterCard.vue` | 修改 | 添加等级显示、上传按钮 |
| `frontend/src/components/EditCharacterModal.vue` | 修改 | 集成头像上传 |
| `frontend/src/api/character.ts` | 修改 | 添加 getTemplates |
| `backend/api/routes/archive.py` | 修改 | 添加 /character/templates |

---

## 四、Implementation Order

1. **Phase 1**: 修改 Character.vue 使用 characterApi（基础，统一 API 层）
2. **Phase 2**: 头像上传集成（用户核心功能）
3. **Phase 3**: 角色等级展示（游戏化体验）
4. **Phase 4**: 角色统计展示（数据可视化）
5. **Phase 5**: 模板列表 API（可选，消除硬编码）

---

## 五、Testing Checklist

- [ ] 创建 sage 角色 → 自动创建 TeacherPersona
- [ ] 创建 traveler 角色 → 不创建 TeacherPersona
- [ ] 上传头像 → 头像正确显示
- [ ] 角色等级 → 显示 Lv. 和经验值
- [ ] 角色统计 → 显示 sage/traveler 数量
- [ ] 模板列表 → 从 API 获取而非硬编码
