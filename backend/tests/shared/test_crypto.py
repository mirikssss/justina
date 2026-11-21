import pytest

from storozh.shared import crypto


def test_internal_signature_roundtrip():
    sig = crypto.sign_internal(b'{"a":1}', 1_000)
    crypto.verify_internal(b'{"a":1}', 1_000, sig, now=1_100)


def test_internal_signature_rejects_tamper_and_replay_window():
    sig = crypto.sign_internal(b"body", 1_000)
    with pytest.raises(crypto.BadSignature):
        crypto.verify_internal(b"other", 1_000, sig, now=1_000)
    with pytest.raises(crypto.BadSignature):
        crypto.verify_internal(b"body", 1_000, sig, now=1_000 + 301)


# --------------------------------------------------------------------------- конвертное шифрование

import base64  # noqa: E402
import os  # noqa: E402
import uuid  # noqa: E402

from storozh.shared.config import settings  # noqa: E402


@pytest.fixture
def keys(monkeypatch):
    """Мастер-ключ и хранилище DEK в памяти вместо shared.data_keys."""
    store: dict[uuid.UUID, bytes] = {}
    monkeypatch.setattr(settings, "master_key", base64.b64encode(os.urandom(32)).decode())
    monkeypatch.setattr(crypto, "_key_store", lambda cid, enc: store.setdefault(cid, enc))
    crypto.forget_cached_keys()
    yield store
    crypto.forget_cached_keys()


def test_envelope_roundtrip_and_isolation(keys):
    alice, bob = uuid.uuid4(), uuid.uuid4()
    blob = crypto.encrypt(alice, b"secret")
    assert crypto.decrypt(alice, blob) == b"secret"
    assert b"secret" not in blob
    assert crypto.encrypt(alice, b"secret") != blob  # новый nonce каждый раз
    with pytest.raises(crypto.CryptoError):
        crypto.decrypt(bob, blob)  # чужой гражданин не расшифрует


def test_tampered_blob_and_shredded_key(keys):
    cid = uuid.uuid4()
    blob = bytearray(crypto.encrypt(cid, b"data"))
    blob[-1] ^= 1
    with pytest.raises(crypto.CryptoError):
        crypto.decrypt(cid, bytes(blob))

    good = crypto.encrypt(cid, b"data")
    keys.pop(cid)  # удалили DEK — данные нечитаемы
    crypto.forget_cached_keys()
    with pytest.raises(crypto.CryptoError):
        crypto.decrypt(cid, good)


def test_missing_master_key(monkeypatch):
    monkeypatch.setattr(settings, "master_key", "")
    crypto.forget_cached_keys()
    with pytest.raises(crypto.CryptoError):
        crypto.encrypt(uuid.uuid4(), b"x")
