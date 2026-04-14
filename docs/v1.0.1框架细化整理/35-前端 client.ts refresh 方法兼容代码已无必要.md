#35: 前端 client.ts refresh 方法兼容代码已无必要

### 问题描述
#213 修复后，`POST /user/profile/refresh` 已直接返回 profile dict，不再包装 `{ success, data }`。但 `frontend/src/api/client.ts` 中 `refresh` 方法仍保留 `data.data ?? data` 兼容逻辑。

### 来源
#213 修复后端响应格式，未同步清理前端兼容代码。

### 严重程度
低

### 建议修复
将 `return data.data ?? data` 简化为 `return data`。
