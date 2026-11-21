-- Состояние корпуса и индекса RAG: отпечатки кода загрузки и индексации (storozh rag ensure).
-- Отпечаток изменился (новый акт в sources.py, другой парсер, нарезка или модель эмбеддингов) —
-- при следующем деплое корпус перезагружается или индекс пересчитывается автоматически.
CREATE TABLE rag_state (
    key         text        PRIMARY KEY,         -- corpus | index
    value       text        NOT NULL,            -- sha256 отпечаток
    detail      jsonb       NOT NULL DEFAULT '{}',
    updated_at  timestamptz NOT NULL DEFAULT now()
);
