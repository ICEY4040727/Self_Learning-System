# UI 迁移 Phase 9 回归验收矩阵（Issue #149）

本矩阵覆盖页面主链路（Login/Home/Learning/Archive/Character/Settings）与业务红线（world-first、checkpoint commit/branch、relationship/emotion/expression、knowledge-graph、user-scoped 隔离）。

## 1) 回归矩阵

| 用例ID | 覆盖范围 | 前置条件 | 操作步骤 | 预期结果 | 实际结果 | 证据 |
|---|---|---|---|---|---|---|
| RM-LOGIN-001 | Login 页面视觉与入口状态 | 前端 preview 已启动 | 访问 `/login`，检查标题与登录按钮 | 登录页渲染正常，无路由异常 | Pass | `01-login-page.png`, `02-playwright-regression.txt` |
| RM-HOME-001 | Home 页面主菜单 + world-first 入口 | localStorage 存在 token；mock `/api/worlds` | 访问 `/home` → 点击“开始学习” | 进入“选择世界”面板并展示世界卡片 | Pass | `05-home-menu.png`, `06-home-world-selection.png`, `02-playwright-regression.txt` |
| RM-LEARNING-001 | Learning 主链路（知识图谱 + 移动端布局） | mock learning APIs | 打开 `/learning/1?worldId=1`，打开图谱并点击节点；切换 mobile viewport | 图谱可渲染并展示节点详情；移动端布局生效 | Pass | `03-knowledge-graph-node-click.png`, `04-learning-mobile-layout.png`, `02-playwright-regression.txt` |
| RM-ARCHIVE-001 | Archive 页面迁移样式与日记/分叉流程 | mock archive APIs | 访问 `/archive`，打开日记弹窗并执行分叉跳转流程 | 页面四区块正常渲染；日记与分叉流程正常 | Pass | `01-archive-overview.png`, `02-archive-diary-dialog.png`, `02-playwright-regression.txt` |
| RM-CHARACTER-001 | Character 角色/人格/课程链路 | mock character APIs | 创建 world-first 课程、编辑课程 world_id、删除课程 | 课程 CRUD 闭环；world 绑定语义正确 | Pass | `08-character-auto-world-binding.png`, `09-character-edit-world-course.png`, `10-character-multiworld-delete.png`, `02-playwright-regression.txt` |
| RM-SETTINGS-001 | Settings 后端设置与本地偏好拆分 | mock `/api/settings` | 保存 provider+api_key；切换本地偏好后刷新页面 | 后端仅接收 `default_provider/api_key`；本地偏好可恢复 | Pass | `01-settings-backend-save.png`, `02-settings-local-prefs-persist.png`, `02-playwright-regression.txt` |
| RL-WORLD-001 | 红线：world-first | 用户进入 Home/Character 课程路径 | Home 进入“选择世界”；Character 课程创建走 world-first 绑定 | 学习入口必须先落 world，再落 course/session | Pass | `06-home-world-selection.png`, `08-character-auto-world-binding.png`, `04-api-response-snippets.json`, `03-backend-redline-tests.txt` |
| RL-CP-001 | 红线：checkpoint commit/branch | 存在可用 session | 创建 checkpoint，再 branch | 返回有效 checkpoint/branch 响应，branch 继承 course/world | Pass | `04-api-response-snippets.json`, `03-backend-redline-tests.txt` |
| RL-REL-001 | 红线：relationship/emotion/expression | 关系维度接近升级阈值 | 调用 chat 接口触发关系升级 | 响应含 `relationship_stage/events`、`emotion`、`expression_hint` | Pass | `04-api-response-snippets.json`, `03-backend-redline-tests.txt` |
| RL-KG-001 | 红线：knowledge-graph | 已有 world/session 学习数据 | 读取 `/api/worlds/{id}/knowledge-graph`；前端打开图谱 | 图谱接口与前端图谱展示一致可用 | Pass | `03-knowledge-graph-node-click.png`, `04-api-response-snippets.json`, `03-backend-redline-tests.txt` |
| RL-SCOPE-001 | 红线：user-scoped 数据隔离 | owner + other 用户均有角色数据 | owner 拉取 `/api/character` | owner 结果不包含 other 用户角色 | Pass | `04-api-response-snippets.json`, `03-backend-redline-tests.txt` |

## 2) 执行与证据映射

| 证据文件 | 类型 | 对应用例 |
|---|---|---|
| `00-frontend-build.txt` | build 日志 | 全部前端用例基础环境 |
| `01-preview-startup.txt` | preview 启动日志 | 全部前端用例基础环境 |
| `02-playwright-regression.txt` | 前端回归执行日志 | RM-LOGIN-001, RM-HOME-001, RM-LEARNING-001, RM-ARCHIVE-001, RM-CHARACTER-001, RM-SETTINGS-001 |
| `03-backend-redline-tests.txt` | 后端红线 pytest 日志 | RL-WORLD-001, RL-CP-001, RL-REL-001, RL-KG-001, RL-SCOPE-001 |
| `04-api-response-snippets.json` | 接口响应片段 | RL-WORLD-001, RL-CP-001, RL-REL-001, RL-KG-001, RL-SCOPE-001, RM-SETTINGS-001 |
| `01-login-page.png` | 页面截图 | RM-LOGIN-001 |
| `05-home-menu.png` | 页面截图 | RM-HOME-001 |
| `06-home-world-selection.png` | 页面截图 | RM-HOME-001, RL-WORLD-001 |
| `03-knowledge-graph-node-click.png` | 页面截图 | RM-LEARNING-001, RL-KG-001 |
| `04-learning-mobile-layout.png` | 页面截图 | RM-LEARNING-001 |
| `01-archive-overview.png` | 页面截图 | RM-ARCHIVE-001 |
| `02-archive-diary-dialog.png` | 页面截图 | RM-ARCHIVE-001 |
| `08-character-auto-world-binding.png` | 页面截图 | RM-CHARACTER-001, RL-WORLD-001 |
| `09-character-edit-world-course.png` | 页面截图 | RM-CHARACTER-001 |
| `10-character-multiworld-delete.png` | 页面截图 | RM-CHARACTER-001 |
| `01-settings-backend-save.png` | 页面截图 | RM-SETTINGS-001 |
| `02-settings-local-prefs-persist.png` | 页面截图 | RM-SETTINGS-001 |

## 3) 结论

当前迁移页面主链路与红线场景在本轮回归中均通过，可在不依赖口头说明的情况下通过上述日志与截图独立复核。
