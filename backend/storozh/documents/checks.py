"""Проверка перед сделкой (покупатель) и кабинет нотариуса: один движок, `POST /v1/checks` (00-project-overview, «API сторожа»).

Что проверяем сегодня на реальных данных:
- Vakolat.uz по номеру доверенности (публичный реестр): есть ли, какой статус;
- наши документы: если доверенность есть у кого-то из пользователей Justina, берём её статус и дату выдачи (только статус и дату);
- правила R3 (продаёт представитель), R4 (доверенность моложе 30 дней), R8 (владельцу 70+).
Чего у нас нет и что честно возвращается в `not_checked`: запрет на объект (R1), режим «только лично» (R2), наследство (R5),
перепродажа (R6), цена и эскроу (R7). ИИ решения не принимает: уровень риска считают только правила.
"""

import asyncio
import json
import re
import time
import uuid
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

import httpx
from pydantic import BaseModel, Field

from storozh.documents.adapters.vakolat import selectors as vk_sel
from storozh.documents.adapters.vakolat.adapter import registry_status
from storozh.shared import db
from storozh.shared.logging import mask

LEVELS = ["low", "medium", "high", "block"]
YOUNG_POA_DAYS = 30
OLD_AGE = 70
VAKOLAT_TIMEOUT_S = 8
VAKOLAT_GAP_S = 1.0  # лимит реестра неизвестен — не чаще запроса в секунду

NOT_CHECKED = [
    {"rule": "R1", "text": "Запрет на объект: нет источника (банк запретов, запрос по кадастровому номеру)",
     "text_uz": "Obyektdagi taqiq: manba yo'q (taqiqlar banki, kadastr raqami bo'yicha so'rov)"},
    {"rule": "R2", "text": "Режим «только лично»: появится вместе с Notarius", "text_uz": "«Faqat shaxsan» rejimi: Notarius bilan birga paydo bo'ladi"},
    {"rule": "R5", "text": "Наследство продавца: нет источника", "text_uz": "Sotuvchining merosi: manba yo'q"},
    {"rule": "R6", "text": "Перепродажа менее чем через 90 дней: нет истории объекта", "text_uz": "90 kundan kam vaqtda qayta sotish: obyekt tarixi yo'q"},
    {"rule": "R7", "text": "Цена и эскроу: данные сделки недоступны", "text_uz": "Narx va eskrou: bitim ma'lumotlari mavjud emas"},
]


class CheckRequest(BaseModel):
    poa_number: str = Field(min_length=3, max_length=40, pattern=r"^[\w\-./]+$")
    acts_by_poa: bool = True  # продаёт представитель по доверенности
    poa_issued_at: date | None = None
    seller_age: int | None = Field(default=None, ge=0, le=130)
    cadastre_number: str | None = Field(default=None, max_length=40)


_gap_lock = asyncio.Lock()
_last_call = 0.0


def _flatten(value: Any, prefix: str = "", out: dict[str, str] | None = None) -> dict[str, str]:
    """Ответ реестра -> плоский словарь для показа. Значения проходят через маску ПИНФЛ и телефонов."""
    out = {} if out is None else out
    if len(out) >= 25:
        return out
    if isinstance(value, dict):
        for k, v in value.items():
            _flatten(v, f"{prefix}.{k}" if prefix else str(k), out)
    elif isinstance(value, list):
        for i, v in enumerate(value[:5]):
            _flatten(v, f"{prefix}[{i}]", out)
    elif value not in (None, ""):
        out[prefix] = mask(str(value))[:200]
    return out


