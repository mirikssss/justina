import pytest

from storozh.documents.adapters.vakolat.adapter import VakolatAdapter, registry_status
from storozh.documents.demo import _poa
from storozh.documents.ports import RawRecord

# НЕ снято с живого реестра: формат успешного ответа неизвестен (см. selectors.py); тест фиксирует предположение.
ASSUMED_OK = {"data": {"status": {"name": "Bekor qilingan"}}}
NOT_FOUND = {"status": {"code": "2013", "message": "Vakolat topilmadi"}}  # снято с живого реестра


@pytest.mark.parametrize("body,expected", [(ASSUMED_OK, "revoked"), ({"data": {"status": "Amalda"}}, "active"),
                                           (NOT_FOUND, "unknown"), ({}, "unknown")])
def test_registry_status(body, expected):
    assert registry_status(body) == expected


def test_normalize_overlays_status_and_keeps_masks():
    payload = _poa("active").model_dump(mode="json")
    doc = VakolatAdapter().normalize(RawRecord("1", {"payload": payload, "registry": ASSUMED_OK}))
    assert doc.status == "revoked" and doc.uri == payload["uri"] and doc.parties[1].name_masked == "Б***р К."


def test_normalize_unknown_status_keeps_document_as_is():
    payload = _poa("active").model_dump(mode="json")
    assert VakolatAdapter().normalize(RawRecord("1", {"payload": payload, "registry": NOT_FOUND})).status == "active"
