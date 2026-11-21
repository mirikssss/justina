"""mygov.family и mygov.doc_deadlines — семья/браки и сроки паспорта и прав из личного профиля my.gov.uz.

Данные третьих лиц (родственники) в payload только масками: имя маской, ПИНФЛ — HMAC, дата рождения — только год.
Серия и номер паспорта в payload не попадают (только маска и хеш в URI); полные строки уйдут в raw_enc.
"""

import hashlib
from datetime import date, datetime

from lxml import html as lxml_html

from storozh.documents.adapters.mygov_cabinet import cabinet_html
from storozh.documents.adapters.mygov_profile import selectors as sel
from storozh.documents.domain.masking import mask_name, mask_number
from storozh.documents.ports import BrowserSession, RawRecord
from storozh.shared import crypto, uri
from storozh.shared.contracts import NormalizedDocument

_ISSUER = {"type": "mygov", "name": "my.gov.uz"}


def _date(text: str | None) -> date | None:
    try:
        return datetime.strptime((text or "").strip()[:10], sel.DATE_FORMAT).date()
    except ValueError:
        return None


def parse_table(page_html: str, columns: tuple[str, ...]) -> list[dict[str, str]]:
    out = []
    for tr in lxml_html.fromstring(page_html).cssselect(sel.ROWS):
        cells = [" ".join(td.text_content().split()) for td in tr.cssselect("td")]
        if len(cells) >= len(columns):
            out.append(dict(zip(columns, cells, strict=False)))
    return out


def parse_family(page_html: str) -> list[RawRecord]:
    out = []
    for row in parse_table(page_html, sel.FAMILY_COLUMNS):
        if row["relation"].lower() in sel.SELF_ROWS or not row["pinfl"].strip():
            continue
        out.append(RawRecord(external_id=crypto.hmac_pinfl(row["pinfl"])[:16], data=row))
    return out


def parse_deadlines(page_html: str) -> list[RawRecord]:
    out = []
    for row in parse_table(page_html, sel.DEADLINES_COLUMNS):
        if sel.NO_DATA_MARK in (row["issued"] + row["expires"]).lower() or not row["mark"].strip():
            continue
        key = hashlib.sha256(f"{row['doc_type']}|{row['mark']}".encode()).hexdigest()[:16]
        out.append(RawRecord(external_id=key, data=row))
    return out


class MyGovFamilyAdapter:
    source_id = "mygov.family"
    title = "my.gov.uz · семья и браки"
    poll_interval_s = 1800
    complete = True

    async def fetch(self, session: BrowserSession) -> list[RawRecord]:
        return parse_family(await cabinet_html(session, sel.FAMILY_PATH, sel.ROWS, self.source_id))

    def normalize(self, raw: RawRecord) -> NormalizedDocument:
        d = raw.data
        relation = d["relation"].strip()
        spouse = any(m in relation.lower() for m in sel.SPOUSE_MARKS)
        birth = _date(d["birth_date"])
        masked = mask_name(d["name"])
        return NormalizedDocument.model_validate({
            "uri": uri.build("mygov", "family", raw.external_id),
            "kind": "marriage" if spouse else "family_record",
            "source": self.source_id,
            "title": f"Брак: {masked}" if spouse else f"{relation}: {masked}",
            "status": "active",
            "owner_role": "party",
            "parties": [{"role": "party", "name_masked": "Вы"},
                        {"role": "spouse" if spouse else relation.lower(), "name_masked": masked,
                         "pinfl_hash": crypto.hmac_pinfl(d["pinfl"])}],
            "issuer": _ISSUER,
            "fields": {"relation": relation, "birth_year": birth.year if birth else None},
            "source_ref": {"external_id": raw.external_id},
        })


class MyGovDeadlinesAdapter:
    source_id = "mygov.doc_deadlines"
    title = "my.gov.uz · сроки документов"
    poll_interval_s = 1800
    complete = True

    async def fetch(self, session: BrowserSession) -> list[RawRecord]:
        return parse_deadlines(await cabinet_html(session, sel.DEADLINES_PATH, sel.ROWS, self.source_id))

    def normalize(self, raw: RawRecord) -> NormalizedDocument:
        d = raw.data
        valid_until = _date(d["expires"])
        expired = valid_until is not None and valid_until < date.today()
        return NormalizedDocument.model_validate({
            "uri": uri.build("mygov", "idcard", raw.external_id),
            "kind": "identity_document",
            "source": self.source_id,
            "title": d["doc_type"].replace("\\", " / "),
            "status": "expired" if expired else "active",
            "owner_role": "party",
            "parties": [{"role": "party", "name_masked": "Вы"}],
            "issued_at": _date(d["issued"]),
            "valid_until": valid_until,
            "issuer": _ISSUER,
            "fields": {"mark_masked": mask_number(d["mark"], keep=2)},
            "source_ref": {"external_id": raw.external_id},
        })
