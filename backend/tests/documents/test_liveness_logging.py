import json
import logging
import uuid

import pytest

from storozh.documents import worker
from storozh.documents.adapters import liveness
from storozh.shared import logging as logs


def _line(record_msg: str, **extra) -> dict:
    rec = logging.LogRecord("t", logging.INFO, "", 0, record_msg, (), None)
    rec.__dict__.update(extra)
    return json.loads(logs.JsonFormatter().format(rec))


def test_json_log_has_request_id_and_extras():
    token = logs.request_id.set("abc123")
    try:
        out = _line("poll ok", source="mygov.car_poa", new_versions=1)
    finally:
        logs.request_id.reset(token)
    assert out["level"] == "info" and out["msg"] == "poll ok" and out["request_id"] == "abc123"
    assert out["source"] == "mygov.car_poa" and out["new_versions"] == 1 and out["time"].endswith("+00:00")


def test_json_log_masks_pinfl_and_phone():
    out = _line("citizen 12345678901234 phone +998 90 123 45 67", pinfl="12345678901234")
    dumped = json.dumps(out, ensure_ascii=False)
    assert "12345678901234" not in dumped and "123 45 67" not in dumped


@pytest.mark.parametrize("url,mark,expected", [
    ("https://my.gov.uz/ru/user/requests", True, True),
    ("https://my.gov.uz/ru/login?redirect=/ru/user/requests", False, False),
    ("https://my.gov.uz/ru/login", True, False),
    ("https://my.gov.uz/ru/user/requests", False, None),
])
def test_verdict(url, mark, expected):
    assert liveness.verdict(url, mark) is expected


@pytest.mark.parametrize("alive,expired", [(False, 1), (True, 0), (None, 0)])
async def test_check_sessions_expires_only_on_definite_no(monkeypatch, alive, expired):
    citizen = uuid.uuid4()
    calls = []

    class FakeProvider:
        def get(self, citizen_id):
            class Ctx:
                async def __aenter__(self_):
                    return object()

                async def __aexit__(self_, *a):
                    return False
            return Ctx()

    async def active():
        return [citizen]

    async def probe(session):
        return alive

    async def expire(citizen_id):
        calls.append(citizen_id)

    monkeypatch.setattr(worker.service, "active_citizens", active)
    monkeypatch.setattr(worker.service, "session_provider", lambda: FakeProvider())
    monkeypatch.setattr(worker.service, "expire_session", expire)
    monkeypatch.setattr(worker.liveness, "cabinet_alive", probe)
    await worker.Collector().check_sessions()
    assert len(calls) == expired
