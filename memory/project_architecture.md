---
name: Architecture direction - World/SQLite redesign
description: Major architectural shift from PostgreSQL+ChromaDB to SQLite single-file with JSON columns, World/Course/Character model
type: project
---

The project is undergoing a major architecture redesign (documented in `docs/course_system_design.md`):

**Why:** Personal local app, single user — PostgreSQL/ChromaDB/Neo4j are overkill. SQLite single-file is zero-config.

**Key changes:**
- World concept: immersive environment containing Characters (Sage=teacher, Traveler=user) + Courses + Knowledge
- SQLite single-file `socratic_learning.db` replaces PostgreSQL
- Knowledge graph stored as JSON column (not separate Neo4j/graph DB)
- ChromaDB removed — LLM does semantic matching on full knowledge JSON
- 4-dimension relationship model: Trust, Familiarity, Respect, Comfort → 5 stages (Stranger→Partner)
- Version-control style save system: Checkpoints + Branch/Fork (no overwrite)
- 7 memory types for learner modeling based on Bloom/ITS/cognitive science theory

**How to apply:** All new DB work should target SQLite. The current PostgreSQL code is being migrated.
