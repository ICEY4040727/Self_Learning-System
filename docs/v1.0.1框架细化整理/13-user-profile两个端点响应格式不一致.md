# 问题 13: User Profile 两个端点响应格式不一致

## ✅ 已解决

**解决方案**: `/me` 端点改为直接返回 User 对象
**PR**: #213 → #220

## 问题类型
API 响应格式不一致 / 逻辑不清

## 涉及文件
- `backend/api/routes/learning.py` 第 432-452 行（`get_user_profile`）
- `backend/api/routes/learning.py` 第 455-474 行（`refresh_user_profile`）
- `frontend/src/api/client.ts` 第 39-53 行（`userProfileApi`）

## 具体描述

**`GET /user/profile`（获取画像）：**
```python
# 直接返回 profile，不包装
return profile
```

**`POST /user/profile/refresh`（刷新画像）：**
```python
# 包装在 { success, data } 中
return {
    "success": True,
    "data": user_profile.profile,
    "computed_at": user_profile.computed_at.isoformat() if user_profile.computed_at else None
}
```

**前端 `client.ts` 中的妥协处理：**
```typescript
get: async (): Promise<UserProfile> => {
    const { data } = await client.get('/user/profile')
    // 后端直接返回 profile，不包装 { success, data }
    return data
},

refresh: async (force = false): Promise<UserProfile> => {
    const { data } = await client.post('/user/profile/refresh', { force })
    // refresh 端点仍返回 { success, data } 格式
    return data.data ?? data  // ← 需要用 ?? 来兼容两种格式
}
```

## 影响分析

1. **API 一致性差**：同一资源的两个端点返回不同格式，增加前端处理复杂度
2. **`data.data ?? data` 的防御性代码**：说明前端开发者已经意识到格式不一致，用 `??` 做了兼容
3. **`refresh` 返回 `user_profile.profile`，`get` 返回完整的 `profile` 对象**：返回的数据层级可能也不同

## 建议修复方向

1. 统一两个端点的响应格式：要么都直接返回 profile，要么都包装在 `{ success, data }` 中
2. 推荐方案：都直接返回 profile 对象（与 `GET /user/profile` 一致），删除 `refresh` 中的 `success` 包装
3. 简化前端的 `refresh` 方法为 `return data`