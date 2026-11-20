"""Сценарии «Документов»: приём снимков, версии, лента, источники, сессии. Снаружи — только через public.py."""

import base64
import hashlib
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from storozh.documents.adapters import ADAPTERS
from storozh.documents.adapters.db import repo
from storozh.documents.domain.versions import DISAPPEAR_AFTER, classify, diff
from storozh.documents.ports import BrowserSession
from storozh.shared import crypto, db, outbox
from storozh.shared.contracts import NormalizedDocument, SourceSnapshot

log = logging.getLogger(__name__)

REFRESH_CHANNEL = "storozh_refresh"  # collector слушает: {"citizen_id", "source"}
NEW_FOR = timedelta(hours=24)  # метка «новое» в ленте
SOURCE_TITLES = {a.source_id: a.title for a in ADAPTERS}
POLL_INTERVALS = {a.source_id: a.poll_interval_s for a in ADAPTERS}


class NotFound(Exception):
    pass


# --------------------------------------------------------------------------- ingestion (UC-D2..D4)

async def ingest_snapshot(snapshot: SourceSnapshot) -> dict[str, int]:
    """Снимок -> версии и события одной транзакцией (FR-D-07, FR-D-08). Возвращает {"new_versions": N}."""
    now = datetime.now(UTC)
    new_versions = 0
    async with db.connect("documents") as conn, conn.transaction():
        fresh = await repo.claim_snapshot(
            conn, snapshot_id=snapshot.snapshot_id, citizen_id=snapshot.citizen_id, source=snapshot.source,
            complete=snapshot.complete, documents_count=len(snapshot.documents), fetched_at=snapshot.fetched_at,
        )
        if not fresh:
            return {"new_versions": 0}

        for doc in snapshot.documents:
            new_versions += await _apply_document(conn, snapshot, doc, now)

        if snapshot.complete:
            present = [d.uri for d in snapshot.documents]
            for row in await repo.mark_missing(conn, citizen_id=snapshot.citizen_id, source=snapshot.source,
                                               present_uris=present):
                if row["missing_count"] == DISAPPEAR_AFTER:  # ровно один раз; статус не меняем
                    await outbox.publish(
                        conn, type="document.disappeared", subject=row["uri"], citizen_id=snapshot.citizen_id,
                        data={"document_id": str(row["id"]), "last_version_no": row["current_version"],
                              "missing_count": row["missing_count"]},
                        dedupe_key=f"{snapshot.citizen_id}:{row['uri']}:{snapshot.snapshot_id}:gone",
                    )

        await repo.source_poll_result(conn, citizen_id=snapshot.citizen_id, source=snapshot.source, ok=True)
    log.info("snapshot %s %s: %s docs, %s new versions", snapshot.source, snapshot.snapshot_id,
             len(snapshot.documents), new_versions)
    return {"new_versions": new_versions}


async def _apply_document(conn, snapshot: SourceSnapshot, doc: NormalizedDocument, now: datetime) -> int:
    # dedupe_key начинается с citizen_id: одну доверенность видят обе стороны, у каждой — своё событие
    citizen = snapshot.citizen_id
    current = await repo.lock_document(conn, citizen, doc.uri)
    change = classify(doc, current["content_hash"] if current else None, current["payload"] if current else None)

    if change.kind == "unchanged":
        await repo.touch_document(conn, current["id"], now)
        return 0

    if change.kind == "created":
        document_id = await repo.insert_document(conn, citizen_id=citizen, doc=change.payload, seen_at=now)
        await repo.insert_version(conn, document_id=document_id, version_no=1, content_hash=change.content_hash,
                                  payload=change.payload, snapshot_id=snapshot.snapshot_id,
                                  fetched_at=snapshot.fetched_at)
        await outbox.publish(
            conn, type="document.created", subject=doc.uri, citizen_id=citizen,
            data={"document_id": str(document_id), "version_no": 1, "kind": doc.kind.value,
                  "owner_role": doc.owner_role.value},
            dedupe_key=f"{citizen}:{doc.uri}:1:created",
        )
        return 1

    document_id, prev = current["id"], current["current_version"]
    version_no = prev + 1
    await repo.insert_version(conn, document_id=document_id, version_no=version_no, content_hash=change.content_hash,
                              payload=change.payload, snapshot_id=snapshot.snapshot_id, fetched_at=snapshot.fetched_at)
    await repo.bump_document(conn, document_id=document_id, version_no=version_no, doc=change.payload, seen_at=now)
    base = {"document_id": str(document_id), "version_no": version_no, "prev_version_no": prev,
            "changed_fields": change.changed_fields}
    await outbox.publish(conn, type="document.changed", subject=doc.uri, citizen_id=citizen, data=base,
                         dedupe_key=f"{citizen}:{doc.uri}:{version_no}:changed")
    if change.status_changed:
        await outbox.publish(
            conn, type="document.status_changed", subject=doc.uri, citizen_id=citizen,
            data={**base, "status_from": change.status_from, "status_to": change.status_to},
            dedupe_key=f"{citizen}:{doc.uri}:{version_no}:status",
        )
    return 1


