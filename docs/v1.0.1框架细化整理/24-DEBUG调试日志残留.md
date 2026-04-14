# 问题 24: `[DEBUG]` 调试日志残留

## 问题类型
调试残留（前端）

## 涉及文件
- `frontend/src/views/WorldDetail.vue`（4 处）
- `frontend/src/views/Worlds.vue`（4 处）
- `frontend/src/views/Character.vue`（1 处）

## 具体内容

**WorldDetail.vue：**
```typescript
console.log('[DEBUG] fetchCharacters API result:', data)
console.log('[DEBUG] allCharacters after fetch:', allCharacters.value.length)
console.error('[DEBUG] fetchCharacters error:', error)
console.log('Edit sage:', sage)   // handleEditSage — TODO 占位
console.log('Edit traveler:', traveler)  // handleEditTraveler — TODO 占位
```

**Worlds.vue：**
```typescript
console.log('[DEBUG] fetchWorlds called')
console.log('[DEBUG] calling client.get("worlds")')
console.log('[DEBUG] response data:', data)
console.error('[DEBUG] fetchWorlds error:', error)
```

**Character.vue：**
```typescript
console.log('Card clicked:', character)
```

## 影响分析

1. **浏览器控制台噪音**：正常操作时控制台输出大量调试信息
2. **性能影响（极小）**：生产环境中不必要的字符串序列化
3. **信息泄露**：API 响应数据结构暴露在控制台中

## 建议修复方向

删除所有 `[DEBUG]` 标记的 `console.log` 调用。对于错误处理中的 `console.error`，保留但去掉 `[DEBUG]` 前缀。