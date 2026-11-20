"""Конверт события и типы данных событий. Зеркало contracts/events/*.schema.json.

Версионирование: новое поле — можно в /v1; удалить или переименовать — только через /v2.
"""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

Producer = Literal["documents", "guard", "assistant", "platform"]

# topic -> версия схемы. Добавили событие — добавьте сюда и в contracts/events/.
TOPICS: dict[str, str] = {
    "document.created": "v1",
    "document.changed": "v1",
    "document.status_changed": "v1",
    "document.disappeared": "v1",
    "source.session_expired": "v1",
    "alert.created": "v1",
    "action.updated": "v1",
    "summary.ready": "v1",
}


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID = Field(default_factory=uuid4)
    type: str
    schema_: str = Field(alias="schema")
    producer: Producer
    subject: str  # URI документа, id тревоги или действия
    citizen_id: UUID
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    dedupe_key: str
    data: dict[str, Any]

    @classmethod
    def new(cls, type: str, *, producer: Producer, subject: str, citizen_id: UUID,
            dedupe_key: str, data: dict[str, Any]) -> "Event":
        if type not in TOPICS:
            raise ValueError(f"unknown event type {type!r}: add it to shared/events.py and contracts/events/")
        return cls(type=type, schema=f"{type}/{TOPICS[type]}", producer=producer, subject=subject,
                   citizen_id=citizen_id, dedupe_key=dedupe_key, data=data)

    def to_json(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)
