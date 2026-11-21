"""mygov.notifications — уведомления кабинета my.gov.uz как документы-события (на них видно разные госрегистры).

Текст уведомления не сохраняем (в нём бывает ФИО): только заголовок и время. URI — хеш (заголовок, время).
"""

import hashlib
from datetime import datetime

from lxml import html as lxml_html

from storozh.documents.adapters.mygov_cabinet import cabinet_html
from storozh.documents.adapters.mygov_notifications import selectors as sel
from storozh.documents.ports import BrowserSession, RawRecord
from storozh.shared import uri
from storozh.shared.contracts import NormalizedDocument


def parse_list(page_html: str) -> list[RawRecord]:
    out = []
    for box in lxml_html.fromstring(page_html).cssselect(sel.ROW):
        spans = box.cssselect(sel.SPANS)
        title = (box.get(sel.TITLE_ATTR) or (spans[0].text_content() if spans else "")).strip().strip('"«»')
        when = spans[-1].text_content().strip() if len(spans) >= 3 else ""
        if not title or any(k in title.lower() for k in sel.SKIP_TITLES):
            continue
        key = hashlib.sha256(f"{title}|{when}".encode()).hexdigest()[:16]
        out.append(RawRecord(external_id=key, data={"title": title, "time": when}))
    return out


class MyGovNotificationsAdapter:
    source_id = "mygov.notifications"
    title = "my.gov.uz · уведомления"
    poll_interval_s = 120
    complete = False  # читаем только первую страницу: старые уведомления «пропадать» не должны

    async def fetch(self, session: BrowserSession) -> list[RawRecord]:
        return parse_list(await cabinet_html(session, sel.LIST_PATH, sel.ROW, self.source_id))

    def normalize(self, raw: RawRecord) -> NormalizedDocument:
        d = raw.data
        try:
            issued = datetime.strptime(d["time"], "%Y-%m-%d %H:%M:%S").date()
        except ValueError:
            issued = None
        return NormalizedDocument.model_validate({
            "uri": uri.build("mygov", "notice", raw.external_id),
            "kind": "notification",
            "source": self.source_id,
            "title": d["title"],
            "status": "completed",
            "owner_role": "party",
            "parties": [{"role": "party", "name_masked": "Вы"}],
            "issued_at": issued,
            "issuer": {"type": "mygov", "name": "my.gov.uz"},
            "fields": {"time": d["time"]},
            "source_ref": {"external_id": raw.external_id},
        })
