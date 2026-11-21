-- T1: «ядовитое» событие не должно навсегда останавливать потребителя.
-- Попытки считаем на пару (потребитель, событие); после MAX_ATTEMPTS событие уходит в dead letter, курсор идёт дальше.
CREATE TABLE shared.consumer_attempts (
    consumer    text        NOT NULL,
    seq         bigint      NOT NULL,
    attempts    int         NOT NULL DEFAULT 0,
    last_error  text,
    updated_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (consumer, seq)
);

CREATE TABLE shared.outbox_dead_letter (
    id          bigserial   PRIMARY KEY,
    consumer    text        NOT NULL,
    seq         bigint      NOT NULL,
    event_id    uuid        NOT NULL,
    type        text        NOT NULL,
    citizen_id  uuid        NOT NULL,
    attempts    int         NOT NULL,
    error       text        NOT NULL,
    at          timestamptz NOT NULL DEFAULT now(),
    UNIQUE (consumer, seq)
);
CREATE INDEX outbox_dead_letter_at ON shared.outbox_dead_letter (at DESC);

DO $$
DECLARE ctx text;
BEGIN
    FOREACH ctx IN ARRAY ARRAY['platform', 'documents', 'guard', 'assistant'] LOOP
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON shared.consumer_attempts TO %I', 'storozh_' || ctx);
        EXECUTE format('GRANT SELECT, INSERT ON shared.outbox_dead_letter TO %I', 'storozh_' || ctx);
        EXECUTE format('GRANT USAGE ON SEQUENCE shared.outbox_dead_letter_id_seq TO %I', 'storozh_' || ctx);
    END LOOP;
END $$;
