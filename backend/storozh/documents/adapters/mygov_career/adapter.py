"""mygov.career — записи о стаже работы из кабинета my.gov.uz (трудовая книжка, ЕНСТ) как документы `labor_contract`.

Одна строка таблицы = один документ uz:mehnat:contract:{хеш}. «До сих пор» → active; появилась дата окончания →
completed (document.status_changed). Название организации — юрлицо, не персональные данные человека.
"""

import hashlib
from datetime import date, datetime

from lxml import html as lxml_html

from storozh.documents.adapters.mygov_cabinet import cabinet_html
from storozh.documents.adapters.mygov_career import selectors as sel
from storozh.documents.ports import BrowserSession, RawRecord
from storozh.shared import uri
from storozh.shared.contracts import NormalizedDocument


def _date(text: str) -> date | None:
    try:
        return datetime.strptime(text.strip(), sel.DATE_FORMAT).date()
    except ValueError:
        return None


def parse_list(page_html: str) -> list[RawRecord]:
    out, seen = [], set()
    for tr in lxml_html.fromstring(page_html).cssselect(sel.ROWS):
        cells = [td.text_content().strip() for td in tr.cssselect("td")]
        if len(cells) < len(sel.COLUMNS):
            continue
        data = dict(zip(sel.COLUMNS, cells, strict=False))
        if not data["employer"]:
            continue
        key = hashlib.sha256("|".join(data[k] for k in ("employer", "started", "position", "department"))
                             .encode()).hexdigest()[:16]
        if key not in seen:
            seen.add(key)
            out.append(RawRecord(external_id=key, data=data))
    return out


class MyGovCareerAdapter:
    source_id = "mygov.career"
    title = "my.gov.uz · стаж работы"
    poll_interval_s = 600
    complete = True

    async def fetch(self, session: BrowserSession) -> list[RawRecord]:
        return parse_list(await cabinet_html(session, sel.LIST_PATH, sel.ROWS, self.source_id))

    def normalize(self, raw: RawRecord) -> NormalizedDocument:
        d = raw.data
        ongoing = sel.ONGOING_MARK in d["ended"].lower()
        return NormalizedDocument.model_validate({
            "uri": uri.build("mehnat", "contract", raw.external_id),
            "kind": "labor_contract",
            "source": self.source_id,
            "title": f"Mehnat faoliyati: {d['position'] or 'lavozim ko‘rsatilmagan'}",
            "status": "active" if ongoing else "completed",
            "owner_role": "employee",
            "parties": [{"role": "employee", "name_masked": "Вы"}, {"role": "employer", "name_masked": d["employer"]}],
            "issued_at": _date(d["started"]),
            "valid_until": None if ongoing else _date(d["ended"]),
            "issuer": {"type": "mygov", "name": "my.gov.uz"},
            "fields": {"position": d["position"], "department": d["department"]},
            "source_ref": {"external_id": raw.external_id},
        })
