# 前后端对齐修复计划

> **生成时间**: 2026-04-06  
> **最后更新**: 2026-04-08  
> **目的**: 整理前后端不一致问题，明确修复优先级和步骤

---

## 一、仍需修复的问题

### P0 问题（阻断联调）

| # | 问题 | 位置 | 修复方式 |
|---|------|------|----------|
| 1 | WorldDetail.vue checkpoint API 路径错误 | `frontend/src/views/WorldDetail.vue:178` | ✅ 已修复 |

### 已修复问题（无需操作）

| # | 问题 | 说明 |
|---|------|------|
| 2 | UserProfile.refresh 响应处理 | `client.ts:48-52` 已处理 `data.data ?? data` |
| 3 | Checkpoint 类型定义不完整 | `types/index.ts:82-89` 已包含完整字段 |
| 4 | createCheckpoint world_id 验证 | `stores/learning.ts` 已正确传递 |
| 5 | Character.avatar 字段名不一致 | `Character.vue` 已做兼容 `avatar: c.avatar \|\| c.avatar_url` |

---

## 二、问题详情及修复方式

### 2.1 WorldDetail.vue checkpoint API 路径错误

**问题描述**：
- 当前代码调用 `/courses/${courseId}/checkpoints`，但后端不存在此接口
- 后端实际提供 `/save?subject_id=${courseId}` 接口，可按 course 过滤 checkpoint

**为什么需要修复**：
- 调用错误路径会导致存档列表为空，用户无法选择存档
- 后端 `/save` 接口支持按 `subject_id`（即 course_id）过滤

**修复位置**：`frontend/src/views/WorldDetail.vue:175-189`

```typescript
// 当前错误代码
const fetchCheckpoints = async (courseId: number) => {
  checkpointsLoading.value = true
  try {
    const { data } = await client.get(`/courses/${courseId}/checkpoints`)  // ❌ 不存在
    checkpoints.value = data
  } catch {
    checkpoints.value = []
  } finally {
    checkpointsLoading.value = false
  }
}

// 修复后 - 使用后端存在的 /save 接口
const fetchCheckpoints = async (courseId: number) => {
  checkpointsLoading.value = true
  try {
    const { data } = await client.get('/save', { params: { subject_id: courseId } })  // ✅ 正确
    checkpoints.value = data
  } catch {
    checkpoints.value = []
  } finally {
    checkpointsLoading.value = false
  }
}
```

---

## 三、后端有但前端未调用的 API（P2 可选增强）

这些是后端已实现但前端未使用的功能：

| API | 后端 | 前端 API 定义 | 调用状态 |
|-----|------|---------------|----------|
| `/character/{id}/avatar` | ✅ | `characterApi.uploadAvatar()` | ❌ 未调用 |
| `/character/stats` | ✅ | `characterApi.getStats()` | ❌ 未调用 |
| `/character/{id}/levelup` | ✅ | `characterApi.levelup()` | ❌ 未调用 |
| `/progress/due` | ✅ | ❌ 未定义 | - |
| `/persona/generate` | ✅ | ❌ 未定义 | - |
| `/progress/{id}/review` | ✅ | ❌ 未定义 | - |
| `/sessions/{id}/end` | ✅ | ❌ 未定义 | - |

---

## 四、修复清单

### P0 立即修复

- [x] 1. 修复 `WorldDetail.vue` 的 checkpoint API 路径改为 `/save?subject_id=${courseId}`

### P2 可选增强（根据业务需求决定）

- [ ] 实现 Character Avatar 上传
- [ ] 实现 Character Stats 展示
- [ ] 实现 Character Level Up 系统
- [ ] 实现 Persona 生成 UI
- [ ] 实现 Progress Review 交互
- [ ] 实现 Session End 调用

---

## 五、验证清单

修复完成后，验证以下功能正常工作：

- [ ] 选择世界 → 选择课程 → 查看存档列表
- [ ] 加载存档（读档）

---

## 六、更新日志

| 日期 | 更新内容 |
|------|----------|
| 2026-04-06 | 初始创建 |
| 2026-04-08 | 确认 UserProfile.refresh 已自动修复；更新 checkpoint 修复方案为使用 /save 接口 |
