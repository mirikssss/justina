from pathlib import Path

from storozh.documents.adapters.birdarcha_company.adapter import BirdarchaCompanyAdapter, parse_list, status_of

HTML = (Path(__file__).parent / "fixtures" / "applications.html").read_text(encoding="utf-8")


def test_one_document_per_application():
    recs = parse_list(HTML)
    assert [r.external_id for r in recs] == ["9000001", "9000050", "9000010"]


def test_normalize_application():
    docs = {r.external_id: BirdarchaCompanyAdapter().normalize(r) for r in parse_list(HTML)}
    ok = docs["9000010"]
    assert ok.uri == "uz:birdarcha:request:9000010" and ok.kind == "application" and ok.status == "completed"
    assert ok.title == "Ro‘yxatdan o‘tkazish: EXAMPLE CO 2" and ok.issued_at.isoformat() == "2026-10-01"
    assert docs["9000050"].status == "unknown"  # «Jarayonda» — статус не размечен, не выдумываем


def test_status_texts():
    assert status_of("Muvaffaqiyatli") == "completed" and status_of("Jarayonda") == "unknown"
