# Issue #127 验收证据（E2E 11~14）

## 11) 完整流程：注册→世界→角色→课程→学习→知识更新→checkpoint→branch

- **自动化用例**：`backend/tests/test_phase4_e2e.py::TestPhase4AcceptanceFlow::test_full_flow_checkpoint_branch_and_temporal_visibility`
- **覆盖点**：
  - 注册/鉴权（通过 `auth_headers` fixture）
  - 世界创建、角色绑定（sage+traveler）、人格激活、课程创建
  - 学习会话启动与对话触发知识更新
  - checkpoint 创建与分叉 branch
  - 分叉后知识时态可见性（主线后置知识隐藏、分叉自有知识可见）
- **本地命令证据**：
  - `01-phase4-backend-e2e.txt`

## 12) 关系系统：四维度变化→阶段派生→事件触发

- **自动化用例**：`backend/tests/test_phase4_e2e.py::TestPhase4AcceptanceFlow::test_relationship_dimensions_stage_and_events`
- **覆盖点**：
  - 预置四维度到阈值临界区
  - chat 后触发 stage 变化（friend → mentor）
  - `relationship_events` 同时包含：
    - `stage_change`
    - `dimension_breakthrough`（trust/familiarity）
  - `RelationshipStageRecord` 持久化
- **本地命令证据**：
  - `01-phase4-backend-e2e.txt`

## 13) 知识图谱可视化：D3 渲染→节点点击→checkpoint_time 过滤

- **自动化用例（UI）**：`frontend/e2e/phase4-ui.spec.mjs::knowledge graph renders and node click reveals detail`
- **自动化用例（后端过滤）**：`backend/tests/test_phase4_e2e.py::TestPhase4AcceptanceFlow::test_full_flow_checkpoint_branch_and_temporal_visibility`
- **证据文件**：
  - `03-knowledge-graph-node-click.png`（图谱渲染 + 节点点击详情）
  - `05-ui-playwright.txt`（UI 自动化执行日志）

## 14) 移动端：双角色缩放与对话框适配

- **自动化用例（UI）**：`frontend/e2e/phase4-ui.spec.mjs::mobile viewport adaptation`
- **覆盖点**：
  - viewport=390x844
  - `.character-layer` 移动端缩放样式生效（transform 非 none）
  - `.dialog-layer` 可见
- **证据文件**：
  - `04-learning-mobile-layout.png`
  - `05-ui-playwright.txt`（UI 自动化执行日志）

## 额外：前端关键迁移自动化覆盖（Character.vue 路径）

- **自动化用例**：`backend/tests/test_phase4_e2e.py::TestCharacterCourseMigrationFlow::test_course_crud_and_world_binding_paths`
- **覆盖点**：
  - world 绑定路径（等价 `ensurePrimaryWorldForCharacter`）
  - 课程创建/编辑/删除
  - 多 world 聚合场景（按 world 读取课程）

## 部署闭环证据（Docker）

- **CI Job**：`.github/workflows/ci.yml` 新增 `docker-compose-smoke`
- **产物**：
  - `docker-compose-ps.txt`
  - `docker-health.json`
  - `docker-backend.log`
  - `docker-frontend.log`
- **本地补充证据**：
  - `06-docker-compose-services.txt`（仅两容器拓扑）
  - `07-local-health.json`（后端健康检查）
