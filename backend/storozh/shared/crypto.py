"""Шифрование персональных данных и подпись внутренних запросов (Разработчик 2).

Конвертное шифрование AES-256-GCM: у каждого гражданина свой ключ данных (DEK, platform.citizens.dek_enc),
зашифрованный мастер-ключом из окружения (settings.master_key). Удалили DEK — данные человека нечитаемы.
Шифруем: source_sessions.state_enc, document_versions.raw_enc, citizens.pinfl_enc, telegram_links.chat_id_enc,
actions.evidence_enc, drafts.pdf_enc.
"""

import base64
import hashlib
import hmac
import os
import threading
import time
from uuid import UUID

import psycopg
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from storozh.shared.config import settings

INTERNAL_WINDOW_S = 300
_VERSION = b"\x01"
_NONCE = 12


class BadSignature(Exception):
    pass


class CryptoError(Exception):
    """Нет мастер-ключа, ключ гражданина удалён или данные испорчены."""


# --------------------------------------------------------------------------- ключи


def _master() -> AESGCM:
    try:
        key = base64.b64decode(settings.master_key, validate=True)
    except ValueError as e:
        raise CryptoError("MASTER_KEY is not valid base64") from e
    if len(key) != 32:
        raise CryptoError("MASTER_KEY must be 32 bytes (base64); see .env.example")
    return AESGCM(key)


def _wrap(citizen_id: UUID, dek: bytes) -> bytes:
    nonce = os.urandom(_NONCE)
    return nonce + _master().encrypt(nonce, dek, b"dek:" + citizen_id.bytes)


def _unwrap(citizen_id: UUID, dek_enc: bytes) -> bytes:
    try:
        return _master().decrypt(dek_enc[:_NONCE], dek_enc[_NONCE:], b"dek:" + citizen_id.bytes)
    except InvalidTag as e:
        raise CryptoError("cannot unwrap data key: wrong MASTER_KEY?") from e


def _db_get_or_create(citizen_id: UUID, candidate_enc: bytes) -> bytes:
    """Хранилище DEK — shared.data_keys под ролью storozh_shared. Синхронно: encrypt/decrypt без соединения."""
    with psycopg.connect(settings.database_url, autocommit=True) as conn:
        conn.execute("SET ROLE storozh_shared")
        conn.execute(
            "INSERT INTO shared.data_keys (citizen_id, dek_enc) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (citizen_id, candidate_enc),
        )
        row = conn.execute("SELECT dek_enc FROM shared.data_keys WHERE citizen_id = %s", (citizen_id,)).fetchone()
    return bytes(row[0])


_key_store = _db_get_or_create  # тесты подменяют на словарь в памяти
_cache: dict[UUID, bytes] = {}
_lock = threading.Lock()


def _dek(citizen_id: UUID) -> bytes:
    with _lock:
        if citizen_id in _cache:
            return _cache[citizen_id]
    dek_enc = _key_store(citizen_id, _wrap(citizen_id, AESGCM.generate_key(bit_length=256)))
    dek = _unwrap(citizen_id, dek_enc)
    with _lock:
        _cache[citizen_id] = dek
    return dek


def forget_cached_keys() -> None:
    with _lock:
        _cache.clear()


# --------------------------------------------------------------------------- данные


def encrypt(citizen_id: UUID, plaintext: bytes) -> bytes:
    """version(1) || nonce(12) || ciphertext || tag ключом данных гражданина; citizen_id — в AAD."""
    nonce = os.urandom(_NONCE)
    return _VERSION + nonce + AESGCM(_dek(citizen_id)).encrypt(nonce, plaintext, citizen_id.bytes)


def decrypt(citizen_id: UUID, blob: bytes) -> bytes:
    blob = bytes(blob)
    if blob[:1] != _VERSION:
        raise CryptoError("unknown ciphertext version")
    nonce, body = blob[1:1 + _NONCE], blob[1 + _NONCE:]
    try:
        return AESGCM(_dek(citizen_id)).decrypt(nonce, body, citizen_id.bytes)
    except InvalidTag as e:
        raise CryptoError("ciphertext is corrupted or belongs to another citizen") from e


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
