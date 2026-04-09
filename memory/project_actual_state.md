---
name: Actual Codebase State (2026-04-09 v1.0.0-baseline)
description: Verified snapshot after D0 baseline reset — World system in main, UI Phase 1-9 done, PR #174 pending split
type: project
---

## main branch (v1.0.0-baseline)

**Git tag**: `v1.0.0-baseline` (bb5d151)

### Backend models (World system schema)
- **Tables**: User, UserProfile, World, Character, TeacherPersona, WorldCharacter, Course, LearnerProfile, Session, ChatMessage, ProgressTracking, Checkpoint, Save, Knowledge, FSRSState
- **World system**: World → WorldCharacter → Character, World → Course
- **Relationship**: 4-dim JSON (trust/familiarity/respect/comfort) + stage on Session
- **4 Alembic migrations**: 2026_04_06_add_character_experience, 2026_04_06_add_user_profiles, 2026_04_08_add_character_title, 2026_04_08_add_course_meta_json

### Backend services
- `memory.py` = **stub** (returns empty). Knowledge retrieval NOT implemented
- `knowledge.py` = **stub** (empty implementation)
- `learning_engine.py` = functional, dual-layer prompt, ZPD scaffold, emotion analysis
- `llm/adapter.py` = **refactored** (official SDKs: Claude, OpenAI, Ollama)
- `prompt_builder/` = **NEW** modular prompt injection system
- `dynamic_analyzer.py` = emotion analysis service
- `relationship.py` = relationship tracking

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
- docker-compose.yml references PostgreSQL (NOT used, outdated)

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

## Open Issues (post D0 reset)

- **#172**: [bugfix] 登录页面从注册切换到登入时动画不平滑 (P1, creator)
  - 相关文件: frontend/src/views/Login.vue
  - 状态: 待处理

- **#183**: feat: 存储结构重设计 - 记忆事实表 + DB 存档 (P1)
  - 依赖 P0 #175（合并 Alembic 双 head）修完后才能开始
  - 设计：新增 memory_facts + save_snapshots 表
  - 删除：knowledge.py 关键词召回、./saves/ JSON 存档
  - 状态: 待 Creator 实现

---

## D0 Changes Summary

| Action | Status |
|--------|--------|
| Tag v1.0.0-baseline | ✅ Done |
| Close old issues (#124-133, #150, #157, #159-160, #163-172) | ✅ Done |
| PR #174 review | ✅ Done (Request Changes) |
| memory/project_actual_state.md | ✅ Updated |

---

**Why**: Knowing the gap between design docs and actual code is critical for accurate reviews.
**How to apply**: When reviewing PRs, verify against this snapshot. World system IS in main as of v1.0.0-baseline.
