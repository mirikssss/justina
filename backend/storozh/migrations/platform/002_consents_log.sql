-- T9 (ЗРУ-547): согласие на обработку фиксируется до сбора данных; отзыв и удаление — в журнале.
CREATE TABLE consents_log (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id   uuid        NOT NULL,
    version      text        NOT NULL,           -- версия текста согласия
    scopes       text[]      NOT NULL,           -- что именно разрешено
    accepted_at  timestamptz NOT NULL DEFAULT now(),
    withdrawn_at timestamptz
);
CREATE INDEX consents_log_citizen ON consents_log (citizen_id, accepted_at DESC);
