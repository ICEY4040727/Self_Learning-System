-- PostgreSQL audit trail for users LLM UPDATE statements.
--
-- Goals:
--   1) Correlate DB writes with app gateway trace_id (SET LOCAL app.user_llm_write_trace)
--   2) Flag legacy-only UPDATE attempts for operator/script attribution
--   3) Complement (not replace) application logs: USER_LLM_WRITE / USER_LLM_WRITE_BLOCKED
--
-- Optional: enable pgAudit for DDL/DCL and broader DML auditing:
--   CREATE EXTENSION IF NOT EXISTS pgaudit;
--   ALTER SYSTEM SET pgaudit.log = 'write';
--   ALTER SYSTEM SET pgaudit.log_relation = 'users';
--   SELECT pg_reload_conf();
--
-- Apply:
--   psql "$DATABASE_URL" -f backend/db/postgres/user_llm_audit.sql

CREATE SCHEMA IF NOT EXISTS app;

CREATE TABLE IF NOT EXISTS app.user_llm_update_audit (
    id BIGSERIAL PRIMARY KEY,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    db_user TEXT NOT NULL DEFAULT current_user,
    application_name TEXT DEFAULT current_setting('application_name', true),
    client_addr INET DEFAULT inet_client_addr(),
    user_row_id INTEGER,
    write_trace TEXT DEFAULT current_setting('app.user_llm_write_trace', true),
    legacy_changed BOOLEAN NOT NULL,
    json_changed BOOLEAN NOT NULL,
    legacy_only BOOLEAN GENERATED ALWAYS AS (legacy_changed AND NOT json_changed) STORED,
    old_default_provider TEXT,
    new_default_provider TEXT,
    old_model TEXT,
    new_model TEXT,
    old_llm_base_url TEXT,
    new_llm_base_url TEXT
);

CREATE INDEX IF NOT EXISTS idx_user_llm_update_audit_occurred_at
    ON app.user_llm_update_audit (occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_llm_update_audit_legacy_only
    ON app.user_llm_update_audit (legacy_only, occurred_at DESC)
    WHERE legacy_only;

COMMENT ON TABLE app.user_llm_update_audit IS
    'Audit trail for users LLM column updates. legacy_only=true indicates bare legacy write.';

CREATE OR REPLACE FUNCTION app.users_audit_llm_update()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    legacy_changed boolean;
    json_changed boolean;
BEGIN
    legacy_changed := (
        OLD.default_provider IS DISTINCT FROM NEW.default_provider OR
        OLD.encrypted_api_key IS DISTINCT FROM NEW.encrypted_api_key OR
        OLD.model IS DISTINCT FROM NEW.model OR
        OLD.llm_base_url IS DISTINCT FROM NEW.llm_base_url
    );
    json_changed := OLD.llm_provider_settings IS DISTINCT FROM NEW.llm_provider_settings;

    IF NOT legacy_changed AND NOT json_changed THEN
        RETURN NEW;
    END IF;

    INSERT INTO app.user_llm_update_audit (
        user_row_id,
        write_trace,
        legacy_changed,
        json_changed,
        old_default_provider,
        new_default_provider,
        old_model,
        new_model,
        old_llm_base_url,
        new_llm_base_url
    ) VALUES (
        NEW.id,
        current_setting('app.user_llm_write_trace', true),
        legacy_changed,
        json_changed,
        OLD.default_provider,
        NEW.default_provider,
        OLD.model,
        NEW.model,
        OLD.llm_base_url,
        NEW.llm_base_url
    );

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_users_audit_llm_update ON users;
CREATE TRIGGER trg_users_audit_llm_update
AFTER UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION app.users_audit_llm_update();

-- Sample queries for operators:
-- Recent gateway-marked writes:
--   SELECT * FROM app.user_llm_update_audit
--   WHERE write_trace IS NOT NULL AND write_trace <> ''
--   ORDER BY occurred_at DESC LIMIT 50;
--
-- Suspected bare legacy writes (no app trace + legacy-only):
--   SELECT * FROM app.user_llm_update_audit
--   WHERE legacy_only AND (write_trace IS NULL OR write_trace = '')
--   ORDER BY occurred_at DESC;
