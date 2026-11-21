"""Синхронизация документов с другим сервером (`documents sync`): локальный сборщик держит сессию человека, а сайт живёт на сервере.

Берём текущие версии документов из локальной базы и шлём на удалённый ingest теми же подписанными снимками, что и сборщик.
Сырые данные (ПИНФЛ, ФИО целиком) не отправляются: только нормализованные документы с масками.
Снимки неполные (complete=False): удалённый сервер не будет считать документ пропавшим, если мы что-то не прислали.
"""

import uuid
from datetime import UTC, datetime
from itertools import groupby
from operator import itemgetter
from uuid import UUID

import httpx

from storozh.documents.adapters.db import repo
from storozh.shared import crypto, db
from storozh.shared.contracts import NormalizedDocument, SourceSnapshot


def build_snapshots(rows: list[dict], remote_citizen: UUID) -> list[SourceSnapshot]:
    """Строки (source, payload) -> по одному неполному снимку на источник, гражданин — удалённый."""
    now = datetime.now(UTC)
    out = []
    for source, group in groupby(sorted(rows, key=itemgetter("source")), key=itemgetter("source")):
        docs = [NormalizedDocument.model_validate(r["payload"]) for r in group]
        out.append(SourceSnapshot(snapshot_id=uuid.uuid4(), citizen_id=remote_citizen, source=source, fetched_at=now,
                                  complete=False, documents=docs))
    return out


async def push_once(local_citizen: UUID, remote_citizen: UUID, url: str, key: str) -> dict[str, int]:
    async with db.connect("documents") as conn:
        rows = await repo.current_payloads(conn, local_citizen)
    result: dict[str, int] = {}
    async with httpx.AsyncClient(timeout=60) as client:
        for snap in build_snapshots(rows, remote_citizen):
            body = snap.model_dump_json().encode()
            ts = int(datetime.now(UTC).timestamp())
            sig = crypto._hmac_hex(key, f"{ts}.".encode() + body)  # та же подпись, что crypto.sign_internal, но ключ сервера
            r = await client.post(url.rstrip("/") + "/internal/ingest/snapshots", content=body, headers={
                "Content-Type": "application/json", "X-Timestamp": str(ts), "X-Signature": sig})
            r.raise_for_status()
            result[snap.source] = r.json().get("new_versions", 0)
    return result
