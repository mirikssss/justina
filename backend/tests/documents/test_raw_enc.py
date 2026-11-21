import base64
import json
import os
import uuid
from datetime import UTC, datetime

import pytest

from storozh.documents import service
from storozh.documents.adapters.mygov_car_poa.adapter import MyGovCarPoaAdapter
from storozh.documents.ports import RawRecord
from storozh.shared import crypto
from storozh.shared.config import settings
from storozh.shared.contracts import SourceSnapshot

RAW = RawRecord(external_id="2026-0001234", data={
    "number": "2026-0001234", "issued_at": "21.11.2026", "vehicle_model": "Chevrolet Cobalt", "plate": "01 A 123 BC",
    "counterparty_name": "Каримов Бахтиёр Алишерович", "counterparty_pinfl": "12345678901234",
    "direction": "Выдана мной", "status_text": "Действует"})


@pytest.fixture
def keys(monkeypatch):
    store: dict = {}
    monkeypatch.setattr(settings, "master_key", base64.b64encode(os.urandom(32)).decode())
    monkeypatch.setattr(settings, "pinfl_hmac_key", "test-key")
    monkeypatch.setattr(crypto, "_key_store", lambda cid, enc: store.setdefault(cid, enc))
    crypto.forget_cached_keys()
    yield
    crypto.forget_cached_keys()


def _snapshot(citizen, with_raw=True) -> tuple[SourceSnapshot, str]:
    doc = MyGovCarPoaAdapter().normalize(RAW)
    return SourceSnapshot(snapshot_id=uuid.uuid4(), citizen_id=citizen, source="mygov.car_poa",
                          fetched_at=datetime.now(UTC), complete=True, documents=[doc],
                          raw={doc.uri: RAW.data} if with_raw else {}), doc.uri


def test_raw_is_encrypted_and_readable_only_by_owner(keys):
    citizen = uuid.uuid4()
    snap, uri = _snapshot(citizen)
    blob = service.raw_enc_for(snap, uri)
    assert blob is not None and b"12345678901234" not in blob and "Каримов".encode() not in blob
    assert json.loads(crypto.decrypt(citizen, blob))["counterparty_pinfl"] == "12345678901234"
    with pytest.raises(crypto.CryptoError):
        crypto.decrypt(uuid.uuid4(), blob)


def test_no_raw_no_blob(keys):
    snap, uri = _snapshot(uuid.uuid4(), with_raw=False)
    assert service.raw_enc_for(snap, uri) is None


def test_payload_stays_free_of_raw_pii(keys):
    snap, _ = _snapshot(uuid.uuid4())
    payload = snap.documents[0].model_dump_json()
    assert "12345678901234" not in payload and "Каримов" not in payload and "123 BC" not in payload
