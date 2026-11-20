"""Версии и события: что произошло с документом при новом снимке."""

from dataclasses import dataclass, field
from typing import Any

from storozh.shared.contracts import NormalizedDocument
from storozh.shared.hashing import content_hash

DISAPPEAR_AFTER = 2  # полных снимков подряд без записи (UC-D4)
_IGNORED = {"source_ref.url"}  # не входит в хеш — не показываем в diff


def diff(old: dict[str, Any], new: dict[str, Any]) -> list[dict[str, Any]]:
    """[{field, from, to}] по плоским ключам, в алфавитном порядке (FR-D-10)."""
    a, b = flatten(old), flatten(new)
    return [
        {"field": k, "from": a.get(k), "to": b.get(k)}
        for k in sorted(a.keys() | b.keys())
        if k not in _IGNORED and a.get(k) != b.get(k)
    ]


def flatten(data: dict[str, Any]) -> dict[str, Any]:
    """{"object": {"label": "x"}} -> {"object.label": "x"}. Списки сравниваются целиком."""
    out: dict[str, Any] = {}

    def walk(v: Any, path: str) -> None:
        if isinstance(v, dict) and v:
            for k, sub in v.items():
                walk(sub, f"{path}.{k}" if path else k)
        else:
            out[path] = v

    walk(data, "")
    return out


@dataclass(frozen=True)
class Change:
    """Решение по одному документу снимка."""

    kind: str  # "created" | "changed" | "unchanged"
    content_hash: str
    payload: dict[str, Any]
    changed_fields: list[str] = field(default_factory=list)
    status_from: str | None = None
    status_to: str | None = None

    @property
    def status_changed(self) -> bool:
        return self.status_from is not None and self.status_from != self.status_to


def classify(doc: NormalizedDocument, prev_hash: str | None, prev_payload: dict[str, Any] | None) -> Change:
    payload = doc.model_dump(mode="json")
    h = content_hash(doc)
    if prev_hash is None:
        return Change("created", h, payload)
    if h == prev_hash:
        return Change("unchanged", h, payload)
    d = diff(prev_payload or {}, payload)
    prev_status = (prev_payload or {}).get("status")
    return Change("changed", h, payload, changed_fields=[x["field"] for x in d],
                  status_from=prev_status, status_to=payload["status"])
