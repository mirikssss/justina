-- Сторож (Разработчик 2).
CREATE TABLE alerts (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id     uuid        NOT NULL UNIQUE,    -- одна тревога на событие
    citizen_id   uuid        NOT NULL,
    document_id  uuid,
    rule_id      text        NOT NULL,
    severity     text        NOT NULL CHECK (severity IN ('critical', 'high', 'info')),
    title        text        NOT NULL,
    explanation  text,
    verdict      text        CHECK (verdict IN ('me', 'not_me')),
    status       text        NOT NULL DEFAULT 'open',
    created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX alerts_citizen ON alerts (citizen_id, created_at DESC);

CREATE TABLE actions (
    id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id          uuid        NOT NULL,
    alert_id            uuid        REFERENCES alerts,
    document_id         uuid        NOT NULL,
    type                text        NOT NULL,    -- белый список: revoke_car_poa, ...
    status              text        NOT NULL DEFAULT 'proposed' CHECK (status IN (
                            'proposed', 'awaiting_confirmation', 'confirmed', 'executing',
                            'verifying', 'done', 'failed', 'expired')),
    idempotency_key     text        NOT NULL UNIQUE,
    confirm_code_hash   text,
    confirm_expires_at  timestamptz,
    attempts            int         NOT NULL DEFAULT 0,
    result              jsonb,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE consents (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    grantor_id  uuid        NOT NULL,
    grantee_id  uuid        NOT NULL,
    scopes      text[]      NOT NULL,            -- read_documents, receive_alerts
    granted_at  timestamptz NOT NULL DEFAULT now(),
    revoked_at  timestamptz
);

CREATE TABLE telegram_links (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id   uuid        NOT NULL UNIQUE,
    chat_id_enc  bytea       NOT NULL,
    chat_id_hmac text        NOT NULL UNIQUE,    -- поиск по chat_id без расшифровки
    linked_at    timestamptz NOT NULL DEFAULT now()
);

-- Журнал только дописывается; правка любой строки ломает цепочку хешей.
CREATE TABLE audit_log (
    seq        bigserial   PRIMARY KEY,
    actor      text        NOT NULL,
    action     text        NOT NULL,
    target     text        NOT NULL,
    details    jsonb       NOT NULL DEFAULT '{}',
    at         timestamptz NOT NULL DEFAULT now(),
    prev_hash  text        NOT NULL,
    hash       text        NOT NULL
);
REVOKE UPDATE, DELETE ON audit_log FROM storozh_guard;
