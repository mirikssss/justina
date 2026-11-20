import json
from pathlib import Path

from storozh.shared.contracts import NormalizedDocument
from storozh.shared.hashing import content_hash

EXAMPLE = Path(__file__).resolve().parents[3] / "contracts" / "examples" / "normalized_document.poa_car.json"


def _doc(**patch) -> NormalizedDocument:
    data = json.loads(EXAMPLE.read_text())
    data.update(patch)
    return NormalizedDocument.model_validate(data)


def test_hash_ignores_source_url():
    a = _doc()
    b = _doc(source_ref={"external_id": "123456", "url": "https://other"})
    assert content_hash(a) == content_hash(b)


def test_hash_sees_status():
    assert content_hash(_doc()) != content_hash(_doc(status="revoked"))
