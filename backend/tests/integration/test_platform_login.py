"""Вход через Telegram целиком: start -> bind_login (бот) -> callback -> cookie -> /me; повтор ссылки отклонён."""

import uuid
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from storozh.main import app
from storozh.platform import public as platform
from storozh.platform import service
from storozh.shared import crypto, db
from storozh.shared.auth import SESSION_COOKIE
from storozh.shared.config import settings
from tests.integration.conftest import requires_db

pytestmark = requires_db


@pytest.fixture
def demo_env(monkeypatch):
    monkeypatch.setattr(settings, "env", "demo")  # без dev-фолбэка: только настоящая сессия
    crypto.forget_cached_keys()


async def _link_telegram(citizen_id: uuid.UUID, chat_id: int) -> None:
    async with db.connect("guard") as conn:
        await conn.execute(
            "INSERT INTO telegram_links (citizen_id, chat_id_enc, chat_id_hmac) VALUES (%s, %s, %s)",
            (citizen_id, crypto.encrypt(citizen_id, str(chat_id).encode()), crypto.hmac_chat_id(chat_id)),
        )


async def test_full_login_flow(demo_env):
    citizen, chat_id = uuid.uuid4(), int(uuid.uuid4().int % 10**9)
    pinfl = str(uuid.uuid4().int)[:14]
    await service.seed_citizen(citizen, "Тест Т.", pinfl, "ru")
    await _link_telegram(citizen, chat_id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://test") as client:
        deep_link = (await client.post("/auth/telegram/start")).json()["deep_link"]
        nonce = deep_link.split("start=login_")[1]

        login_url = await platform.bind_login(nonce, chat_id)          # это делает бот
        with pytest.raises(platform.LoginError):
            await platform.bind_login(nonce, chat_id)                  # nonce одноразовый
        token = parse_qs(urlsplit(login_url).query)["token"][0]

        r = await client.get("/auth/callback", params={"token": token})
        assert r.status_code == 302 and r.headers["location"] == "/documents"
        assert SESSION_COOKIE in r.cookies

        me = (await client.get("/me")).json()
        assert me == {"id": str(citizen), "display_name": "Тест Т.", "lang": "ru"}
        assert (await client.get("/audit")).json()["items"][0]["action"] == "login"

        client.cookies.clear()
        again = await client.get("/auth/callback", params={"token": token})
        assert again.headers["location"] == "/login?error=expired"     # повторное открытие ссылки
        assert (await client.get("/me")).status_code == 401

    assert (await platform.citizen_profile(citizen))["pinfl"] == pinfl


async def test_unlinked_chat_cannot_login_when_signup_disabled(demo_env, monkeypatch):
    monkeypatch.setattr(settings, "telegram_signup", False)
    nonce_link = await service.start_login()
    with pytest.raises(platform.LoginError):
        await platform.bind_login(nonce_link.split("login_")[1], int(uuid.uuid4().int % 10**9))


async def test_audit_verify_endpoint():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://test") as client:
        assert (await client.get("/audit/verify")).json() == {"ok": True, "broken_seq": None}


async def test_first_login_from_new_telegram_registers_citizen(demo_env):
    """Новый Telegram без привязки: бот заводит гражданина, привязывает чат и выдаёт ссылку входа; тот же чат — тот же гражданин."""
    from storozh.guard import public as guard

    chat_id = int(uuid.uuid4().int % 10**9)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://test") as client:
        nonce = (await client.post("/auth/telegram/start")).json()["deep_link"].split("start=login_")[1]
        url = await platform.bind_login(nonce, chat_id, "Иван Тестов", "ru")
        r = await client.get("/auth/callback", params={"token": parse_qs(urlsplit(url).query)["token"][0]})
        assert r.status_code == 302 and SESSION_COOKIE in r.cookies
        me = (await client.get("/me")).json()
        assert me["display_name"] == "Иван Тестов" and me["lang"] == "ru"
    first = await guard.citizen_by_chat(chat_id)
    nonce2 = (await service.start_login()).split("login_")[1]
    await platform.bind_login(nonce2, chat_id, "Иван Тестов", "ru")
    assert await guard.citizen_by_chat(chat_id) == first == uuid.UUID(me["id"])
