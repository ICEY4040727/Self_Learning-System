## Creator 修复回复

Issue #124（Phase 1: World 数据模型 + 表重构）已完成，采用严格 One-shot 迁移方案（Option A），并提供可审计证据。

### 1) 方案决策

- 选择一次性切换 + 兼容层最小化：直接完成 subjects -> courses、saves -> checkpoints、relationship_stage -> relationship(JSON)，避免双轨长期并存带来的一致性风险。

### 2) 代码变更（后端）

- 模型重构：新增 World / WorldCharacter / Knowledge / Checkpoint / FSRSState / Course，并将 Session 与 LearnerProfile 切换到新结构。
- API 切换：
  - 归档路由：/worlds、/courses、world-profile 语义；
  - 学习路由：/courses/{course_id}/start|chat，session 列表改为课程语义；
  - 存档路由：/checkpoints 全量替代旧 save 接口。
- 服务层对齐：学习引擎读取 learner_profiles.profile，掌握度按 course_id 统计；FSRS 持久化切到 fsrs_states。
- 配置修复：settings 允许忽略无关 .env 字段，避免运行时因额外键失败。

### 3) 数据迁移与回滚工具

- 新增迁移脚本：scripts/migrate_phase1_world_schema.py
- 新增回滚脚本：scripts/rollback_phase1_world_schema.py
- 新增证据脚本：scripts/run_phase1_migration_evidence.py
- 新增执行手册：docs/phase1_migration_playbook.md

### 4) 对 Item 13-16 的可审计证据

证据文件：backend/migration_evidence/phase1_reconciliation_report.json

- Item 13（Character -> World + WorldCharacter）：
  - created_worlds = 2
  - created_world_characters = 2
- Item 14（courses.world_id 回填）：
  - courses_total = 1
  - courses_with_world_id = 1
  - fill_rate = 1.0
- Item 15（sessions world/sage 回填）：
  - migrated_rows = 1
  - filled_world_id = 1
  - filled_sage_character_id = 1
- Item 16（saves -> checkpoints）：
  - legacy_saves = 1
  - migrated_checkpoints = 1
  - fill_rate_world_id = 1.0

并且 post-reconciliation 中：

- worlds = 2
- knowledge = 2（每个 world 一行）
- 关键字段空值统计均为 0（courses.world_id / sessions.world_id / checkpoints.world_id / sessions.relationship / knowledge.graph）
- anomaly samples 为空

### 5) 测试验证

已运行并通过：

- 核心套件：
  - backend/tests/test_phase1_migration.py
  - backend/tests/test_checkpoints.py
  - backend/tests/test_learning_sessions.py
  - backend/tests/test_archive.py
  - 结果：9 passed
- 全量后端：backend/tests
  - 结果：44 passed

### 6) 回滚触发策略（已写入 playbook）

出现以下任一条件立即回滚：

- knowledge 与 worlds 行数不一致
- Item 14/15/16 填充率或迁移数量不达标
- 关键 anomaly 非空
- /api/courses/_ 或 /api/checkpoints/_ 出现 5xx

回滚命令：

- python scripts/rollback_phase1_world_schema.py --db <db_path> --backup <backup_path>
