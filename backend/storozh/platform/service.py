"""Вход через Telegram (UC-P1), сессии, профиль. Токены в базе — только хеши (NFR-P-02)."""

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from storozh.guard import public as guard
from storozh.platform import repo
from storozh.shared import audit, crypto, db
from storozh.shared.auth import token_hash
from storozh.shared.config import settings

LOGIN_TTL = timedelta(minutes=5)
SESSION_TTL = timedelta(hours=12)


class LoginError(Exception):
    """Ссылка устарела, уже использована или Telegram не привязан."""


def _now() -> datetime:
    return datetime.now(UTC)


def bot_link(payload: str) -> str:
    return f"https://t.me/{settings.telegram_bot_username or 'storozh_bot'}?start={payload}"


async def start_login() -> str:
    """Шаг 1: одноразовый nonce на 5 минут -> ссылка на бота."""
    nonce = secrets.token_urlsafe(24)
    async with db.connect("platform") as conn:
        await repo.create_nonce(conn, token_hash(nonce), _now() + LOGIN_TTL)
    return bot_link(f"login_{nonce}")


async def issue_login_link(nonce: str | None, citizen_id: UUID, chat_id: int | None = None) -> str:
    """Одноразовая ссылка /auth/callback для гражданина (nonce=None — служебный вход для демо из CLI)."""
    token = secrets.token_urlsafe(32)
    async with db.connect("platform") as conn:
        if nonce is None:
            nonce = secrets.token_urlsafe(24)
            await repo.create_nonce(conn, token_hash(nonce), _now() + LOGIN_TTL)
        chat_enc = crypto.encrypt(citizen_id, str(chat_id or 0).encode())
        if not await repo.bind_nonce(conn, token_hash(nonce), citizen_id, chat_enc, token_hash(token)):
            raise LoginError("login link expired or already used")
    return f"{settings.public_web_url}/api/auth/callback?token={token}"


async def bind_login(nonce: str, chat_id: int, display_name: str | None = None, lang: str = "uz") -> str:
    """Шаг 2 (бот): /start login_<nonce> -> гражданин по привязанному chat_id -> ссылка входа.

    Первый вход с нового Telegram: если регистрация через Telegram разрешена, заводим гражданина и привязываем чат
    (личность подтверждает сам Telegram). Иначе вход был бы возможен только после привязки, а привязка — только после входа.
    """
    citizen_id = await guard.citizen_by_chat(chat_id)
    if citizen_id is None:
        if not settings.telegram_signup:
            raise LoginError("telegram chat is not linked to a citizen")
        citizen_id = await register_telegram_citizen(chat_id, display_name or "Fuqaro", lang)
    return await issue_login_link(nonce, citizen_id, chat_id)


async def register_telegram_citizen(chat_id: int, display_name: str, lang: str) -> UUID:
    """Новый гражданин для Telegram-аккаунта. ПИНФЛ неизвестен: вместо него стабильный технический идентификатор чата."""
    import uuid

    citizen_id = uuid.uuid4()
    placeholder = f"tg:{chat_id}"
    async with db.connect("platform") as conn:
        await repo.upsert_citizen(conn, citizen_id, crypto.hmac_pinfl(placeholder),
                                  crypto.encrypt(citizen_id, placeholder.encode()), display_name[:80], lang)
        await audit.write(conn, actor=f"citizen:{citizen_id}", action="citizen.registered", target="telegram")
    await guard.link_chat_to_citizen(citizen_id, chat_id)
    return citizen_id


async def consume_login(token: str) -> str:
    """Шаг 3: одноразовый токен -> сессия на 12 часов. Возвращает токен сессии для cookie."""
    session = secrets.token_urlsafe(32)
    async with db.connect("platform") as conn:
        citizen_id = await repo.use_login_token(conn, token_hash(token))
        if citizen_id is None:
            raise LoginError("login link expired or already used")
        await repo.create_session(conn, citizen_id, token_hash(session), _now() + SESSION_TTL)
        await audit.write(conn, actor=f"citizen:{citizen_id}", action="login", target="web")
    return session


async def logout(session_token: str, citizen_id: UUID) -> None:
    async with db.connect("platform") as conn:
        await repo.revoke_session(conn, token_hash(session_token))
        await audit.write(conn, actor=f"citizen:{citizen_id}", action="logout", target="web")


async def profile(citizen_id: UUID) -> dict:
    async with db.connect("platform") as conn:
        row = await repo.get_citizen(conn, citizen_id)
    if row is None:
        return {"id": str(citizen_id), "display_name": "Fuqaro", "lang": "uz"}
    return {"id": str(row["id"]), "display_name": row["display_name"], "lang": row["lang"]}


async def seed_citizen(citizen_id: UUID, display_name: str, pinfl: str, lang: str) -> None:
    async with db.connect("platform") as conn:
        await repo.upsert_citizen(conn, citizen_id, crypto.hmac_pinfl(pinfl), crypto.encrypt(citizen_id, pinfl.encode()),
                                  display_name, lang)


async def citizen_profile(citizen_id: UUID) -> dict | None:
    """ФИО и ПИНФЛ для черновика заявления (только в PDF, в модель не уходят)."""
    async with db.connect("platform") as conn:
        row = await repo.get_citizen(conn, citizen_id)
    if row is None:
        return None
    pinfl = crypto.decrypt(citizen_id, row["pinfl_enc"]).decode() if row["pinfl_enc"] else None
    return {"display_name": row["display_name"], "lang": row["lang"], "pinfl": pinfl}


# --- T9: согласие на обработку и удаление данных (ЗРУ-547) ---------------------------------------------

CONSENT_VERSION = "2026-11-21"
CONSENT_SCOPES = ["read_cabinets", "store_encrypted", "notify_telegram", "ai_explanations"]


async def get_consent(citizen_id: UUID) -> dict:
    async with db.connect("platform") as conn:
        row = await repo.current_consent(conn, citizen_id)
    accepted = row is not None and row["version"] == CONSENT_VERSION
    return {"version": CONSENT_VERSION, "scopes": CONSENT_SCOPES, "accepted": accepted,
            "accepted_at": row["accepted_at"] if accepted else None}


async def accept_consent(citizen_id: UUID, version: str) -> dict:
    if version != CONSENT_VERSION:
        raise ValueError("consent version is outdated")
    async with db.connect("platform") as conn:
        row = await repo.add_consent(conn, citizen_id, version, CONSENT_SCOPES)
        await audit.write(conn, actor=f"citizen:{citizen_id}", action="consent.accepted",
                          target=f"consent:{version}")
    return {"version": row["version"], "scopes": list(row["scopes"]), "accepted": True,
            "accepted_at": row["accepted_at"]}


async def delete_my_data(citizen_id: UUID) -> None:
    """Криптоудаление: ключ данных стёрт, сессии и привязка Telegram сняты, согласие отозвано, факт — в аудите.

    Маски и HMAC в карточках остаются (персональных данных в них нет), всё зашифрованное — нечитаемо:
    сессии OneID, сырые данные источников, ПИНФЛ, chat_id, скриншоты, PDF-заявления.
    """
    await guard.forget_citizen(citizen_id)
    crypto.destroy_key(citizen_id)
    async with db.connect("platform") as conn:
        await repo.withdraw_consents(conn, citizen_id)
        await repo.revoke_all_sessions(conn, citizen_id)
        await audit.write(conn, actor=f"citizen:{citizen_id}", action="data.deleted", target=f"citizen:{citizen_id}")
