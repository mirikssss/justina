import json

from storozh.documents.adapters.soliq_legal import selectors as sel
from storozh.documents.adapters.soliq_legal.adapter import (
    SoliqPropertyAdapter,
    SoliqTaxesAdapter,
    SoliqVehiclesAdapter,
    mask_cadastre,
    parse_money,
    parse_table,
)
from storozh.documents.adapters.soliq_legal.tests.fixtures import tables as T
from storozh.documents.ports import RawRecord


def test_empty_table_has_no_rows():
    assert parse_table(T.EMPTY, sel.PROPERTY_COLUMNS) == []


def test_property_normalize_masks_cadastre_and_address():
    (row,) = parse_table(T.PROPERTY, sel.PROPERTY_COLUMNS)
    doc = SoliqPropertyAdapter().normalize(RawRecord(row["cadastre"], {**row, "category": "land"}))
    assert doc.uri == "uz:kadastr:object:10:05:01:02:03:0017" and doc.kind == "real_estate_right"
    assert doc.object.id_masked == "10:05:***:0017" and doc.issued_at.isoformat() == "2026-03-01"
    assert "Тестовая" not in doc.model_dump_json()


def test_vehicle_uri_and_payload_hide_plate():
    (row,) = parse_table(T.VEHICLES, sel.VEHICLE_COLUMNS)
    doc = SoliqVehiclesAdapter().normalize(RawRecord(row["plate"], row))
    dumped = doc.model_dump_json()
    assert "123" not in doc.uri and "123 BC" not in dumped and doc.object.id_masked == "01 *** BC"
    assert doc.kind == "vehicle" and doc.issued_at.isoformat() == "2024-06-15"


def test_taxes_debt_means_active_and_debtor():
    docs = [SoliqTaxesAdapter().normalize(RawRecord(f"{r['code']}-{r['date']}", r))
            for r in parse_table(T.TAXES, sel.TAX_COLUMNS)]
    assert [d.status for d in docs] == ["active", "completed"]
    assert docs[0].owner_role == "debtor" and docs[1].owner_role == "party"
    assert docs[0].uri == "uz:soliq:tax:10101-20.11.2026"
    assert json.loads(docs[0].model_dump_json())["fields"]["debt"] == "600 000"


def test_money_and_cadastre_helpers():
    assert str(parse_money("1 000 000,50")) == "1000000.50" and parse_money("—") is None
    assert mask_cadastre("12:34") == "12:34"


def test_company_founders_and_shares_masked():
    from storozh.documents.adapters.soliq_legal.adapter import SoliqCompanyAdapter, parse_company

    company = parse_company(T.COMPANY)
    assert company["inn"] == "300000001" and company["name"] == '"EXAMPLE CO 1" MCHJ' and len(company["founders"]) == 2
    doc = SoliqCompanyAdapter().normalize(RawRecord(company["inn"], company))
    assert doc.uri == "uz:soliq:company:300000001" and doc.kind == "company"
    f = doc.fields["founders"]
    assert f[0]["name_masked"] == "I***n I." and f[0]["share_percent"] == "60" and f[0]["amount"] == "600 000.00 сум"
    assert f[1]["legal_entity"] and f[1]["inn"] == "300000999" and f[1]["name_masked"] == '"PARTNER CO" MCHJ'
    assert "IVANOV" not in doc.model_dump_json() and "PETROVICH" not in doc.model_dump_json()


def test_company_page_without_header_is_none():
    from storozh.documents.adapters.soliq_legal.adapter import parse_company

    assert parse_company("<div>другая страница</div>") is None
