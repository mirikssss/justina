"""Репозиторий схемы guard (SQL). Все функции работают в транзакции вызывающего."""

from datetime import date
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection

from storozh.guard.domain.rules import AlertDraft

_ALERT_COLS = "id, document_id, rule_id, severity, title, explanation, verdict, status, buttons, created_at"
_SEVERITY_ORDER = "CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 ELSE 2 END"


async def insert_alert(conn: AsyncConnection, *, event_id: UUID, citizen_id: UUID, document_id: UUID | None,
                       draft: AlertDraft, explanation: str | None) -> UUID | None:
    """Новая тревога. None — такая уже есть (повтор события: FR-G-01, NFR-G-03)."""
    cur = await conn.execute(
        """INSERT INTO alerts (event_id, citizen_id, document_id, rule_id, rule_version, severity, title,
                               explanation, buttons)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (event_id, rule_id, citizen_id) DO NOTHING RETURNING id""",
        (event_id, citizen_id, document_id, draft.rule_id, draft.rule_version, str(draft.severity), draft.title,
         explanation, list(draft.buttons)),
    )
    row = await cur.fetchone()
    return row["id"] if row else None


async def list_alerts(conn: AsyncConnection, citizen_id: UUID, *, status: str | None, offset: int,
                      limit: int) -> list[dict[str, Any]]:
    cur = await conn.execute(
        f"""SELECT {_ALERT_COLS} FROM alerts
            WHERE citizen_id = %s AND (%s::text IS NULL OR status = %s)
            ORDER BY (status = 'closed'), {_SEVERITY_ORDER}, created_at DESC, id
            OFFSET %s LIMIT %s""",
        (citizen_id, status, status, offset, limit),
    )
    return await cur.fetchall()


async def document_alerts(conn: AsyncConnection, citizen_id: UUID, document_id: UUID) -> list[dict[str, Any]]:
    cur = await conn.execute(
        f"""SELECT {_ALERT_COLS} FROM alerts WHERE citizen_id = %s AND document_id = %s
            ORDER BY created_at DESC""",
        (citizen_id, document_id),
    )
    return await cur.fetchall()


async def set_verdict(conn: AsyncConnection, citizen_id: UUID, alert_id: UUID, verdict: str) -> dict | None:
    """«Это я» закрывает тревогу (UC-G2); «Это не я» — тревога остаётся открытой до действия (UC-G3)."""
    cur = await conn.execute(
        f"""UPDATE alerts SET verdict = %s, status = CASE WHEN %s = 'me' THEN 'closed' ELSE 'seen' END
            WHERE id = %s AND citizen_id = %s RETURNING {_ALERT_COLS}""",
        (verdict, verdict, alert_id, citizen_id),
    )
    return await cur.fetchone()


async def receive_alerts_grantees(conn: AsyncConnection, grantor_id: UUID) -> list[UUID]:
    """Родственники с активным согласием receive_alerts (G7)."""
    cur = await conn.execute(
        """SELECT DISTINCT grantee_id FROM consents
           WHERE grantor_id = %s AND revoked_at IS NULL AND 'receive_alerts' = ANY(scopes)""",
        (grantor_id,),
    )
    return [r["grantee_id"] for r in await cur.fetchall()]


async def upsert_poa_watch(conn: AsyncConnection, *, document_id: UUID, citizen_id: UUID,
                           valid_until: date | None, status: str) -> None:
    await conn.execute(
        """INSERT INTO poa_watch (document_id, citizen_id, valid_until, status) VALUES (%s, %s, %s, %s)
           ON CONFLICT (document_id) DO UPDATE
           SET valid_until = EXCLUDED.valid_until, status = EXCLUDED.status, updated_at = now()""",
        (document_id, citizen_id, valid_until, status),
    )


async def expiring_poas(conn: AsyncConnection, today: date, until: date) -> list[dict[str, Any]]:
    cur = await conn.execute(
        """SELECT document_id, citizen_id, valid_until FROM poa_watch
           WHERE status = 'active' AND valid_until BETWEEN %s AND %s""",
        (today, until),
    )
    return await cur.fetchall()
