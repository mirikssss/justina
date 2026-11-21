"""mygov.requests — все поданные заявки человека в «Мои заявки» my.gov.uz, кроме e-доверенностей (их читает car_poa).

Заявка = документ с URI uz:mygov:request:{номер}; смена статуса «В обработке → Обработано» даёт document.status_changed.
Разметка списка общая с car_poa (mygov_car_poa/selectors.py).
"""

from storozh.documents.adapters.mygov_cabinet import cabinet_html
from storozh.documents.adapters.mygov_car_poa import selectors as sel
from storozh.documents.adapters.mygov_car_poa.adapter import is_poa_title, parse_cards, parse_date
from storozh.documents.ports import BrowserSession, RawRecord
from storozh.shared import uri
from storozh.shared.contracts import NormalizedDocument

_STATUS = [  # (подстрока текста статуса в нижнем регистре, статус)
    ("обработано", "completed"), ("исполнен", "completed"), ("выполнен", "completed"),
    ("в обработке", "active"), ("на рассмотрении", "active"), ("ожидани", "active"), ("новая", "active"),
]


def status_of(text: str | None) -> str:
    t = (text or "").lower()
    return next((s for key, s in _STATUS if key in t), "unknown")


def parse_list(page_html: str) -> list[RawRecord]:
    return [RawRecord(external_id=d["number"], data=d) for d in parse_cards(page_html) if not is_poa_title(d["title"])]


class MyGovRequestsAdapter:
    source_id = "mygov.requests"
    title = "my.gov.uz · мои заявки"
    poll_interval_s = 60
    complete = True

    async def fetch(self, session: BrowserSession) -> list[RawRecord]:
        return parse_list(await cabinet_html(session, sel.LIST_PATH, sel.CARD, self.source_id))

    def normalize(self, raw: RawRecord) -> NormalizedDocument:
        d = raw.data
        return NormalizedDocument.model_validate({
            "uri": uri.build("mygov", "request", d["number"]),
            "kind": "application",
            "source": self.source_id,
            "title": d.get("title") or "Заявка на госуслугу",
            "status": status_of(d.get("status_text")),
            "owner_role": "party",
            "parties": [{"role": "party", "name_masked": "Вы"}],
            "issued_at": parse_date(d.get("issued_at")),
            "issuer": {"type": "mygov", "name": "my.gov.uz"},
            "fields": {"request_id": d["number"]},
            "source_ref": {"external_id": raw.external_id, "url": f"{sel_base()}{d.get('detail_href') or sel.LIST_PATH}"},
        })


def sel_base() -> str:
    from storozh.shared.config import settings

    return settings.mygov_base_url.rstrip("/")
