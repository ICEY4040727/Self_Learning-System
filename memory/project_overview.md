---
name: Project Overview
description: Socratic-method AI personalized learning platform with Galgame-style immersive UI, Vue3+FastAPI+SQLite stack
type: project
---

**Self_Learning-System**: AI personalized learning platform using Socratic teaching method with Galgame visual novel style UI.

**Core concepts** (from course_system_design.md):
- **World**: immersive environment with its own worldview, scenes, character combinations
- **Sage** (teacher character): has TeacherPersona, sprites, relationship system
- **Traveler** (user): can have sprites, no inner monologue
- **Course**: learning content within a World

**Key systems**:
- 4-dimensional relationship model: Trust/Familiarity/Respect/Comfort -> 5 stages (stranger->partner)
- 7-type knowledge graph (knowledge/edge/misconception/skill/episode/preference/metacognition)
- Dynamic prompt assembly: persona template + relationship stage + emotion + knowledge state
- Version-control style save system (COMMIT/BRANCH checkpoints)

**Current phase**: Phase 5 (deployment + polish). Recently completed SQLite migration (Phase 0). World system design done, implementation pending.

**Why:** Owner's vision is users create AI teacher personas (historical figures, game characters, custom) and learn through Socratic dialogue in an immersive Galgame setting.

**How to apply:** All reviews should consider educational effectiveness (not just code quality) and Galgame immersion (not just functionality).
