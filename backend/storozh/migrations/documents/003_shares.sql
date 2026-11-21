-- «Поделиться документом»: одноразово выданная ссылка на 24 часа с журналом просмотров. В базе только хеш токена.
CREATE TABLE shares (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id    uuid        NOT NULL,
    document_id   uuid        NOT NULL REFERENCES documents (id),
    token_hash    text        NOT NULL UNIQUE,
    created_at    timestamptz NOT NULL DEFAULT now(),
    expires_at    timestamptz NOT NULL,
    revoked_at    timestamptz,
    views         int         NOT NULL DEFAULT 0,
    last_view_at  timestamptz
);
CREATE INDEX shares_document ON shares (document_id, created_at DESC);
CREATE TABLE share_views (
    id         bigserial   PRIMARY KEY,
    share_id   uuid        NOT NULL REFERENCES shares (id) ON DELETE CASCADE,
    viewed_at  timestamptz NOT NULL DEFAULT now()
);
