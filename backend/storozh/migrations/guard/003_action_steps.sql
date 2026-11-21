-- Сторож, шаг 3: ход действия для /actions/[id] (Action.steps) и быстрый поиск открытых действий.
CREATE TABLE action_steps (
    id         bigserial   PRIMARY KEY,
    action_id  uuid        NOT NULL REFERENCES actions ON DELETE CASCADE,
    status     text        NOT NULL,
    at         timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX action_steps_action ON action_steps (action_id, id);

-- Одно открытое действие одного типа на документ: двойной клик с новым ключом не даёт второго отзыва.
CREATE UNIQUE INDEX actions_one_open ON actions (document_id, type)
    WHERE status NOT IN ('done', 'failed', 'expired');
CREATE INDEX actions_worker ON actions (status, updated_at) WHERE status IN ('awaiting_confirmation', 'confirmed',
                                                                             'executing', 'verifying');
