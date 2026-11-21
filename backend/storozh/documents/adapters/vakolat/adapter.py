"""vakolat.check — статус известных доверенностей по номеру в публичном реестре (FR-D-05). Второй источник правды.

Не ходит в кабинет и не использует сессию OneID: публичный JSON-запрос по каждому номеру. Берёт текущие доверенности
гражданина из базы и накладывает на их payload статус реестра. Так отзыв, не видный в «Мои заявки», попадает в ленту.
"""

import asyncio
import logging
from typing import Any

import httpx

from storozh.documents.adapters.db import repo
from storozh.documents.adapters.mygov_car_poa.adapter import status_of
from storozh.documents.adapters.vakolat import selectors as sel
from storozh.documents.ports import BrowserSession, RawRecord
from storozh.shared import db
from storozh.shared.contracts import NormalizedDocument

log = logging.getLogger(__name__)
REQUEST_GAP_S = 1.0  # лимит реестра неизвестен — не чаще запроса в секунду


def registry_status(body: dict[str, Any]) -> str:
    """Статус из ответа реестра -> наш статус или "unknown". Разбор по предположению (см. selectors.STATUS_KEYS)."""
    data = body.get("data", body)
    for key in sel.STATUS_KEYS:
        value = data.get(key) if isinstance(data, dict) else None
        if isinstance(value, dict):
            value = value.get("name") or value.get("uz") or value.get("ru") or value.get("code")
        if isinstance(value, str) and (s := status_of(value)) != "unknown":
            return s
    return "unknown"


class VakolatAdapter:
    source_id = "vakolat.check"
    title = "Vakolat.uz · проверка доверенностей"
    poll_interval_s = 300
    complete = False  # проверяем только известные номера, пропажа записи ничего не значит

    async def fetch(self, session: BrowserSession) -> list[RawRecord]:
        async with db.connect("documents") as conn:
            known = await repo.poa_for_registry_check(conn, session.citizen_id)
        out: list[RawRecord] = []
        async with httpx.AsyncClient(timeout=15, headers={"Accept": "application/json"}) as client:
            for row in known:
                number = (row["payload"].get("source_ref") or {}).get("external_id")
                if not number:
                    continue
                r = await client.get(sel.API_URL.format(number=number))
                body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
                if r.status_code == 422 and (body.get("status") or {}).get("code") == sel.NOT_FOUND_CODE:
                    continue  # номера нет в реестре: статус не меняем (возможно, это номер заявки, а не вакольата)
                r.raise_for_status()
                out.append(RawRecord(external_id=number, data={"payload": row["payload"], "registry": body}))
                await asyncio.sleep(REQUEST_GAP_S)
        return out

    def normalize(self, raw: RawRecord) -> NormalizedDocument:
        """Тот же документ, что уже в ленте, но со статусом реестра (unknown — статус не трогаем)."""
        payload = dict(raw.data["payload"])
        status = registry_status(raw.data["registry"])
        if status != "unknown":
            payload["status"] = status
        return NormalizedDocument.model_validate(payload)
