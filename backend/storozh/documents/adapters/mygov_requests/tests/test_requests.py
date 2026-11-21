from pathlib import Path

from storozh.documents.adapters.mygov_car_poa.adapter import parse_list as poa_list
from storozh.documents.adapters.mygov_requests.adapter import MyGovRequestsAdapter, parse_list, status_of

# Фикстура car_poa: в ней одна доверенность и одна справка — адаптеры не должны пересекаться.
HTML = (Path(__file__).parents[2] / "mygov_car_poa" / "tests" / "fixtures" / "requests_list.html").read_text(encoding="utf-8")


def test_requests_exclude_poa_and_poa_excludes_requests():
    assert [r.external_id for r in parse_list(HTML)] == ["900000002"]
    assert [r.external_id for r in poa_list(HTML)] == ["900000001"]


def test_normalize_application():
    (rec,) = parse_list(HTML)
    doc = MyGovRequestsAdapter().normalize(rec)
    assert doc.uri == "uz:mygov:request:900000002" and doc.kind == "application"
    assert doc.status == "completed" and doc.title == "Справка о трудовой деятельности"
    assert doc.issued_at.isoformat() == "2026-11-12"


def test_status_texts():
    assert status_of("В обработке") == "active" and status_of("Обработано") == "completed" and status_of("?") == "unknown"
