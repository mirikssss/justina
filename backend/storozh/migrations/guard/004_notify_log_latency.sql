-- T2: намерение отправить в Telegram фиксируется ДО отправки отдельной транзакцией.
-- Повтор события видит 'sending' и не шлёт вслепую второй раз; 'sent' — уже доставлено.
CREATE TABLE notify_log (
    key         text        PRIMARY KEY,          -- alert:<id> | action:<id>:<status>
    status      text        NOT NULL CHECK (status IN ('sending', 'sent', 'skipped')),
    message_id  text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

-- T11: задержки для экрана и метрик. detected_at — когда documents заметил изменение (occurred_at события),
-- sent_at — когда тревога ушла в канал уведомлений.
ALTER TABLE alerts ADD COLUMN detected_at timestamptz;
ALTER TABLE alerts ADD COLUMN sent_at timestamptz;
