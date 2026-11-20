-- Общая шина событий. Только дописывается: UPDATE и DELETE запрещены всем ролям контекстов.
CREATE TABLE shared.outbox (
    seq         bigserial   PRIMARY KEY,
    event_id    uuid        NOT NULL UNIQUE,
    topic       text        NOT NULL,
    citizen_id  uuid        NOT NULL,
    payload     jsonb       NOT NULL,
    dedupe_key  text        NOT NULL UNIQUE,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX outbox_topic_seq ON shared.outbox (topic, seq);

-- Курсор каждого потребителя.
CREATE TABLE shared.consumer_offsets (
    consumer    text        PRIMARY KEY,
    last_seq    bigint      NOT NULL DEFAULT 0,
    updated_at  timestamptz NOT NULL DEFAULT now()
);

DO $$
DECLARE ctx text;
BEGIN
    FOREACH ctx IN ARRAY ARRAY['platform', 'documents', 'guard', 'assistant'] LOOP
        EXECUTE format('REVOKE ALL ON shared.outbox, shared.consumer_offsets FROM %I', 'storozh_' || ctx);
        EXECUTE format('GRANT SELECT, INSERT ON shared.outbox TO %I', 'storozh_' || ctx);
        EXECUTE format('GRANT USAGE ON SEQUENCE shared.outbox_seq_seq TO %I', 'storozh_' || ctx);
        EXECUTE format('GRANT SELECT, INSERT, UPDATE ON shared.consumer_offsets TO %I', 'storozh_' || ctx);
    END LOOP;
END $$;
