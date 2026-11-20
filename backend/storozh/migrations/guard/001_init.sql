-- Сторож (Разработчик 3). Аудит — в shared.audit_log (shared/002).
CREATE TABLE alerts (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id     uuid        NOT NULL,
    citizen_id   uuid        NOT NULL,
    document_id  uuid,
    rule_id      text        NOT NULL,
    rule_version int         NOT NULL,
    severity     text        NOT NULL CHECK (severity IN ('critical', 'high', 'info')),
    title        text        NOT NULL,
    explanation  text,
    verdict      text        CHECK (verdict IN ('me', 'not_me')),
    status       text        NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'seen', 'closed')),
    tg_message_id text,                          -- чтобы дописать объяснение правкой сообщения
    created_at   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (event_id, rule_id)                   -- повтор события не даёт второй тревоги
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
    submitted_at        timestamptz,             -- форма аннулирования отправлена: повтор запрещён
    evidence_enc        bytea,                   -- скриншот результата
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

-- Одноразовые приглашения в семью: код -> согласие с правами.
CREATE TABLE invite_codes (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    code_hash   text        NOT NULL UNIQUE,
    grantor_id  uuid        NOT NULL,
    scopes      text[]      NOT NULL,
    expires_at  timestamptz NOT NULL,
    used_at     timestamptz
);

CREATE TABLE telegram_links (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id   uuid        NOT NULL UNIQUE,
    chat_id_enc  bytea       NOT NULL,
    chat_id_hmac text        NOT NULL UNIQUE,    -- поиск по chat_id без расшифровки
    linked_at    timestamptz NOT NULL DEFAULT now()
);

-- Привязка Telegram: t.me/<bot>?start=link_<token>, 10 минут.
CREATE TABLE link_tokens (
    token_hash  text        PRIMARY KEY,
    citizen_id  uuid        NOT NULL,
    expires_at  timestamptz NOT NULL,
    used_at     timestamptz
);
