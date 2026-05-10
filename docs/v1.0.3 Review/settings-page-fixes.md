# v1.0.3 Settings 页面问题修复计划

> 审查时间：2026-05-02
> 状态：待实施

## 问题清单

### P0 — 影响功能正确性

#### 1. autoModeDelay 单位混乱
- **文件**: `frontend/src/stores/settings.ts` (L44), `frontend/src/views/Settings.vue` (L168), `frontend/src/views/Learning.vue` (L273)
- **现象**: Store 默认值 `2.8`（秒），Settings 滑块范围 `1000-5000`（毫秒），Learning.vue 使用时乘以 1000
- **后果**: 用户第一次拖动滑块后（比如设为 3000），实际延迟变成 `3000 * 1000 = 3,000,000ms`（约 50 分钟）
- **修复方案**: 
  - Store 默认值改为 `2800`（毫秒），与滑块单位一致
  - Learning.vue 中去掉 `* 1000`，直接使用毫秒值
  - Settings.vue 滑块显示改为 `{{ settings.autoModeDelay / 1000 }}s`

### P1 — 误导用户

#### 2. Temperature / Max Tokens 是摆设
- **文件**: `frontend/src/views/Settings.vue` (L116-148), `frontend/src/stores/settings.ts` (L45-46)
- **现象**: 这两个值只存到 localStorage，后端 `SettingsUpdate` 模型不支持，LLM 调用从不读取
- **后果**: 用户以为调了有用，实际完全无效
- **修复方案**（二选一）:
  - **方案 A（推荐）**: 打通后端 — 后端新增 `temperature`/`max_tokens` 字段，LLM adapter 读取用户配置
  - **方案 B**: 移除这两个设置项，避免误导

#### 3. 无法清除 API Key
- **文件**: `frontend/src/views/Settings.vue`, `backend/api/routes/archive.py` (L1538-1553)
- **现象**: 没有删除按钮，留空输入框不会清除已有 Key（后端只在 `api_key` 非空时更新）
- **修复方案**: 
  - 前端：添加"清除 Key"按钮
  - 后端：支持 `api_key: ""` 时清除 `encrypted_api_key`

### P2 — 体验改进

#### 4. 没有连接测试
- **现象**: 保存 API Key 后无法验证是否有效
- **修复方案**: 后端新增 `/api/settings/test-key` 端点，前端保存后自动调用并显示结果

#### 5. 没有模型选择
- **现象**: 只能选 Provider，不能选具体模型
- **修复方案**: 后端返回每个 Provider 支持的模型列表，前端根据 Provider 动态显示模型下拉框

---

## 实施步骤

### Step 1: 修复 autoModeDelay 单位（P0）
- [ ] `stores/settings.ts`: 默认值 `2.8` → `2800`
- [ ] `views/Learning.vue`: `settings.autoModeDelay * 1000` → `settings.autoModeDelay`
- [ ] `views/Settings.vue`: 显示 `{{ (settings.autoModeDelay / 1000).toFixed(1) }}s`

### Step 2: 打通 Temperature / Max Tokens（P1）
- [ ] `backend/api/routes/archive.py`: `SettingsUpdate` 新增 `temperature`/`max_tokens` 字段
- [ ] `backend/models/models.py`: User 模型新增 `temperature`/`max_tokens` 列
- [ ] `backend/api/routes/archive.py`: `SettingsResponse` 返回这两个值
- [ ] `backend/api/routes/archive.py`: `update_settings` 保存到数据库
- [ ] `backend/api/routes/learning.py`: chat 端点读取用户配置传给 LLM
- [ ] `backend/services/llm/adapter.py`: 支持 temperature/max_tokens 参数
- [ ] `frontend/src/stores/settings.ts`: `fetchSettings` 读取，`saveSettings` 发送
- [ ] `frontend/src/views/Settings.vue`: 绑定已打通

### Step 3: 支持清除 API Key（P1）
- [ ] `backend/api/routes/archive.py`: `update_settings` 支持 `api_key === ""` 时清除
- [ ] `frontend/src/views/Settings.vue`: 添加"清除 Key"按钮 + 确认对话框

### Step 4: 连接测试（P2，可选）
- [ ] 后端新增 `/api/settings/test-key` 端点
- [ ] 前端保存后自动测试并显示结果

### Step 5: 模型选择（P2，可选）
- [ ] 后端新增 `/api/settings/models?provider=xxx` 端点
- [ ] 前端根据 Provider 动态显示模型下拉框

---

## 影响范围

| 文件 | 改动类型 |
|------|----------|
| `frontend/src/stores/settings.ts` | 修改 |
| `frontend/src/views/Settings.vue` | 修改 |
| `frontend/src/views/Learning.vue` | 修改 |
| `backend/api/routes/archive.py` | 修改 |
| `backend/api/routes/learning.py` | 修改 |
| `backend/models/models.py` | 修改 |
| `backend/services/llm/adapter.py` | 修改 |
| `backend/alembic/versions/` | 新增迁移 |