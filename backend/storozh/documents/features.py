"""Продуктовые функции поверх агрегации: сводка, «поделиться документом», доказательный пакет.

Сводка — только по данным самого человека. Ссылка «поделиться» открывает **замаскированный** документ (то же, что человек видит в ленте)
на 24 часа без входа, каждый просмотр считается. Доказательный пакет — PDF со всеми версиями документа и хешами: для банка, нотариуса, суда.
"""

import hashlib
import secrets
from datetime import UTC, date, datetime, timedelta
from html import escape
from typing import Any
from uuid import UUID

from storozh.documents import service
from storozh.documents.domain.versions import diff
from storozh.shared import audit, db
from storozh.shared.config import settings

SHARE_TTL = timedelta(hours=24)
EXPIRING_DAYS = 90
ATTENTION_DAYS = 30


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# --------------------------------------------------------------------------- сводка

def _attention(rows: list[dict[str, Any]], sources: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        until = date.fromisoformat(r["valid_until"]) if r["valid_until"] else None
        left = (until - today).days if until else None
        base = {"document_id": str(r["id"]), "title": r["title"]}
        if r["kind"] == "tax_assessment" and r["status"] == "active" and r["owner_role"] == "debtor":
            out.append({**base, "level": "high", "type": "tax_debt",
                        "text": "Есть налоговая задолженность или пеня", "text_uz": "Soliq qarzi yoki penya bor"})
        elif r["status"] == "expired" and r["kind"] == "identity_document":
            out.append({**base, "level": "high", "type": "expired_id",
                        "text": "Срок документа истёк: замените его", "text_uz": "Hujjat muddati tugagan: uni almashtiring"})
        elif r["status"] == "active" and left is not None and 0 <= left <= ATTENTION_DAYS:
            out.append({**base, "level": "medium", "type": "expiring", "days_left": left,
                        "text": f"Срок истекает через {left} дн.", "text_uz": f"Muddat {left} kundan so'ng tugaydi"})
        elif r["status"] == "revoked":
            out.append({**base, "level": "info", "type": "revoked",
                        "text": "Документ отозван", "text_uz": "Hujjat bekor qilingan"})
    bad = [s for s in sources if s["status"] in ("error", "expired")]
    if bad:
        out.append({"level": "medium", "type": "sources", "title": ", ".join(s["title"] for s in bad[:3]),
                    "text": "Источник недоступен или сессия истекла: данные могут устареть",
                    "text_uz": "Manba mavjud emas yoki sessiya tugagan: ma'lumotlar eskirishi mumkin"})
    order = {"high": 0, "medium": 1, "info": 2}
    return sorted(out, key=lambda a: order[a["level"]])


async def overview(citizen_id: UUID, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    async with db.connect("documents") as conn:
        cur = await conn.execute(
            """SELECT d.id, d.kind, d.title, d.status, d.owner_role, d.first_seen_at, d.updated_at, d.current_version,
                      v.payload->>'valid_until' AS valid_until
               FROM documents d JOIN document_versions v ON v.document_id = d.id AND v.version_no = d.current_version
               WHERE d.citizen_id = %s""", (citizen_id,))
        rows = await cur.fetchall()
    sources = await service.list_sources(citizen_id)
    by_kind: dict[str, int] = {}
    for r in rows:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
    week_ago = datetime.now(UTC) - timedelta(days=7)
    expiring = []
    for r in rows:
        if r["status"] == "active" and r["valid_until"]:
            left = (date.fromisoformat(r["valid_until"]) - today).days
            if 0 <= left <= EXPIRING_DAYS:
                expiring.append({"id": str(r["id"]), "title": r["title"], "kind": r["kind"],
                                 "valid_until": r["valid_until"], "days_left": left})
    recent = sorted((r for r in rows if r["current_version"] > 1), key=lambda r: r["updated_at"], reverse=True)[:5]
    counts = {"ok": 0, "error": 0, "expired": 0, "disabled": 0}
    for s in sources:
        counts[s["status"]] = counts.get(s["status"], 0) + 1
    return {
        "total": len(rows),
        "by_kind": sorted(({"kind": k, "count": n} for k, n in by_kind.items()), key=lambda x: -x["count"]),
        "new_7d": sum(1 for r in rows if r["first_seen_at"] >= week_ago),
        "expiring": sorted(expiring, key=lambda e: e["days_left"]),
        "attention": _attention(rows, sources, today),
        "recent_changes": [{"id": str(r["id"]), "title": r["title"], "kind": r["kind"], "status": r["status"],
                            "version": r["current_version"], "updated_at": r["updated_at"].isoformat()} for r in recent],
        "sources": counts,
    }


# --------------------------------------------------------------------------- поделиться документом

async def create_share(citizen_id: UUID, document_id: UUID) -> dict[str, Any]:
    async with db.connect("documents") as conn, conn.transaction():
        cur = await conn.execute("SELECT id FROM documents WHERE id = %s AND citizen_id = %s", (document_id, citizen_id))
        if await cur.fetchone() is None:
            raise service.NotFound(document_id)
        token = secrets.token_urlsafe(24)
        expires = datetime.now(UTC) + SHARE_TTL
        cur = await conn.execute(
            "INSERT INTO shares (citizen_id, document_id, token_hash, expires_at) VALUES (%s, %s, %s, %s) RETURNING id",
            (citizen_id, document_id, _hash(token), expires))
        share_id = (await cur.fetchone())["id"]
        await audit.write(conn, actor=f"citizen:{citizen_id}", action="document.shared", target=f"share:{share_id}")
    return {"share_id": str(share_id), "url": f"{settings.public_web_url.rstrip('/')}/s/{token}",
            "expires_at": expires.isoformat()}


async def list_shares(citizen_id: UUID, document_id: UUID) -> list[dict[str, Any]]:
    async with db.connect("documents") as conn:
        cur = await conn.execute(
            """SELECT id, created_at, expires_at, revoked_at, views, last_view_at FROM shares
               WHERE citizen_id = %s AND document_id = %s ORDER BY created_at DESC LIMIT 20""", (citizen_id, document_id))
        rows = await cur.fetchall()
    now = datetime.now(UTC)
    return [{"share_id": str(r["id"]), "created_at": r["created_at"].isoformat(), "expires_at": r["expires_at"].isoformat(),
             "active": r["revoked_at"] is None and r["expires_at"] > now, "views": r["views"],
             "last_view_at": r["last_view_at"].isoformat() if r["last_view_at"] else None} for r in rows]


async def revoke_share(citizen_id: UUID, share_id: UUID) -> bool:
    async with db.connect("documents") as conn, conn.transaction():
        cur = await conn.execute(
            "UPDATE shares SET revoked_at = now() WHERE id = %s AND citizen_id = %s AND revoked_at IS NULL RETURNING id",
            (share_id, citizen_id))
        if await cur.fetchone() is None:
            return False
        await audit.write(conn, actor=f"citizen:{citizen_id}", action="document.share_revoked", target=f"share:{share_id}")
    return True


async def open_share(token: str) -> dict[str, Any] | None:
    """Публичный просмотр: замаскированный документ + срок ссылки. None — нет такой, просрочена или отозвана."""
    async with db.connect("documents") as conn, conn.transaction():
        cur = await conn.execute(
            """SELECT s.id, s.expires_at, d.id AS document_id, d.current_version, v.payload,
                      (SELECT count(*) FROM document_versions x WHERE x.document_id = d.id)::int AS versions_count
               FROM shares s JOIN documents d ON d.id = s.document_id
               JOIN document_versions v ON v.document_id = d.id AND v.version_no = d.current_version
               WHERE s.token_hash = %s AND s.revoked_at IS NULL AND s.expires_at > now() FOR UPDATE OF s""", (_hash(token),))
        row = await cur.fetchone()
        if row is None:
            return None
        await conn.execute("UPDATE shares SET views = views + 1, last_view_at = now() WHERE id = %s", (row["id"],))
        await conn.execute("INSERT INTO share_views (share_id) VALUES (%s)", (row["id"],))
    payload = {k: v for k, v in row["payload"].items() if k != "source_ref"}
    return {"document": payload, "versions_count": row["versions_count"], "shared_until": row["expires_at"].isoformat(),
            "note": "Данные показаны с масками, как в кабинете владельца. Ссылка временная."}


# --------------------------------------------------------------------------- доказательный пакет

def evidence_html(doc: dict[str, Any], versions: list[dict[str, Any]], diffs: dict[int, list[dict[str, Any]]],
                  generated: datetime) -> str:
    e = escape
    rows = "".join(
        f"<tr><td>{v['version_no']}</td><td>{e(str(v['fetched_at'])[:19])}</td><td class='h'>{e(v['content_hash'])}</td>"
        f"<td>{e(', '.join(v.get('changed_fields') or []) or '—')}</td></tr>" for v in sorted(versions, key=lambda v: v["version_no"]))
    changes = "".join(
        f"<h3>Версия {n}</h3><ul>" + "".join(f"<li><b>{e(x['field'])}</b>: {e(str(x['from']))} → {e(str(x['to']))}</li>" for x in d) + "</ul>"
        for n, d in sorted(diffs.items()) if d)
    return f"""<!doctype html><html lang="ru"><meta charset="utf-8"><style>
body{{font-family:'DejaVu Sans',sans-serif;font-size:11pt;color:#111}} h1{{font-size:18pt}} h2{{font-size:13pt;margin-top:18pt}}
table{{border-collapse:collapse;width:100%}} td,th{{border:1px solid #999;padding:4pt 6pt;font-size:9pt;vertical-align:top}}
.h{{font-family:monospace;font-size:7pt;word-break:break-all}} .muted{{color:#555;font-size:9pt}}</style>
<h1>Доказательный пакет</h1>
<p class="muted">Сформирован {e(generated.strftime('%d.%m.%Y %H:%M UTC'))} системой «Justina» (Сторож сделок). Данные получены из кабинета владельца;
персональные данные в пакете показаны масками.</p>
<h2>Документ</h2>
<table><tr><th>Название</th><td>{e(doc['title'])}</td></tr><tr><th>Идентификатор (URI)</th><td>{e(doc['uri'])}</td></tr>
<tr><th>Вид</th><td>{e(doc['kind'])}</td></tr><tr><th>Источник</th><td>{e(doc['source'])}</td></tr>
<tr><th>Статус сейчас</th><td>{e(doc['status'])}</td></tr><tr><th>Выдан</th><td>{e(str(doc.get('issued_at') or '—'))}</td></tr>
<tr><th>Действует до</th><td>{e(str(doc.get('valid_until') or '—'))}</td></tr>
<tr><th>Впервые обнаружен системой</th><td>{e(str(doc.get('first_seen_at', ''))[:19])}</td></tr></table>
<h2>История версий</h2>
<table><tr><th>№</th><th>Получена из источника</th><th>Хеш содержимого (SHA-256)</th><th>Что изменилось</th></tr>{rows}</table>
<h2>Что именно менялось</h2>{changes or '<p>Изменений после первой версии не было.</p>'}
<h2>Как проверить</h2>
<p class="muted">Каждая версия хранится в базе без права изменения и удаления (только добавление). Хеш считается от нормализованного
содержимого версии, поэтому любое расхождение с источником видно по хешу. Записи журнала аудита связаны цепочкой хешей.</p></html>"""


async def evidence_pdf(citizen_id: UUID, document_id: UUID) -> bytes:
    doc = await service.get_document_detail(document_id, citizen_id)
    versions = await service.list_versions(document_id, citizen_id)
    diffs = {}
    for v in versions:
        if v["version_no"] > 1:
            diffs[v["version_no"]] = await service.version_diff(document_id, v["version_no"], citizen_id)
    html = evidence_html(doc, versions, diffs, datetime.now(UTC))
    from weasyprint import HTML  # тяжёлый импорт — только когда нужен PDF

    return HTML(string=html).write_pdf()


__all__ = ["diff"]