async def vakolat_lookup(number: str, client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    """{found, status, fields, unavailable}. Реестр недоступен — unavailable=True (это не «не найдено»)."""
    global _last_call
    async with _gap_lock:
        wait = VAKOLAT_GAP_S - (time.monotonic() - _last_call)
        if wait > 0:
            await asyncio.sleep(wait)
        _last_call = time.monotonic()
    own = client is None
    client = client or httpx.AsyncClient(timeout=VAKOLAT_TIMEOUT_S, headers={"Accept": "application/json"})
    try:
        digits = re.sub(r"[\s\-./]", "", number)  # с дефисами реестр отвечает 500, номера у него без разделителей
        r = await client.get(vk_sel.API_URL.format(number=digits))
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if r.status_code == 422 and (body.get("status") or {}).get("code") == vk_sel.NOT_FOUND_CODE:
            return {"found": False, "status": "unknown", "fields": {}, "unavailable": False}
        if r.status_code >= 400:
            return {"found": False, "status": "unknown", "fields": {}, "unavailable": True}
        data = body.get("data", body)
        valid = data.get("isValid") if isinstance(data, dict) else None
        if isinstance(valid, bool):  # реальный формат ответа: {"data": {"isValid": true|false}} (снято с живого реестра)
            return {"found": valid, "status": "active" if valid else "unknown", "fields": _flatten(data),
                    "unavailable": False}
        return {"found": True, "status": registry_status(body), "fields": _flatten(data), "unavailable": False}
    except (httpx.HTTPError, ValueError):
        return {"found": False, "status": "unknown", "fields": {}, "unavailable": True}
    finally:
        if own:
            await client.aclose()


async def own_poa(number: str) -> dict[str, Any] | None:
    """Доверенность в наших данных (любой гражданин Justina): только статус и дата выдачи, без личных данных."""
    async with db.connect("documents") as conn:
        cur = await conn.execute(
            """SELECT d.status, v.payload->>'issued_at' AS issued_at
               FROM documents d JOIN document_versions v ON v.document_id = d.id AND v.version_no = d.current_version
               WHERE d.uri = %s""",
            (f"uz:notarius:poa:{number}",),
        )
        rows = await cur.fetchall()
    if not rows:
        return None
    statuses = {r["status"] for r in rows}
    status = "revoked" if "revoked" in statuses else "expired" if "expired" in statuses else rows[0]["status"]
    issued = next((r["issued_at"] for r in rows if r["issued_at"]), None)
    return {"status": status, "issued_at": date.fromisoformat(issued) if issued else None, "holders": len(rows)}


def _reason(rule: str, level: str, text: str, text_uz: str) -> dict[str, str]:
    return {"rule": rule, "level": level, "text": text, "text_uz": text_uz}


def evaluate(req: CheckRequest, registry: dict[str, Any], own: dict[str, Any] | None, today: date) -> dict[str, Any]:
    """Чистая функция: правила -> уровень риска. Решение принимают только правила, ИИ не участвует."""
    reasons: list[dict[str, str]] = []
    consent_required = False
    status = registry["status"] if registry["found"] and registry["status"] != "unknown" else (own or {}).get("status")

    if registry["unavailable"]:
        reasons.append(_reason("REG", "medium", "Реестр Vakolat сейчас недоступен: проверка по реестру не выполнена",
                               "Vakolat reyestri hozir mavjud emas: reyestr bo'yicha tekshiruv bajarilmadi"))
    elif not registry["found"] and own is None:
        reasons.append(_reason("REG", "high", "Реестр Vakolat не подтверждает доверенность (не найдена или недействительна). Если она бумажная "
                               "или нотариальная, проверьте её у нотариуса",
                               "Vakolat reyestri ishonchnomani tasdiqlamaydi (topilmadi yoki yaroqsiz). Qog'oz yoki notarial bo'lsa, notariusda tekshiring"))
    if status == "revoked":
        reasons.append(_reason("REV", "block", "Доверенность отозвана: сделку по ней проводить нельзя",
                               "Ishonchnoma bekor qilingan: u bo'yicha bitim tuzish mumkin emas"))
    elif status == "expired":
        reasons.append(_reason("EXP", "block", "Срок доверенности истёк", "Ishonchnoma muddati tugagan"))
    if own is not None and own["status"] == "revoked":
        reasons.append(_reason("OWN", "block", "Доверитель уже отозвал доверенность в Justina",
                               "Ishonch bildiruvchi ishonchnomani Justina'da allaqachon bekor qilgan"))
    if req.acts_by_poa:
        consent_required = True
        reasons.append(_reason("R3", "medium", "Продаёт представитель: нужно подтверждение доверителя через MyID",
                               "Vakil sotmoqda: ishonch bildiruvchining MyID orqali tasdig'i kerak"))
    issued = req.poa_issued_at or (own or {}).get("issued_at")
    if issued is not None and (today - issued).days < YOUNG_POA_DAYS:
        reasons.append(_reason("R4", "high", f"Доверенность выдана меньше {YOUNG_POA_DAYS} дней назад ({issued.isoformat()})",
                               f"Ishonchnoma {YOUNG_POA_DAYS} kundan kam avval berilgan ({issued.isoformat()})"))
    if req.seller_age is not None and req.seller_age >= OLD_AGE:
        reasons.append(_reason("R8", "medium", f"Владельцу {OLD_AGE} лет или больше: уведомить родственников из режима «семья»",
                               f"Egasi {OLD_AGE} yosh yoki undan katta: «oila» rejimidagi qarindoshlarni xabardor qiling"))
    level = max((r["level"] for r in reasons), key=LEVELS.index, default="low")
    return {"risk_level": level, "reasons": reasons, "consent_required": consent_required, "not_checked": NOT_CHECKED,
            "registry": {"found": registry["found"], "status": registry["status"], "fields": registry["fields"],
                         "unavailable": registry["unavailable"]},
            "known_in_justina": own is not None, "checked_at": datetime.now(UTC).isoformat(timespec="seconds")}


def _status_for(result: dict[str, Any]) -> str:
    if result["risk_level"] == "block":
        return "denied"
    return "pending" if result["consent_required"] else "approved"


async def run_check(citizen_id: UUID, req: CheckRequest) -> dict[str, Any]:
    registry, own = await asyncio.gather(vakolat_lookup(req.poa_number), own_poa(req.poa_number))
    result = evaluate(req, registry, own, date.today())
    status = _status_for(result)
    check_id = uuid.uuid4()
    async with db.connect("documents") as conn:
        await conn.execute(
            "INSERT INTO checks (id, citizen_id, request, result, status) VALUES (%s, %s, %s, %s, %s)",
            (check_id, citizen_id, json.dumps(req.model_dump(mode="json")), json.dumps(result), status),
        )
    return {"check_id": str(check_id), "status": status, **result}


async def get_check(citizen_id: UUID, check_id: UUID) -> dict[str, Any] | None:
    async with db.connect("documents") as conn:
        cur = await conn.execute(
            "SELECT id, result, status, created_at, expires_at FROM checks WHERE id = %s AND citizen_id = %s",
            (check_id, citizen_id))
        row = await cur.fetchone()
    if row is None:
        return None
    status = "expired" if row["expires_at"] < datetime.now(UTC) and row["status"] == "pending" else row["status"]
    return {"check_id": str(row["id"]), "status": status, **row["result"]}


async def document_stats() -> dict[str, Any]:
    """Панель рисков: обезличенные агрегаты по документам всех граждан (виды, статусы). Личных данных нет."""
    async with db.connect("documents") as conn:
        cur = await conn.execute("SELECT kind, status, count(*)::int AS n FROM documents GROUP BY kind, status ORDER BY n DESC")
        rows = await cur.fetchall()
        cur = await conn.execute("SELECT count(DISTINCT citizen_id)::int AS citizens, count(*)::int AS documents FROM documents")
        total = await cur.fetchone()
    return {"citizens": total["citizens"], "documents": total["documents"],
            "by_kind_status": [{"kind": r["kind"], "status": r["status"], "count": r["n"]} for r in rows],
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds")}
