"""Шифрование персональных данных и подпись внутренних запросов (Разработчик 2).

Конвертное шифрование AES-256-GCM: у каждого гражданина свой ключ данных (DEK, platform.citizens.dek_enc),
зашифрованный мастер-ключом из окружения (settings.master_key). Удалили DEK — данные человека нечитаемы.
Шифруем: source_sessions.state_enc, document_versions.raw_enc, citizens.pinfl_enc, telegram_links.chat_id_enc,
actions.evidence_enc, drafts.pdf_enc.
"""

import hashlib
import hmac
import time
from uuid import UUID

from storozh.shared.config import settings

INTERNAL_WINDOW_S = 300


class BadSignature(Exception):
    pass


def encrypt(citizen_id: UUID, plaintext: bytes) -> bytes:
    """nonce || ciphertext || tag ключом данных гражданина."""
    raise NotImplementedError("shared.crypto.encrypt: Разработчик 2")


def decrypt(citizen_id: UUID, blob: bytes) -> bytes:
    raise NotImplementedError("shared.crypto.decrypt: Разработчик 2")


def _hmac_hex(key: str, data: bytes) -> str:
    return hmac.new(key.encode(), data, hashlib.sha256).hexdigest()


def hmac_pinfl(pinfl: str) -> str:
    """Поиск гражданина по ПИНФЛ без хранения ПИНФЛ в открытом виде (отдельный ключ)."""
    return _hmac_hex(settings.pinfl_hmac_key, pinfl.strip().encode())


def sign_internal(body: bytes, ts: int) -> str:
    """Подпись внутреннего запроса: заголовки X-Signature и X-Timestamp."""
    return _hmac_hex(settings.ingest_hmac_key, f"{ts}.".encode() + body)


def verify_internal(body: bytes, ts: int, signature: str, now: float | None = None) -> None:
    """Бросает BadSignature, если подпись неверна или метка вне окна 5 минут."""
    now = time.time() if now is None else now
    if abs(now - ts) > INTERNAL_WINDOW_S:
        raise BadSignature("timestamp outside window")
    if not hmac.compare_digest(sign_internal(body, ts), signature):
        raise BadSignature("bad signature")
