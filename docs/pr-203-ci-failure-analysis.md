# PR #203 CI 失败分析

## 基本信息
- **PR**: #203 - feat: UI polish - 统一页面风格与修复滚动问题
- **分支**: feat/ui-polish-world-pages
- **状态**: OPEN
- **创建时间**: 2026-04-09 14:27:52

## CI 状态总览

| 检查名称 | 状态 | 说明 |
|---------|------|------|
| lint | ❌ FAIL | Ruff 代码风格检查失败 |
| phase4-ui-e2e | ❌ FAIL | E2E 测试失败 |
| phase4-ui-e2e (Phase4 Evidence) | ❌ FAIL | E2E 测试失败 |
| frontend-build | ✅ PASS | 前端构建成功 |
| pr-issue-closure | ✅ PASS | PR Issue 关闭检查通过 |
| docker-compose-smoke | ✅ PASS | Docker 集成测试通过 |
| backend-test | ⏭️ SKIPPED | 后端测试跳过 |

---

## 1. Lint 失败详情

Ruff 检查发现 **48+ 个** 代码风格问题，主要包括：

### 问题类型
| 错误码 | 数量 | 描述 |
|--------|------|------|
| I001 | 5+ | Import 顺序或格式不正确 |
| F401 | 8+ | 导入但未使用的模块 |
| W293 | 35+ | 空行包含空白符 |

### 涉及文件

#### Alembic Migration 文件
1. `backend/alembic/versions/2026_04_06_000_create_base_tables.py:10:1` - I001
2. `backend/alembic/versions/2026_04_06_add_character_experience.py` - F401 (sqlalchemy, alembic.op)
3. `backend/alembic/versions/2026_04_06_add_user_profiles.py` - I001, F401
4. `backend/alembic/versions/2026_04_08_add_character_title.py` - F401
5. `backend/alembic/versions/2026_04_08_add_course_meta_json.py` - I001, F401
6. `backend/alembic/versions/2026_04_09_add_memory_facts_and_save_snapshots.py` - I001, W293 (4处)

#### API 路由文件
- `backend/api/routes/archive.py`
  - Line 6:28 - F401 (`sqlalchemy.exc.IntegrityError` 未使用)
  - W293 - 15 处空行包含空白符

### 修复建议

```bash
# 自动修复大部分问题
cd backend && ruff check --fix .

# 或针对特定文件
ruff check --fix backend/alembic/versions/
ruff check --fix backend/api/routes/archive.py
```

---

## 2. E2E 测试失败详情

### 测试 1: knowledge graph renders and node click reveals detail

**失败原因**: Test timeout of 30000ms exceeded

**错误信息**:
```
locator.click: Test timeout of 30000ms exceeded.
Call log:
  - waiting for getByRole('button', { name: '📊 图谱' })
```

**分析**:
- 测试无法找到 "📊 图谱" 按钮
- 可能原因：
  1. 该按钮在 PR 修改中被移除或禁用
  2. 按钮的 accessibility name 发生变化
  3. 学习页面渲染延迟
  4. 该功能尚未实现或被注释掉

**相关代码**:
- `frontend/e2e/phase4-ui.spec.mjs:113`
- `frontend/src/views/Learning.vue`

---

### 测试 2: learning page applies mobile layout for dual-role scene

**失败原因**: expect(locator).toBeVisible() failed

**错误信息**:
```
Locator: locator('.character-layer')
Expected: visible
Timeout: 5000ms
Error: element(s) not found
```

**分析**:
- 移动端视口测试中找不到 `.character-layer` 元素
- 可能原因：
  1. PR 中对学习页面布局进行了重构
  2. `.character-layer` 类名或结构发生变化
  3. 移动端布局样式问题导致元素未渲染

**相关代码**:
- `frontend/e2e/phase4-ui.spec.mjs:134`
- `frontend/src/views/Learning.vue`

---

## 3. PR 修改文件清单

