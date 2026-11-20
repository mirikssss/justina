import json
from pathlib import Path

from storozh.documents.domain.masking import mask_name, mask_number, mask_plate
from storozh.documents.domain.versions import classify, diff
from storozh.shared.contracts import NormalizedDocument
from storozh.shared.hashing import content_hash

EX = Path(__file__).resolve().parents[3] / "contracts" / "examples" / "normalized_document.poa_car.json"
DOC = NormalizedDocument.model_validate(json.loads(EX.read_text()))


def test_diff_nested_and_ignores_url():
    a = {"status": "active", "object": {"label": "A"}, "source_ref": {"external_id": "1", "url": "x"}}
    b = {"status": "revoked", "object": {"label": "A"}, "source_ref": {"external_id": "1", "url": "y"}}
    assert diff(a, b) == [{"field": "status", "from": "active", "to": "revoked"}]


def test_classify_created_unchanged_changed():
    assert classify(DOC, None, None).kind == "created"
    h, p = content_hash(DOC), DOC.model_dump(mode="json")
    assert classify(DOC, h, p).kind == "unchanged"
    revoked = DOC.model_copy(update={"status": "revoked"})
    ch = classify(revoked, h, p)
    assert ch.kind == "changed" and ch.status_changed and ch.changed_fields == ["status"]


def test_masks():
    assert mask_name("Каримов Бахтиёр Алишерович") == "Б***р К."
    assert mask_plate("01 A 123 BC") == "01 *** BC"
    assert mask_number("2026-0001234") == "2026-****234"
