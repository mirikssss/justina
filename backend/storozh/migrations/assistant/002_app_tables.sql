-- Помощник (Разработчик 3): кэш резюме и история чата. Корпус lex.uz — в 001_lex_corpus.sql.
CREATE TABLE summaries (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id  uuid        NOT NULL,
    version_no   int         NOT NULL,
    lang         text        NOT NULL,
    text         jsonb       NOT NULL,           -- структурированное резюме (Summary)
    citations    jsonb       NOT NULL DEFAULT '[]',
    model        text        NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (document_id, version_no, lang)
);

CREATE TABLE chat_messages (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id   uuid        NOT NULL,
    document_id  uuid        NOT NULL,
    role         text        NOT NULL CHECK (role IN ('user', 'assistant')),
    text         text        NOT NULL,
    citations    jsonb       NOT NULL DEFAULT '[]',
    created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX chat_messages_doc ON chat_messages (citizen_id, document_id, created_at);
