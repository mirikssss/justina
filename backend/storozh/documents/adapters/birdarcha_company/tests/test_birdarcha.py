from pathlib import Path

from storozh.documents.adapters.birdarcha_company.adapter import BirdarchaCompanyAdapter, parse_list, status_of

HTML = (Path(__file__).parent / "fixtures" / "applications.html").read_text(encoding="utf-8")


def test_one_document_per_inn_newest_application_wins():
    recs = {r.external_id: r.data for r in parse_list(HTML)}
    assert set(recs) == {"300000001", "300000002"}
    assert recs["300000001"]["application_no"] == "9000050"


def test_normalize_company():
    docs = {r.external_id: BirdarchaCompanyAdapter().normalize(r) for r in parse_list(HTML)}
    ok = docs["300000002"]
    assert ok.uri == "uz:birdarcha:company:300000002" and ok.kind == "company" and ok.status == "active"
    assert ok.title == "EXAMPLE CO 2" and ok.issued_at.isoformat() == "2026-10-01"
    assert docs["300000001"].status == "unknown"  # «Jarayonda» — статус не размечен, не выдумываем


def test_status_texts():
    assert status_of("Muvaffaqiyatli") == "active" and status_of("Jarayonda") == "unknown"
