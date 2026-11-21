"""callback_data кнопок тревоги с HMAC-подписью (FR-G-05). Лимит Telegram — 64 байта, у нас ~41.

Формат: "<op>.<alert_id base64url>.<подпись base64url, 12 байт>". op: m — «Это я», n — «Это не я».
Подделка или чужая тревога -> None. Владельца чата сверяет сервис (проверка chat_id).
"""

import base64
import hashlib
import hmac
from uuid import UUID

from storozh.shared.config import settings

OPS = {"m": "me", "n": "not_me"}
_REV = {v: k for k, v in OPS.items()}


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _key() -> bytes:
    if not settings.callback_hmac_key:
        raise RuntimeError("CALLBACK_HMAC_KEY is not configured")
    return settings.callback_hmac_key.encode()


def _sig(op: str, alert_id: UUID) -> str:
    return _b64(hmac.new(_key(), f"cb:{op}:{alert_id}".encode(), hashlib.sha256).digest()[:12])


def sign(verdict: str, alert_id: UUID) -> str:
    op = _REV[verdict]
    return f"{op}.{_b64(alert_id.bytes)}.{_sig(op, alert_id)}"


def verify(data: str) -> tuple[str, UUID] | None:
    """(verdict, alert_id) или None, если данные подделаны или битые."""
    try:
        op, raw_id, sig = data.split(".")
        alert_id = UUID(bytes=_unb64(raw_id))
    except (ValueError, TypeError):
        return None
    if op not in OPS or not hmac.compare_digest(sig, _sig(op, alert_id)):
        return None
    return OPS[op], alert_id
