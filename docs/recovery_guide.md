# 文件恢复指南

> 基于 commit `bcd5811` (2026-04-08 15:50)

## 可恢复文件分类

### 1. 样式和资源文件 ✅ 已恢复

| 文件 | 大小 | 状态 | 说明 |
|------|------|------|------|
| `frontend/src/assets/char-bg.jpg` | 296KB | ✅ 已恢复 | 角色页背景图 |
| `frontend/src/assets/home-bg.jpg` | 786KB | ✅ 已恢复 | 首页背景图 |
| `frontend/src/assets/home-bg.png` | 2.5MB | ✅ 已恢复 | 首页背景图 |
| `frontend/src/assets/login-bg.jpg` | 255KB | ✅ 已恢复 | 登录页背景图 |
| `frontend/src/assets/main.css` | 9.7KB | ✅ 已恢复 | 主样式文件 |
| `frontend/src/styles/fonts.css` | 191B | ✅ 已恢复 | 字体样式 |
| `frontend/src/styles/galgame.css` | 10KB | ✅ 已恢复 | Galgame 样式 |
| `frontend/src/styles/index.css` | 96B | ✅ 已恢复 | 入口样式 |
| `frontend/src/styles/tailwind.css` | 135B | ✅ 已恢复 | Tailwind 配置 |
| `frontend/src/styles/theme.css` | 5.5KB | ✅ 已恢复 | 主题配置 |

---

### 2. 组件文件 ⚠️ 需谨慎恢复

| 文件 | 后果 | 说明 |
|------|------|------|
| `frontend/src/components/BacklogPanel.vue` | 可能冲突 | 待办面板组件 |
| `frontend/src/components/CharSection.vue` | **可能冲突** | 角色区块组件 |
| `frontend/src/components/CharacterSprite.vue` | 可能冲突 | 角色精灵图组件 |
| `frontend/src/components/CreateCharacterModal.vue` | **可能冲突** | 创建角色模态框 |
| `frontend/src/components/CreateWorldModal.vue` | **可能冲突** | 创建世界模态框 |
| `frontend/src/components/DialogBox.vue` | 可能冲突 | 对话框组件 |
| `frontend/src/components/HudBar.vue` | 可能冲突 | HUD 栏组件 |
| `frontend/src/components/KnowledgeGraphModal.vue` | 可能冲突 | 知识图谱模态框 |
| `frontend/src/components/ParticleBackground.vue` | 可能冲突 | 粒子背景组件 |
| `frontend/src/components/RelationshipStageOverlay.vue` | 可能冲突 | 关系阶段覆盖组件 |
| `frontend/src/components/SaveLoadPanel.vue` | 可能冲突 | 存档面板组件 |

**风险**: 当前分支已有 `StepCreateModal.vue` 和 `EditCharacterModal.vue`，恢复旧的 `CreateCharacterModal.vue` 可能导致冲突。

---

### 3. 页面文件 ⚠️ 需谨慎恢复

| 文件 | 后果 | 说明 |
|------|------|------|
| `frontend/src/views/WorldDetail.vue` | 可能冲突 | 世界详情页 |
| `frontend/src/views/Worlds.vue` | **高风险** | 世界列表页 |

**风险**: 恢复后可能覆盖当前的页面实现。

---

### 4. Pinia Stores ⚠️ 需谨慎恢复

| 文件 | 后果 | 说明 |
|------|------|------|
| `frontend/src/stores/learning.ts` | **高风险** | 学习状态管理 |
| `frontend/src/stores/settings.ts` | **高风险** | 设置状态管理 |
| `frontend/src/stores/world.ts` | **高风险** | 世界状态管理 |

**风险**: 当前代码可能已迁移到其他状态管理方案，恢复可能破坏功能。

---

### 5. 后端服务文件 ⚠️ 需谨慎恢复

| 文件 | 后果 | 说明 |
|------|------|------|
| `backend/services/prompt_builder/modules/*` | **高风险** | 提示词构建器模块 |
| `backend/services/prompt_builder/contexts/*` | **高风险** | 提示词上下文 |
| `backend/services/prompt_builder/base.py` | **高风险** | 基础提示词构建 |
| `backend/services/llm/*.py` | **高风险** | LLM 适配器文件 |
| `backend/services/user_profile.py` | 可能冲突 | 用户画像服务 |

**风险**: 这些文件可能已被重构或替代，恢复可能导致严重冲突。

---

### 6. 数据库迁移 ⚠️ 谨慎恢复

| 文件 | 说明 |
|------|------|
| `backend/alembic/versions/2026_04_06_add_character_experience.py` | 添加角色经验字段 |
| `backend/alembic/versions/2026_04_06_add_user_profiles.py` | 添加用户画像表 |

**注意**: 如果这些迁移已在生产环境运行，恢复可能造成数据不一致。

---

### 7. 测试文件 ⚠️ 谨慎恢复

| 文件 | 说明 |
|------|------|
| `backend/tests/test_llm_adapter.py` | LLM 适配器测试 |
| `backend/tests/test_minimax.py` | Minimax API 测试 |
| `backend/tests/test_prompt_builder.py` | 提示词构建器测试 |
| `backend/tests/test_user_profile.py` | 用户画像测试 |

---

### 8. 文档文件 ✅ 安全恢复

| 文件 | 说明 |
|------|------|
| `docs/DEPLOYMENT.md` | 部署文档 |
| `docs/deployment_packaging_options.md` | 部署选项文档 |
| `docs/persona_generate_design.md` | Persona 生成设计 |
| `docs/vue3_migration_contract_adaptation.md` | Vue3 迁移适配 |
| `docs/UI迁移书.md` | UI 迁移指南 |
| `memory/*.md` | 项目记忆文档 |
| `idea/idea.md` | 创意文档 |
| `first_work_record.md` | 工作记录 |

---

### 9. 其他文件 ❌ 不建议恢复

| 文件 | 说明 |
|------|------|
| `.worktrees/*` | 已删除的 worktree 目录 |
| `skill-cowork/` | 子模块，可能已独立 |
| `paper2galgame/` | 已废弃的项目 |
| `src__figma/` | 已废弃的 Figma 导入 |

---

## 恢复命令示例

### 恢复单个文件/目录
```bash
git checkout bcd5811 -- <文件或目录路径>
```

### 恢复所有样式和资源
```bash
git checkout bcd5811 -- frontend/src/assets/ frontend/src/styles/
```

### 恢复单个组件
```bash
git checkout bcd5811 -- frontend/src/components/BacklogPanel.vue
```

---

## 恢复后果评估

### 低风险 (可安全恢复)
- 文档文件 (`docs/*.md`)
- 样式文件 (`*.css`)
- 图片资源 (`*.jpg`, `*.png`)

### 中风险 (可能冲突)
- 组件文件 (需检查当前实现)
- 页面文件 (需手动合并)

### 高风险 (可能导致功能损坏)
- Store 文件
- 后端服务文件
- 数据库迁移文件

---

## 建议

1. **已恢复**: 样式和资源文件 ✅
2. **待确认**: 组件和页面文件 (建议先备份当前版本)
3. **不建议**: 后端服务和 Store 文件
4. **安全恢复**: 文档文件