### 前端文件
| 文件 | 变更 | 说明 |
|------|------|------|
| `frontend/src/router/index.ts` | +6/-8 | CoursePage 路由改为独立路由 |
| `frontend/src/views/Worlds.vue` | +155/-219 | 改为 Character 风格列表视图 |
| `frontend/src/views/WorldDetail.vue` | +24/-43 | 移除卡片背景 |
| `frontend/src/views/CoursePage.vue` | +247/-139 | 统一为 Character 风格 |
| `frontend/src/views/Archive.vue` | +6/-4 | 修复滚动限制 |
| `frontend/src/views/Settings.vue` | +8/-6 | 修复滚动限制 |
| `frontend/src/views/Learning.vue` | +1/-2 | 移除未使用导入 |
| `frontend/src/components/CreatePersonaModal.vue` | 0/-1 | 移除未使用导入 |
| `frontend/src/types/index.ts` | +1/0 | 添加类型字段 |

### 后端文件
| 文件 | 变更 | 说明 |
|------|------|------|
| `backend/api/routes/learning.py` | +212/-209 | 添加 message_count 等字段 |
| `backend/api/routes/archive.py` | +14/-2 | API 修改 |
| `backend/alembic/versions/*.py` | 多个 | Lint 问题 |

---

## 4. 修复优先级

### P0 - 阻塞合并
1. **修复 Ruff Lint 问题** - 必须通过
   - 运行 `ruff check --fix backend/`
   - 手动处理剩余问题

### P1 - E2E 测试
2. **修复 Knowledge Graph 测试**
   - 检查 "📊 图谱" 按钮是否存在
   - 更新测试或恢复功能

3. **修复移动端布局测试**
   - 检查 `.character-layer` 元素
   - 确认移动端样式正确

---

## 5. 下一步行动

1. 立即修复 Lint 问题（最简单）
2. 本地运行 E2E 测试确认问题
3. 更新测试用例或恢复缺失功能
4. 重新推送触发 CI

```bash
# 本地验证
cd backend && ruff check --fix .
cd frontend && npm run test:e2e
```

---

## 6. 相关 Issue

- Closes #188, #189, #191, #192

---

## 7. 其他已关闭但未合并的 PR

在检查仓库历史时，发现以下 PR 已关闭但未合并：

### PR #170 - feat: migrate shared style foundation for phase A

| 属性 | 值 |
|------|-----|
| 状态 | CLOSED (未合并) |
| 分支 | feat/163-shared-style-base |
| 可合并性 | MERGEABLE ✅ |
| CI 状态 | 全部通过 ✅ |
| 关闭时间 | 2026-04-05 07:41:13 |

**CI 检查结果**:
- ✅ lint
- ✅ frontend-build
- ✅ backend-test
- ✅ phase4-ui-e2e
- ✅ docker-compose-smoke

**Reviewer 结论**: "通过（可合并）...阻塞项：无。Owner 如同意，可执行 merge。"

**关闭原因**: 评论显示 "Closing to resubmit with rebuild screenshots" —— 为了重新提交带重建截图的版本而关闭

**分析**: 这是一个**可挽回的 PR**，CI 全部通过，Reviewer 已批准，只是因为截图需要重建而关闭。

---

### PR #171 - feat: 更新登录页面文字 - ZHĪ YÙ · 愿求知者皆得其道

| 属性 | 值 |
|------|-----|
| 状态 | CLOSED (未合并) |
| 分支 | feat/login-page-text-update |
| 可合并性 | CONFLICTING ❌ |
| CI 状态 | 无记录 |
| 关闭时间 | 2026-04-05 15:35:56 |

**变更内容**:
- 顶部标语改为 `ZHĪ YÙ · 愿求知者皆得其道`
- 底部版本号改为 `ZHĪ YÙ v1.0.0`

**分析**: 这是一个**有 merge conflict 的 PR**，需要重新基于最新的 main 分支解决冲突后再提交。

---

## 8. 总结与建议

### 需要关注的 PR

| PR | 问题 | 建议操作 |
|----|------|----------|
| #203 | Lint + E2E 失败 | 修复后可合并 |
| #170 | 已关闭但 CI 全绿 | 考虑重新开启或 cherry-pick |
| #171 | Merge conflict | 解决冲突后重新提交 |

### 建议行动

1. **立即修复 #203** - 这是当前阻塞的唯一 PR
2. **恢复 #170 的内容** - 如果 shared style foundation 的更改仍有价值，可以：
   - 重新开启 PR（如果分支仍存在）
   - 或将更改 cherry-pick 到新分支
3. **#171 可暂时搁置** - 登录页面文字更改是低优先级的美化工作
