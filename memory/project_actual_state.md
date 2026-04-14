---
name: Actual Codebase State (2026-04-14 update)
description: Post D0 baseline, CI in place, Legacy Save deprecated, PR #205 pending merge
type: project
---

## main branch (v1.0.0-baseline)

**Git tag**: `v1.0.0-baseline` (bb5d151)

### Backend models (World system schema)
- **Tables**: User, UserProfile, World, Character, TeacherPersona, WorldCharacter, Course, LessonPlan, LearningDiary, ProgressTracking, Session, ChatMessage, RelationshipStageRecord, Checkpoint, SaveSnapshot, MemoryFact, FSRSState
- **World system**: World → WorldCharacter → Character, World → Course
- **Relationship**: 4-dim JSON (trust/familiarity/respect/comfort) + stage on Session
- **4 Alembic migrations**: 2026_04_06_add_character_experience, 2026_04_06_add_user_profiles, 2026_04_08_add_character_title, 2026_04_08_add_course_meta_json

### Backend services
- `memory.py` = **deleted** (no longer exists)
- `knowledge.py` = **deleted** (no longer exists)
- `memory_facts.py` = functional, MemoryFact CRUD + retrieval
- `memory_extractor.py` = memory extraction from conversations
- `learning_engine.py` = functional, dual-layer prompt, ZPD scaffold, emotion analysis
- `llm/adapter.py` = **refactored** (official SDKs: Claude, OpenAI, Ollama)
- `prompt_builder/` = **NEW** modular prompt injection system
- `dynamic_analyzer.py` = emotion analysis service
- `relationship.py` = relationship tracking
- `spaced_repetition.py` = FSRS-based spaced repetition
- `user_profile.py` = cross-world user profile aggregation

### Frontend (UI Phase 1-9 completed)
- **Views**: Login, Home, Worlds, WorldDetail, Character, Learning, Archive, Settings
- **Galgame components**: DialogBox, CharacterDisplay, HudBar, BacklogPanel, CheckpointPanel
- **Character management**: CreateCharacterModal, EditCharacterModal, CreatePersonaModal
- **API client**: unified client.ts with auth headers
- **Styles**: galgame.css, theme.css, fonts.css, tailwind.css

### Database: SQLite single file
- Location: `data/socratic_learning.db`
- No PostgreSQL/ChromaDB/Neo4j (removed in earlier refactor)

### Docker
- frontend (nginx) + backend only
- docker-compose.yml does NOT reference PostgreSQL (cleaned)

### CI
- `.github/workflows/ci.yml` — full pipeline (lint + pytest + npm build + E2E + docker smoke)
- `.github/workflows/phase4-evidence.yml` — evidence collection
- ⚠️ backend-test ignores 11 test files via `--ignore` list

---

## PR #174 Status (feat/character-mgmt-bucket4)

**Decision**: Request Changes (2026-04-09)

**Issues**:
1. PR too large: 174 files, +32k lines (must split)
2. PR description incomplete (missing: affected tables, routes, migration info)
3. Contains unrelated files: paper2galgame/, .worktrees/, skill-cowork

**Required splits**:
1. `feat/backend-llm-refactor` (llm/adapter, prompt_builder)
2. `feat/backend-migrations` (alembic versions)
3. `feat/frontend-character-management` (Character.vue, modals)
4. `feat/frontend-styles` (styles/*.css, galgame components)
5. `docs/v1.0.0-alignment` (course_system_design.md, recovery_guide.md)

---

## Open Issues (2026-04-14 Reviewer 更新)

### P1 Sprint（建议 Creator 按顺序执行）
- **#176**: fix: 修复 checkpoints/sessions FK 循环依赖 (bugfix, P1)
  - Session.parent_checkpoint_id → Checkpoint.id ↔ Checkpoint.session_id → Session.id
  - 状态: 待 Creator 实现
- **#179**: docs: 同步技术栈文档到实际实现 (documentation, P1)
  - CLAUDE.md 有 7+ 处过时描述（ChromaDB/PostgreSQL/Axios/memory.py）
  - 状态: 待 Creator 实现
- **#178**: fix: 登录页注册/登入切换动画优化 (bugfix, P1)
  - Login.vue confirm-fast transition 仅 opacity，无 height/margin 过渡
  - 状态: 待 Creator 实现
- **#181**: test: 存档读档端到端回归测试 (feature, P1 → 原 P2, Reviewer 建议升级)
  - CI 中 --ignore=test_checkpoints.py，无 E2E 覆盖
  - 依赖 #176 先完成
  - 状态: 待 Creator 实现

### P0
- **#204**: P0: 清理 Legacy Save API 冗余接口
  - PR #205 已开，Reviewer 已 Approve，等 Owner 合并
  - Phase 1 (deprecation) 完成，Phase 3 (移除) 待下个版本
- **#207**: refactor: 记忆系统文件化改造
  - ⚠️ Reviewer 指出与已有 SaveSnapshot 模型冲突，需修订设计
  - 状态: 待 Creator 修订方案

### P2 Backlog (v1.1.0)
- **#184**: v1.1.0 知识图谱基于 memory_facts 重做 (feature, P2)
- **#194**: [B4] 前端: 工具调用 UI 占位 (enhancement, P2)

### Closed
- **#177**: ci: 添加 GitHub Actions — ✅ 已完成关闭 (2026-04-14)

---

## Open PRs (2026-04-14)

- **PR #205**: feat(#204): 标记 Legacy /save/* 接口为废弃
  - 状态: Reviewer ✅ Approve (comment)，等 Owner 确认合并
- **PR #206**: docs: 添加 GitHub Projects 设置指南与自动化工作流 (copilot DRAFT)

---

## Reviewer Activity (2026-04-14)

| Action | Status |
|--------|--------|
| 审查全部 9 个 Open Issue 合理性 | ✅ 完成 |
| PR #205 Review (approve) | ✅ 完成 |
| 关闭 #177 (CI 已实现) | ✅ 完成 |
| 评论 #207 (SaveSnapshot 冲突) | ✅ 完成 |
| 评论 #181 (优先级 P2→P1) + 更新 label | ✅ 完成 |
| 更新 memory/project_actual_state.md | ✅ 进行中 |

---

**Why**: Knowing the gap between design docs and actual code is critical for accurate reviews.
**How to apply**: When reviewing PRs, verify against this snapshot. World system IS in main as of v1.0.0-baseline.
