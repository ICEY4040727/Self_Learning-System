# Phase 1 Migration Playbook (Issue #124)

## Scope

This playbook covers the one-shot migration from legacy schema to world-based schema:

- `subjects` -> `courses`
- `saves` -> `checkpoints`
- `sessions.relationship_stage` -> `sessions.relationship` JSON
- New tables: `worlds`, `world_characters`, `knowledge`, `checkpoints`, `fsrs_states`
- Legacy removals: `saves`, `subjects`, `tenants`, `tenant_id`

## Commands

### 1. Run migration with reconciliation report

```bash
python scripts/migrate_phase1_world_schema.py \
  --db backend/data/socratic_learning.db \
  --report backend/data/phase1_migration_report.json
```

### 2. Review reconciliation output

The report includes:

- pre/post table row counts
- key backfill fill rates (items 13-16)
- null statistics
- anomaly samples

```bash
cat backend/data/phase1_migration_report.json
```

### 3. Rollback (if triggered)

```bash
python scripts/rollback_phase1_world_schema.py \
  --db backend/data/socratic_learning.db \
  --backup <backup_path_from_report>
```

## Required Evidence Checklist

The migration report must contain these fields with non-empty metrics:

1. `backfill_results.item_13_character_world_creation`
2. `backfill_results.item_14_course_world_backfill`
3. `backfill_results.item_15_session_world_sage_backfill`
4. `backfill_results.item_16_saves_to_checkpoints`

Each entry must include:

- total rows and migrated rows
- fill rate
- anomaly samples

## Breaking Changes

1. API path changes

- `POST/GET/PUT/DELETE /api/subjects*` removed
- `POST/GET/PUT/DELETE /api/courses*` added
- `POST/GET/DELETE /api/save*` removed
- `POST/GET/DELETE /api/checkpoints*` added

2. Session payload changes

- `relationship_stage` now derived from `relationship.stage`
- Session now requires `course_id` and `world_id`

3. Learner profile schema changes

- `learning_style/cognitive_traits/emotional_traits` removed
- unified `profile` JSON introduced

4. FSRS persistence changes

- `progress_trackings.fsrs_state` removed
- `fsrs_states` table is canonical storage

## Rollback Triggers

Immediately rollback if any condition is met:

1. `post_reconciliation.row_counts.knowledge != post_reconciliation.row_counts.worlds`
2. `item_14_course_world_backfill.fill_rate < 1.0`
3. `item_15_session_world_sage_backfill.filled_world_id < item_15_session_world_sage_backfill.migrated_rows`
4. `item_16_saves_to_checkpoints.migrated_checkpoints < item_16_saves_to_checkpoints.legacy_saves`
5. Any `post_reconciliation.anomaly_samples.*` list is non-empty for blocking categories
6. Smoke tests for `/api/courses/*` or `/api/checkpoints/*` fail with 5xx

## Post-Migration Smoke SQL

```sql
SELECT COUNT(*) AS worlds FROM worlds;
SELECT COUNT(*) AS knowledge_rows FROM knowledge;
SELECT COUNT(*) AS courses_missing_world FROM courses WHERE world_id IS NULL;
SELECT COUNT(*) AS sessions_missing_world FROM sessions WHERE world_id IS NULL;
SELECT COUNT(*) AS checkpoints_missing_world FROM checkpoints WHERE world_id IS NULL;
SELECT COUNT(*) AS orphan_knowledge
FROM worlds w
LEFT JOIN knowledge k ON k.world_id = w.id
WHERE k.world_id IS NULL;
```
