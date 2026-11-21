from datetime import UTC, date, datetime

from storozh.documents import features

TODAY = date(2026, 11, 21)


def row(**kw):
    base = {"id": "00000000-0000-0000-0000-000000000001", "kind": "poa_car", "title": "Доверенность", "status": "active",
            "owner_role": "principal", "valid_until": None}
    return {**base, **kw}


def test_attention_orders_high_first_and_covers_cases():
    rows = [
        row(kind="poa_car", valid_until="2026-12-01"),  # через 10 дней
        row(kind="poa_car", status="revoked"),
        row(kind="identity_document", status="expired", title="Паспорт"),
        row(kind="tax_assessment", owner_role="debtor", title="НДС"),
        row(kind="labor_contract", valid_until="2027-06-01"),  # далеко — не внимание
    ]
    src = [{"status": "error", "title": "my.soliq.uz"}, {"status": "ok", "title": "my.gov.uz"}]
    out = features._attention(rows, src, TODAY)
    assert [a["type"] for a in out] == ["tax_debt", "expired_id", "expiring", "sources", "revoked"] or \
        [a["level"] for a in out] == sorted((a["level"] for a in out), key=["high", "medium", "info"].index)
    assert {a["type"] for a in out} == {"tax_debt", "expired_id", "expiring", "revoked", "sources"}
    assert next(a for a in out if a["type"] == "expiring")["days_left"] == 10


def test_attention_nothing_when_all_fine():
    assert features._attention([row(valid_until="2027-06-01")], [{"status": "ok", "title": "x"}], TODAY) == []


def test_evidence_html_has_versions_hashes_and_escapes():
    doc = {"title": "<b>Доверенность</b>", "uri": "uz:notarius:poa:1", "kind": "poa_car", "source": "mygov.car_poa",
           "status": "revoked", "issued_at": "2026-11-01", "valid_until": None, "first_seen_at": "2026-11-01T10:00:00+00:00"}
    versions = [{"version_no": 1, "fetched_at": "2026-11-01T10:00:00", "content_hash": "a" * 64, "changed_fields": []},
                {"version_no": 2, "fetched_at": "2026-11-02T11:00:00", "content_hash": "b" * 64, "changed_fields": ["status"]}]
    html = features.evidence_html(doc, versions, {2: [{"field": "status", "from": "active", "to": "revoked"}]},
                                  datetime(2026, 11, 21, tzinfo=UTC))
    assert "a" * 64 in html and "b" * 64 in html and "active → revoked" in html
    assert "<b>Доверенность</b>" not in html and "&lt;b&gt;" in html


def test_evidence_pdf_is_a_real_pdf_when_weasyprint_is_available():
    import pytest

    try:
        from weasyprint import HTML
    except OSError:  # на машине разработчика нет Pango; в CI и в образе есть
        pytest.skip("WeasyPrint system libraries are not installed")
    doc = {"title": "Доверенность", "uri": "uz:notarius:poa:1", "kind": "poa_car", "source": "mygov.car_poa", "status": "active",
           "first_seen_at": "2026-11-01T10:00:00+00:00"}
    html = features.evidence_html(doc, [{"version_no": 1, "fetched_at": "2026-11-01T10:00:00", "content_hash": "a" * 64,
                                         "changed_fields": []}], {}, datetime(2026, 11, 21, tzinfo=UTC))
    assert HTML(string=html).write_pdf().startswith(b"%PDF")
