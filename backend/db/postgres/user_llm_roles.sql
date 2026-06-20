-- PostgreSQL production role split for users LLM settings.
--
-- Enforcement layers:
--   1) DB triggers (2026_06_20_001 migration): block legacy-only UPDATE; sync mirror on JSON update
--   2) Role split below: optional hard deny on legacy columns for business account
--
-- NOTE: Current ORM write gateway updates JSON + legacy in one statement. Triggers allow that
-- (full update). Do NOT enable STRICT legacy REVOKE until the app writes JSON-only on PostgreSQL.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'socratic_app') THEN
        CREATE ROLE socratic_app LOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'socratic_dba') THEN
        CREATE ROLE socratic_dba LOGIN;
    END IF;
END $$;

GRANT USAGE ON SCHEMA public TO socratic_app, socratic_dba;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO socratic_app, socratic_dba;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO socratic_app, socratic_dba;

COMMENT ON ROLE socratic_app IS
    'Business runtime account. Legacy-only users LLM UPDATE blocked by triggers; use ORM gateway.';
COMMENT ON ROLE socratic_dba IS
    'DBA/ops account. High-risk scripts must use: python -m backend.scripts.dba_user_llm_runner';

-- Optional STRICT mode (enable after app writes JSON-only on PostgreSQL):
-- REVOKE UPDATE (default_provider, encrypted_api_key, model, llm_base_url) ON users FROM socratic_app;
-- GRANT UPDATE (
--     username, password_hash, role, llm_provider_settings, temperature, max_tokens, created_at
-- ) ON users TO socratic_app;
