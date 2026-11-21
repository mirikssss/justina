from storozh.assistant.drafts import render
from storozh.shared.contracts import NormalizedDocument


def _doc() -> NormalizedDocument:
    return NormalizedDocument.model_validate({
        "uri": "uz:notarius:poa:2026-0001234", "kind": "poa_car", "source": "mygov.car_poa",
        "title": "Доверенность на автомобиль", "status": "active", "owner_role": "principal",
        "parties": [{"role": "principal", "name_masked": "М***л А."}, {"role": "agent", "name_masked": "Б***р К."}],
        "object": {"type": "vehicle", "id_masked": "01 *** 45", "label": "Chevrolet Cobalt"},
        "issued_at": "2026-11-21", "issuer": {"type": "notary", "name": "Нотариус Юнусабадского района"},
        "source_ref": {"external_id": "123456"},
    })


def test_art31_has_requisites_and_legal_basis():
    ctx = render.context(_doc(), {"display_name": "Каримов Азиз", "pinfl": "31234567890123"}, "ru")
    html = render.render_html("art31_postpone", ctx)
    for part in ("Каримов Азиз", "31234567890123", "№ 123456", "Chevrolet Cobalt", "статьи 31",
                 "Нотариус Юнусабадского района", "десяти дней"):
        assert part in html, part


def test_court_claim_uz_and_pdf():
    ctx = render.context(_doc(), {"display_name": "Karimov Aziz"}, "uz")
    html = render.render_html("court_claim", ctx)
    assert "Da’vo arizasi" in html and "Б***р К." in html  # ответчик — другая сторона документа
    assert render.render_pdf("court_claim", ctx).startswith(b"%PDF")
