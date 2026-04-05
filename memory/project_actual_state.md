---
name: Actual Codebase State (2026-04-03)
description: Verified snapshot of what's actually in main vs what's planned — models still use old schema, memory.py is stub, world-system-wip branch has new models
type: project
---

## main branch (current deployed state)

**Backend models (old schema, NOT yet migrated to World system)**:
- 13 tables: User, Character, TeacherPersona, LearnerProfile, Subject, LessonPlan, LearningDiary, ProgressTracking, Session, ChatMessage, RelationshipStageRecord, Save
- Subject FK → Character (not World)
- Session has `relationship_stage` string (not 4-dim JSON)
- No World, WorldCharacter, Course, Checkpoint, Knowledge, FSRSState tables yet

**Backend services**:
- `memory.py` = **stub** (all no-ops, returns empty). ChromaDB removed but JSON knowledge not yet implemented
- `learning_engine.py` = functional, dual-layer prompt, ZPD scaffold, emotion analysis, but knowledge_context always ""
- `llm/adapter.py` = Claude/OpenAI/Local adapters via raw httpx (not using official SDKs)
- `dynamic_analyzer.py` = emotion analysis service

**Frontend**:
- Home.vue = Galgame VN menu (particles, character select, subject select)
- Learning.vue = 4-layer layout, DialogBox 4-mode state machine, CharacterDisplay, HudBar, BacklogPanel, SaveLoad, ToolConfirmDialog
- Phase A visual polish merged (blur, rounded, jump animation)

**Database**: SQLite single file (`data/socratic_learning.db`), no PostgreSQL/ChromaDB/Neo4j
**Docker**: frontend (nginx) + backend only, no DB containers

## feat/world-system-wip branch (NOT merged)
- New models: World, WorldCharacter, Course, Checkpoint, Knowledge, FSRSState
- 4-dim relationship JSON on Session
- ~2400 lines changed across all backend files
- Has migration scripts in `scripts/`

## Open issues (#130 is P0)
- #130: WorldCharacter management API missing → learning engine can't get teacher persona
- #131: archive.py get_characters duplicate filter (P2)
- #132: FK columns missing nullable=False (P1)
- #133: Missing SQLite schema smoke test (P2)
- #124-#127: Phase 1-4 of World system implementation
- #129: World system data model restructure

**Why:** Knowing the gap between design docs and actual code is critical for accurate reviews.
**How to apply:** When reviewing PRs, verify against actual main code, not design docs. The World system is NOT yet in main.
