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
