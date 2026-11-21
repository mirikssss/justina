"""T9 (ЗРУ-547): согласие в журнале; «Удалить мои данные» — криптоудаление, выход, снятие Telegram."""

import uuid

import httpx
import pytest

from storozh.guard.public import citizen_by_chat
from storozh.main import app
from storozh.platform import service
from storozh.shared import crypto, db, ratelimit
from storozh.shared.auth import DEV_CITIZEN_ID
from tests.integration.conftest import requires_db

pytestmark = requires_db


async def test_consent_flow_via_api():
    ratelimit.window.reset()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://x") as cl:
        state = (await cl.get("/me/consent")).json()
        assert set(state) >= {"version", "scopes", "accepted"} and "read_cabinets" in state["scopes"]
        assert (await cl.post("/me/consent", json={"version": "1999-01-01"})).status_code == 409
        r = await cl.post("/me/consent", json={"version": state["version"]})
        assert r.status_code == 200 and r.json()["accepted"] is True
        assert (await cl.get("/me/consent")).json()["accepted"] is True
    async with db.connect("platform") as conn:
        cur = await conn.execute("SELECT action FROM shared.audit_log WHERE actor = %s ORDER BY seq DESC LIMIT 1",
                                 (f"citizen:{DEV_CITIZEN_ID}",))
        assert (await cur.fetchone())["action"] == "consent.accepted"


async def test_delete_my_data_makes_encrypted_data_unreadable():
    citizen, chat_id = uuid.uuid4(), int(uuid.uuid4().int % 10**9) + 1
    await service.seed_citizen(citizen, "Тест Т.", str(uuid.uuid4().int)[:14], "uz")
    await service.accept_consent(citizen, service.CONSENT_VERSION)
    secret = crypto.encrypt(citizen, b"oneid session state")
    async with db.connect("guard") as conn:
        await conn.execute("INSERT INTO telegram_links (citizen_id, chat_id_enc, chat_id_hmac) VALUES (%s, %s, %s)",
                           (citizen, crypto.encrypt(citizen, str(chat_id).encode()), crypto.hmac_chat_id(chat_id)))
    assert crypto.decrypt(citizen, secret) == b"oneid session state"

    await service.delete_my_data(citizen)

    crypto.forget_cached_keys()  # другой процесс (воркер) тоже не прочитает: ключа нет в базе
    with pytest.raises(crypto.CryptoError):
        crypto.decrypt(citizen, secret)
    assert await citizen_by_chat(chat_id) is None
    assert (await service.get_consent(citizen))["accepted"] is False
    async with db.connect("platform") as conn:
        cur = await conn.execute("SELECT action FROM shared.audit_log WHERE actor = %s ORDER BY seq DESC LIMIT 1",
                                 (f"citizen:{citizen}",))
        assert (await cur.fetchone())["action"] == "data.deleted"
