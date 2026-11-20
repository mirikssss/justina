-- Документы (Разработчик 1). Между схемами нет внешних ключей, только UUID.
CREATE TABLE sources (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id     text        NOT NULL,          -- "mygov.car_poa"
    citizen_id    uuid        NOT NULL,
    last_poll_at  timestamptz,
    last_ok_at    timestamptz,
    last_error    text,
    enabled       boolean     NOT NULL DEFAULT true,
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (citizen_id, source_id)
);

CREATE TABLE source_sessions (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id  uuid        NOT NULL,
    provider    text        NOT NULL DEFAULT 'oneid',
    state_enc   bytea       NOT NULL,            -- Playwright storage state, зашифрован
    expires_at  timestamptz,
    status      text        NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired', 'revoked')),
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (citizen_id, provider)
);

CREATE TABLE documents (
    id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    uri              text        NOT NULL,
    citizen_id       uuid        NOT NULL,
    kind             text        NOT NULL,
    source           text        NOT NULL,
    status           text        NOT NULL,
    owner_role       text        NOT NULL,
    title            text        NOT NULL,
    current_version  int         NOT NULL DEFAULT 1,
    first_seen_at    timestamptz NOT NULL DEFAULT now(),
    last_seen_at     timestamptz NOT NULL DEFAULT now(),
    missing_count    int         NOT NULL DEFAULT 0,
    created_at       timestamptz NOT NULL DEFAULT now(),
    UNIQUE (citizen_id, uri)
);
CREATE INDEX documents_feed ON documents (citizen_id, last_seen_at DESC);

-- Версии только дописываются.
CREATE TABLE document_versions (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id   uuid        NOT NULL REFERENCES documents,
    version_no    int         NOT NULL,
    content_hash  text        NOT NULL,
    payload       jsonb       NOT NULL,          -- NormalizedDocument: только маски и HMAC
    raw_enc       bytea,                         -- сырой снимок записи, зашифрован
    snapshot_id   uuid        NOT NULL,
    fetched_at    timestamptz NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (document_id, version_no)
);
REVOKE UPDATE, DELETE ON document_versions FROM storozh_documents;

-- Идемпотентность приёма снимков.
CREATE TABLE snapshots (
    snapshot_id  uuid        PRIMARY KEY,
    citizen_id   uuid        NOT NULL,
    source       text        NOT NULL,
    complete     boolean     NOT NULL,
    fetched_at   timestamptz NOT NULL,
    received_at  timestamptz NOT NULL DEFAULT now()
);
