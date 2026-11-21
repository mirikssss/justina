-- Проверки перед сделкой и кабинет нотариуса (POST /v1/checks). Храним запрос и результат: журнал «почему так решили».
CREATE TABLE checks (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id  uuid        NOT NULL,
    request     jsonb       NOT NULL,
    result      jsonb       NOT NULL,
    status      text        NOT NULL CHECK (status IN ('pending', 'approved', 'denied', 'expired')),
    created_at  timestamptz NOT NULL DEFAULT now(),
    expires_at  timestamptz NOT NULL DEFAULT now() + interval '24 hours'
);
CREATE INDEX checks_citizen_created ON checks (citizen_id, created_at DESC);
