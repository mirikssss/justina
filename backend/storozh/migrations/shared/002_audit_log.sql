-- Журнал аудита (Разработчик 2). Пишут все контексты через shared.audit.write; только дописывается.
-- Правка любой строки ломает цепочку хешей: GET /audit/verify находит номер испорченной записи.
CREATE TABLE shared.audit_log (
    seq        bigserial   PRIMARY KEY,
    actor      text        NOT NULL,             -- citizen:<uuid> | system:<context>
    action     text        NOT NULL,             -- login, action.confirmed, family.view ...
    target     text        NOT NULL,
    at         timestamptz NOT NULL DEFAULT now(),
    prev_hash  text        NOT NULL,
    hash       text        NOT NULL
);

DO $$
DECLARE ctx text;
BEGIN
    FOREACH ctx IN ARRAY ARRAY['platform', 'documents', 'guard', 'assistant'] LOOP
        EXECUTE format('REVOKE ALL ON shared.audit_log FROM %I', 'storozh_' || ctx);
        EXECUTE format('GRANT SELECT, INSERT ON shared.audit_log TO %I', 'storozh_' || ctx);
        EXECUTE format('GRANT USAGE ON SEQUENCE shared.audit_log_seq_seq TO %I', 'storozh_' || ctx);
    END LOOP;
END $$;
