"""birdarcha.company — юрлица человека из заявок на регистрацию в Birdarcha (Business Registration).

Один документ на юрлицо: URI uz:birdarcha:company:{ИНН}. Если заявок по ИНН несколько (регистрация, изменения),
берём самую свежую. ИНН и название юрлица публичны; ПИНФЛ человека на странице не читаем.
Роль человека (директор или учредитель) на списке не видна — владелец записи `party`.
"""

from datetime import date, datetime

from lxml import html as lxml_html
from playwright.async_api import TimeoutError as PlaywrightTimeout

from storozh.documents.adapters import browser
from storozh.documents.adapters.birdarcha_company import selectors as sel
from storozh.documents.ports import BrowserSession, RawRecord
from storozh.shared import uri
from storozh.shared.config import settings
from storozh.shared.contracts import NormalizedDocument


def _date(text: str) -> date | None:
    try:
        return datetime.strptime(text.strip(), sel.DATE_FORMAT).date()
    except ValueError:
        return None


def status_of(text: str) -> str:
    t = text.lower()
    return next((s for key, s in sel.STATUS if key in t), "unknown")


def parse_list(page_html: str) -> list[RawRecord]:
    """Строки таблицы -> по одной записи на ИНН (самая свежая заявка)."""
    newest: dict[str, dict] = {}
    for tr in lxml_html.fromstring(page_html).cssselect(sel.ROWS):
        cells = [td.text_content().strip() for td in tr.cssselect("td")]
        if len(cells) < len(sel.COLUMNS):
            continue
        d = dict(zip(sel.COLUMNS, cells, strict=False))
        if not d["inn"].isdigit():
            continue
        cur = newest.get(d["inn"])
        if cur is None or (_date(d["date"]) or date.min, d["application_no"]) > (_date(cur["date"]) or date.min, cur["application_no"]):
            newest[d["inn"]] = d
    return [RawRecord(external_id=inn, data=d) for inn, d in newest.items()]


class BirdarchaCompanyAdapter:
    source_id = "birdarcha.company"
    title = "Birdarcha.uz · мои юрлица"
    poll_interval_s = 600
    complete = True

    async def fetch(self, session: BrowserSession) -> list[RawRecord]:
        async with browser.page(session) as page:
            await page.goto(settings.birdarcha_base_url.rstrip("/") + sel.LIST_PATH, wait_until="domcontentloaded")
            try:
                await page.wait_for_selector(sel.READY, timeout=20_000)
            except PlaywrightTimeout:
                raise browser.SessionExpired(self.source_id) from None
            await page.wait_for_load_state("networkidle")
            return parse_list(await page.content())

    def normalize(self, raw: RawRecord) -> NormalizedDocument:
        d = raw.data
        return NormalizedDocument.model_validate({
            "uri": uri.build("birdarcha", "company", d["inn"]),
            "kind": "company",
            "source": self.source_id,
            "title": d["name"],
            "status": status_of(d["status_text"]),
            "owner_role": "party",
            "parties": [{"role": "party", "name_masked": "Вы"}],
            "issued_at": _date(d["date"]),
            "issuer": {"type": "adliya", "name": "Birdarcha.uz"},
            "fields": {"inn": d["inn"], "application_no": d["application_no"], "application_type": d["application_type"]},
            "source_ref": {"external_id": d["inn"],
                           "url": settings.birdarcha_base_url.rstrip("/") + sel.VIEW_PATH.format(number=d["application_no"])},
        })
