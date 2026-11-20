-- Платформа (Разработчик 3): граждане и веб-сессии.
CREATE TABLE citizens (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    pinfl_hmac    text        NOT NULL UNIQUE,   -- ищем по HMAC, в открытом виде не храним
    pinfl_enc     bytea,
    display_name  text        NOT NULL,
    lang          text        NOT NULL DEFAULT 'uz' CHECK (lang IN ('uz', 'ru')),
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE web_sessions (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id  uuid        NOT NULL,
    token_hash  text        NOT NULL UNIQUE,     -- в cookie случайный токен, здесь его хеш
    expires_at  timestamptz NOT NULL,
    revoked_at  timestamptz,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX web_sessions_citizen ON web_sessions (citizen_id);

-- Одноразовые ссылки входа из бота: 32 байта, 5 минут, одно использование.
CREATE TABLE login_nonces (
    nonce_hash  text        PRIMARY KEY,
    citizen_id  uuid,
    expires_at  timestamptz NOT NULL,
    used_at     timestamptz,
    created_at  timestamptz NOT NULL DEFAULT now()
);