async def record_poll_error(citizen_id: UUID, source: str, error: str) -> None:
    async with db.connect("documents") as conn:
        await repo.source_poll_result(conn, citizen_id=citizen_id, source=source, ok=False, error=error[:500])


# --------------------------------------------------------------------------- чтение (UC-D5, UC-D6)

def _encode_cursor(updated_at: datetime, doc_id: UUID) -> str:
    return base64.urlsafe_b64encode(f"{updated_at.isoformat()}|{doc_id}".encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    ts, doc_id = base64.urlsafe_b64decode(cursor.encode()).decode().split("|")
    return datetime.fromisoformat(ts), UUID(doc_id)


def _list_item(row: dict, now: datetime) -> dict[str, Any]:
    p = row["payload"]
    others = [x for x in p.get("parties", []) if x.get("role") != p.get("owner_role")]
    obj = p.get("object") or {}
    label = " · ".join(x for x in (obj.get("label"), obj.get("id_masked")) if x) or None
    return {
        "id": row["id"], "uri": row["uri"], "kind": row["kind"], "title": row["title"], "status": row["status"],
        "owner_role": row["owner_role"], "source": row["source"],
        "number_masked": (p.get("fields") or {}).get("number_masked"),
        "counterparty_masked": others[0]["name_masked"] if others else None,
        "object_label": label, "issued_at": p.get("issued_at"),
        "is_new": now - row["first_seen_at"] < NEW_FOR, "updated_at": row["updated_at"],
    }


async def list_documents(citizen_id: UUID, *, kind: str | None = None, status: str | None = None,
                         q: str | None = None, cursor: str | None = None, limit: int = 50) -> dict[str, Any]:
    async with db.connect("documents") as conn:
        rows = await repo.list_documents(conn, citizen_id=citizen_id, kind=kind, status=status, q=q,
                                         after=_decode_cursor(cursor) if cursor else None, limit=limit + 1)
    now = datetime.now(UTC)
    page = rows[:limit]
    next_cursor = _encode_cursor(page[-1]["updated_at"], page[-1]["id"]) if len(rows) > limit else None
    return {"items": [_list_item(r, now) for r in page], "next_cursor": next_cursor}


async def get_document_detail(document_id: UUID, citizen_id: UUID) -> dict[str, Any]:
    async with db.connect("documents") as conn:
        row = await repo.get_document(conn, document_id, citizen_id)
    if row is None:
        raise NotFound(document_id)
    return {**row["payload"], "id": row["id"], "current_version": row["current_version"],
            "versions_count": row["versions_count"], "first_seen_at": row["first_seen_at"],
            "last_seen_at": row["last_seen_at"]}


async def get_document(document_id: UUID) -> NormalizedDocument:
    """Для других контекстов (без проверки гражданина: они получают id из своих событий)."""
    async with db.connect("documents") as conn:
        row = await repo.get_document(conn, document_id)
    if row is None:
        raise NotFound(document_id)
    return NormalizedDocument.model_validate(row["payload"])


async def _versions(document_id: UUID, citizen_id: UUID) -> list[dict]:
    async with db.connect("documents") as conn:
        if await repo.get_document(conn, document_id, citizen_id) is None:
            raise NotFound(document_id)
        return await repo.list_versions(conn, document_id)


async def list_versions(document_id: UUID, citizen_id: UUID) -> list[dict[str, Any]]:
    rows = await _versions(document_id, citizen_id)  # новые сверху
    out = []
    for i, r in enumerate(rows):
        prev = rows[i + 1]["payload"] if i + 1 < len(rows) else None
        changed = [d["field"] for d in diff(prev, r["payload"])] if prev is not None else []
        out.append({"version_no": r["version_no"], "content_hash": r["content_hash"], "fetched_at": r["fetched_at"],
                    "changed_fields": changed})
    return out


async def version_diff(document_id: UUID, version_no: int, citizen_id: UUID) -> list[dict[str, Any]]:
    by_no = {r["version_no"]: r["payload"] for r in await _versions(document_id, citizen_id)}
    if version_no not in by_no:
        raise NotFound(version_no)
    return diff(by_no.get(version_no - 1, {}), by_no[version_no]) if version_no > 1 else []


async def list_sources(citizen_id: UUID) -> list[dict[str, Any]]:
    async with db.connect("documents") as conn:
        rows = {r["source_id"]: r for r in await repo.list_sources(conn, citizen_id)}
        session = await repo.session_status(conn, citizen_id)
    out = []
    for source_id, title in SOURCE_TITLES.items():
        r = rows.get(source_id)
        if r is None or not r["enabled"]:
            status = "disabled"
        elif session == "expired":
            status = "expired"
        elif r["last_error"]:
            status = "error"
        else:
            status = "ok"
        out.append({"source_id": source_id, "title": title, "status": status,
                    "last_poll_at": r["last_poll_at"] if r else None, "last_ok_at": r["last_ok_at"] if r else None,
                    "last_error": r["last_error"] if r else None, "poll_interval_s": POLL_INTERVALS[source_id]})
    return out


# --------------------------------------------------------------------------- обновить сейчас (UC-D7)

class TooSoon(Exception):
    pass


async def _notify_refresh(conn, citizen_id: UUID, source: str) -> None:
    await conn.execute("SELECT pg_notify(%s, %s)",
                       (REFRESH_CHANNEL, json.dumps({"citizen_id": str(citizen_id), "source": source})))


async def refresh_source(citizen_id: UUID, source: str, min_interval_s: int = 20) -> None:
    if source not in SOURCE_TITLES:
        raise NotFound(source)
    async with db.connect("documents") as conn:
        cur = await conn.execute(
            "SELECT last_poll_at FROM sources WHERE citizen_id = %s AND source_id = %s", (citizen_id, source)
        )
        row = await cur.fetchone()
        last = row["last_poll_at"] if row else None
        if last and datetime.now(UTC) - last < timedelta(seconds=min_interval_s):
            raise TooSoon(source)
        await _notify_refresh(conn, citizen_id, source)


async def request_refresh(document_id: UUID) -> None:
    async with db.connect("documents") as conn:
        cur = await conn.execute("SELECT citizen_id, source FROM documents WHERE id = %s", (document_id,))
        row = await cur.fetchone()
        if row is None:
            raise NotFound(document_id)
        await _notify_refresh(conn, row["citizen_id"], row["source"])


# --------------------------------------------------------------------------- сессии OneID (FR-D-01, FR-D-11)

def _lock_key(citizen_id: UUID, provider: str) -> int:
    """64-битный ключ advisory lock на аккаунт."""
    return int.from_bytes(hashlib.sha256(f"{citizen_id}:{provider}".encode()).digest()[:8], "big", signed=True)


async def save_session(citizen_id: UUID, storage_state: dict[str, Any], provider: str = "oneid",
                       expires_at: datetime | None = None) -> None:
    blob = crypto.encrypt(citizen_id, json.dumps(storage_state).encode())
    async with db.connect("documents") as conn, conn.transaction():
        await conn.execute(
            """INSERT INTO source_sessions (citizen_id, provider, state_enc, expires_at, status)
               VALUES (%s, %s, %s, %s, 'active')
               ON CONFLICT (citizen_id, provider) DO UPDATE
               SET state_enc = EXCLUDED.state_enc, expires_at = EXCLUDED.expires_at, status = 'active'""",
            (citizen_id, provider, blob, expires_at),
        )
        for source_id in SOURCE_TITLES:
            await conn.execute(
                """INSERT INTO sources (source_id, citizen_id, enabled) VALUES (%s, %s, true)
                   ON CONFLICT (citizen_id, source_id) DO UPDATE SET enabled = true, last_error = NULL""",
                (source_id, citizen_id),
            )


async def expire_session(citizen_id: UUID, provider: str = "oneid") -> None:
    """UC-D8: статус expired + source.session_expired. Опрос гражданина останавливается до нового connect."""
    now = datetime.now(UTC)
    async with db.connect("documents") as conn, conn.transaction():
        cur = await conn.execute(
            """UPDATE source_sessions SET status = 'expired' WHERE citizen_id = %s AND provider = %s
               AND status = 'active' RETURNING id""",
            (citizen_id, provider),
        )
        if await cur.fetchone() is None:
            return
        await outbox.publish(
            conn, type="source.session_expired", subject=f"session:{provider}", citizen_id=citizen_id,
            data={"source": "*", "provider": provider},
            dedupe_key=f"{citizen_id}:{provider}:{now.isoformat(timespec='seconds')}",
        )


async def active_citizens(provider: str = "oneid") -> list[UUID]:
    async with db.connect("documents") as conn:
        cur = await conn.execute(
            "SELECT citizen_id FROM source_sessions WHERE provider = %s AND status = 'active'", (provider,)
        )
        return [r["citizen_id"] for r in await cur.fetchall()]


class _SessionProvider:
    @asynccontextmanager
    async def get(self, citizen_id: UUID, provider: str = "oneid") -> AsyncIterator[BrowserSession]:
        """Держит pg_advisory_lock на отдельном соединении, пока сессия в работе (опрос или действие)."""
        p = await db.pool("documents")
        async with p.connection() as conn:
            await conn.execute("SELECT pg_advisory_lock(%s)", (_lock_key(citizen_id, provider),))
            await conn.commit()
            try:
                cur = await conn.execute(
                    "SELECT state_enc, status FROM source_sessions WHERE citizen_id = %s AND provider = %s",
                    (citizen_id, provider),
                )
                row = await cur.fetchone()
                await conn.commit()
                if row is None or row["status"] != "active":
                    raise NotFound(f"no active {provider} session for {citizen_id}")
                state = json.loads(crypto.decrypt(citizen_id, row["state_enc"]))
                yield BrowserSession(citizen_id=citizen_id, storage_state=state)
            finally:
                await conn.execute("SELECT pg_advisory_unlock(%s)", (_lock_key(citizen_id, provider),))
                await conn.commit()


def session_provider() -> _SessionProvider:
    return _SessionProvider()
