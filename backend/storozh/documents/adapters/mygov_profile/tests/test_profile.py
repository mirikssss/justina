import json
from datetime import date
from pathlib import Path

from storozh.documents.adapters.mygov_profile.adapter import (
    MyGovDeadlinesAdapter,
    MyGovFamilyAdapter,
    parse_deadlines,
    parse_family,
)

FIX = Path(__file__).parent / "fixtures"
FAMILY = (FIX / "family.html").read_text(encoding="utf-8")
DEADLINES = (FIX / "deadlines.html").read_text(encoding="utf-8")


def test_family_skips_user_row_and_marks_spouse_as_marriage():
    recs = parse_family(FAMILY)
    assert [r.data["relation"] for r in recs] == ["Отец", "Мать", "Супруга"]
    docs = [MyGovFamilyAdapter().normalize(r) for r in recs]
    assert [d.kind for d in docs] == ["family_record", "family_record", "marriage"]
    assert docs[2].parties[1].role == "spouse" and docs[2].title.startswith("Брак: ")


def test_family_payload_has_no_third_party_pii():
    dumped = "".join(MyGovFamilyAdapter().normalize(r).model_dump_json() for r in parse_family(FAMILY))
    for secret in ("30000000000001", "60000000000004", "ИВАНОВ", "СИДОРОВА", "31.08.2006", "01.02.2007"):
        assert secret not in dumped
    d = json.loads(MyGovFamilyAdapter().normalize(parse_family(FAMILY)[2]).model_dump_json())
    assert d["fields"]["birth_year"] == 2007 and len(d["parties"][1]["pinfl_hash"]) == 64


def test_deadlines_only_documents_with_data_and_no_passport_number():
    recs = parse_deadlines(DEADLINES)
    assert len(recs) == 1
    doc = MyGovDeadlinesAdapter().normalize(recs[0])
    assert doc.kind == "identity_document" and doc.title == "Паспорт / ID-карта"
    assert doc.status == "active" and doc.valid_until == date(2033, 12, 31) and doc.issued_at == date(2024, 1, 1)
    assert "AD1234567" not in doc.model_dump_json() and "1234567" not in doc.uri


def test_expired_passport_flips_status_keeping_uri():
    old = DEADLINES.replace("31.12.2033", "31.12.2020")
    a, b = parse_deadlines(DEADLINES)[0], parse_deadlines(old)[0]
    assert a.external_id == b.external_id
    adapter = MyGovDeadlinesAdapter()
    assert adapter.normalize(a).status == "active" and adapter.normalize(b).status == "expired"
