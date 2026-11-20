"""Шифрование персональных данных (Разработчик 3). Сигнатуры зафиксированы, реализация — TODO.

Конвертное шифрование AES-256-GCM: у каждого гражданина свой ключ данных (DEK), зашифрованный
мастер-ключом из окружения (settings.master_key). Удалили DEK — данные человека нечитаемы.
Шифруем: source_sessions.state_enc, document_versions.raw_enc, citizens.pinfl_enc, telegram_links.chat_id_enc.
"""

import hashlib
import hmac
from uuid import UUID

from storozh.shared.config import settings


async def encrypt(citizen_id: UUID, plaintext: bytes) -> bytes:
    """nonce || ciphertext || tag ключом данных гражданина."""
    raise NotImplementedError("shared/crypto: Разработчик 3")


async def decrypt(citizen_id: UUID, blob: bytes) -> bytes:
    raise NotImplementedError("shared/crypto: Разработчик 3")


def hmac_hex(key: str, value: str) -> str:
    return hmac.new(key.encode(), value.encode(), hashlib.sha256).hexdigest()


def pinfl_hash(pinfl: str) -> str:
    """Поиск гражданина по ПИНФЛ без хранения ПИНФЛ в открытом виде."""
    return hmac_hex(settings.pinfl_hmac_key, pinfl)


def verify_signature(key: str, body: bytes, signature: str) -> bool:
    expected = hmac.new(key.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
