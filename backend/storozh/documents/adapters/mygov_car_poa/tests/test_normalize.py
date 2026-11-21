from storozh.documents.adapters.mygov_car_poa.adapter import MyGovCarPoaAdapter, status_of
from storozh.documents.ports import RawRecord

RAW = RawRecord(external_id="2026-0001234", data={
    "number": "2026-0001234", "issued_at": "21.11.2026", "valid_until": "21.12.2026",
    "vehicle_model": "Chevrolet Cobalt", "plate": "01 A 123 BC", "counterparty_name": "Каримов Бахтиёр Алишерович",
    "counterparty_pinfl": "12345678901234", "direction": "Выдана мной", "status_text": "Действует",
})


def test_normalize_masks_and_roles():
    doc = MyGovCarPoaAdapter().normalize(RAW)
    assert doc.uri == "uz:notarius:poa:2026-0001234"
    assert doc.owner_role == "principal" and doc.status == "active"
    dumped = doc.model_dump_json()
    assert "Каримов" not in dumped and "12345678901234" not in dumped and "123 BC" not in dumped
    assert doc.parties[1].name_masked == "Б***р К." and doc.object.id_masked == "01 *** BC"


def test_status_texts():
    assert status_of("Bekor qilingan") == "revoked"
    assert status_of("Аннулирована") == "revoked"
    assert status_of("Muddati o'tgan") == "expired"
    assert status_of("???") == "unknown"


def test_parse_list_keeps_only_poa_cards():
    from pathlib import Path

    from storozh.documents.adapters.mygov_car_poa.adapter import parse_list

    html = (Path(__file__).parent / "fixtures" / "requests_list.html").read_text(encoding="utf-8")
    records = parse_list(html)
    assert [r.external_id for r in records] == ["900000001"]
    d = records[0].data
    assert d["issued_at"] == "21.11.2026" and d["status_text"] == "Обработано"
    doc = MyGovCarPoaAdapter().normalize(records[0])
    assert doc.uri == "uz:notarius:poa:900000001"
    assert doc.status == "active" and doc.owner_role == "principal" and doc.issued_at.isoformat() == "2026-11-21"
