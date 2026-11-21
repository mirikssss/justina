-- Сторож, шаг 2: потребитель событий.
-- G7 копирует одну тревогу нескольким родственникам на одном event_id -> уникальность включает citizen_id.
ALTER TABLE alerts DROP CONSTRAINT alerts_event_id_rule_id_key;
ALTER TABLE alerts ADD CONSTRAINT alerts_event_rule_citizen_key UNIQUE (event_id, rule_id, citizen_id);
ALTER TABLE alerts ADD COLUMN buttons text[] NOT NULL DEFAULT '{}';
CREATE INDEX alerts_document ON alerts (document_id, created_at DESC) WHERE document_id IS NOT NULL;

CREATE INDEX consents_grantor_active ON consents (grantor_id) WHERE revoked_at IS NULL;

-- G4: доверенности, которые видел guard (схему documents читать нельзя). Обновляется на каждом document.*.
CREATE TABLE poa_watch (
    document_id  uuid        PRIMARY KEY,
    citizen_id   uuid        NOT NULL,
    valid_until  date,
    status       text        NOT NULL,
    updated_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX poa_watch_expiring ON poa_watch (valid_until) WHERE status = 'active';
