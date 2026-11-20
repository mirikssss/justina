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
