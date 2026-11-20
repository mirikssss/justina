-- Схема и роль на каждый контекст. Роль видит только свою схему и общую shared.
-- Приложение подключается одним пользователем и делает SET ROLE storozh_<context> (см. shared/db.py).
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
DECLARE ctx text;
BEGIN
    FOREACH ctx IN ARRAY ARRAY['shared', 'platform', 'documents', 'guard', 'assistant'] LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'storozh_' || ctx) THEN
            EXECUTE format('CREATE ROLE %I NOLOGIN', 'storozh_' || ctx);
        END IF;
        EXECUTE format('GRANT %I TO CURRENT_USER', 'storozh_' || ctx);
        EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', ctx);
        EXECUTE format('GRANT USAGE, CREATE ON SCHEMA %I TO %I', ctx, 'storozh_' || ctx);  -- только в своей схеме
        EXECUTE format('GRANT USAGE ON SCHEMA shared TO %I', 'storozh_' || ctx);
        EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %I',
                       ctx, 'storozh_' || ctx);
        EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT USAGE, SELECT ON SEQUENCES TO %I',
                       ctx, 'storozh_' || ctx);
    END LOOP;
END $$;
