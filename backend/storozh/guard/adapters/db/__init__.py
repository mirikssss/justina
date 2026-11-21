"""Репозиторий схемы guard (SQL). Все функции работают в транзакции вызывающего."""

from datetime import date
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

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


# --- действия ---------------------------------------------------------------------------------------

_ACTION_FIELDS = {"confirm_code_hash", "confirm_expires_at", "attempts", "submitted_at", "evidence_enc", "result"}


async def get_action(conn: AsyncConnection, action_id: UUID, citizen_id: UUID | None = None, *,
                     for_update: bool = False) -> dict[str, Any] | None:
    cur = await conn.execute(
        "SELECT * FROM actions WHERE id = %s AND (%s::uuid IS NULL OR citizen_id = %s)"
        + (" FOR UPDATE" if for_update else ""),
        (action_id, citizen_id, citizen_id),
    )
    return await cur.fetchone()


async def action_by_key(conn: AsyncConnection, idempotency_key: str) -> dict[str, Any] | None:
    cur = await conn.execute("SELECT * FROM actions WHERE idempotency_key = %s", (idempotency_key,))
    return await cur.fetchone()


async def open_action(conn: AsyncConnection, document_id: UUID, type: str) -> dict[str, Any] | None:
    cur = await conn.execute(
        "SELECT * FROM actions WHERE document_id = %s AND type = %s AND status NOT IN ('done', 'failed', 'expired')",
        (document_id, type),
    )
    return await cur.fetchone()


async def insert_action(conn: AsyncConnection, *, citizen_id: UUID, alert_id: UUID | None, document_id: UUID,
                        type: str, idempotency_key: str) -> dict[str, Any] | None:
    """None — гонка: такой ключ или открытое действие по документу уже вставил параллельный запрос."""
    cur = await conn.execute(
        """INSERT INTO actions (citizen_id, alert_id, document_id, type, idempotency_key)
           VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING *""",
        (citizen_id, alert_id, document_id, type, idempotency_key),
    )
    return await cur.fetchone()


async def update_action(conn: AsyncConnection, action_id: UUID, *, expect_status: str, status: str | None = None,
                        **fields: Any) -> dict[str, Any] | None:
    """Оптимистичная запись: None, если статус уже сменил кто-то другой."""
    bad = set(fields) - _ACTION_FIELDS
    if bad:
        raise ValueError(f"unknown action fields {bad}")
    sets = ["updated_at = now()"] + [f"{k} = %s" for k in fields]
    params: list[Any] = [Jsonb(v) if k == "result" and v is not None else v for k, v in fields.items()]
    if status is not None:
        sets.append("status = %s")
        params.append(status)
    cur = await conn.execute(
        f"UPDATE actions SET {', '.join(sets)} WHERE id = %s AND status = %s RETURNING *",
        (*params, action_id, expect_status),
    )
    return await cur.fetchone()


async def add_step(conn: AsyncConnection, action_id: UUID, status: str) -> None:
    await conn.execute("INSERT INTO action_steps (action_id, status) VALUES (%s, %s)", (action_id, status))


async def action_steps(conn: AsyncConnection, action_id: UUID) -> list[dict[str, Any]]:
    cur = await conn.execute("SELECT status, at FROM action_steps WHERE action_id = %s ORDER BY id", (action_id,))
    return await cur.fetchall()


async def claim_action(conn: AsyncConnection, status: str, *, older_than_s: float = 0) -> dict[str, Any] | None:
    """Одно действие в статусе для воркера; SKIP LOCKED — два воркера не возьмут одно и то же."""
    cur = await conn.execute(
        """SELECT * FROM actions WHERE status = %s AND updated_at <= now() - make_interval(secs => %s)
           ORDER BY updated_at LIMIT 1 FOR UPDATE SKIP LOCKED""",
        (status, older_than_s),
    )
    return await cur.fetchone()


async def claim_expired_codes(conn: AsyncConnection) -> list[dict[str, Any]]:
    cur = await conn.execute(
        """SELECT * FROM actions WHERE status = 'awaiting_confirmation' AND confirm_expires_at <= now()
           FOR UPDATE SKIP LOCKED""")
    return await cur.fetchall()


async def verifying_actions(conn: AsyncConnection, document_id: UUID) -> list[dict[str, Any]]:
    cur = await conn.execute("SELECT * FROM actions WHERE document_id = %s AND status = 'verifying' FOR UPDATE",
                             (document_id,))
    return await cur.fetchall()


async def get_poa_watch(conn: AsyncConnection, document_id: UUID) -> dict[str, Any] | None:
    cur = await conn.execute("SELECT * FROM poa_watch WHERE document_id = %s", (document_id,))
    return await cur.fetchone()


async def latest_alert_id(conn: AsyncConnection, citizen_id: UUID, document_id: UUID) -> UUID | None:
    cur = await conn.execute(
        """SELECT id FROM alerts WHERE citizen_id = %s AND document_id = %s
           ORDER BY (rule_id = 'G1') DESC, created_at DESC LIMIT 1""",
        (citizen_id, document_id),
    )
    row = await cur.fetchone()
    return row["id"] if row else None


async def has_telegram_link(conn: AsyncConnection, citizen_id: UUID) -> bool:
    cur = await conn.execute("SELECT 1 FROM telegram_links WHERE citizen_id = %s", (citizen_id,))
    return await cur.fetchone() is not None
