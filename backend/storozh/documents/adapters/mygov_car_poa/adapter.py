"""mygov.car_poa — электронные доверенности на авто, выданные человеком и ему (FR-D-03).

fetch читает страницу кабинета сессией человека, parse_list — разметку (тесты на фикстурах),
normalize — в NormalizedDocument: ФИО и госномер маской, ПИНФЛ — HMAC.
"""

import re
from datetime import date, datetime
from urllib.parse import urljoin

from lxml import html as lxml_html
from playwright.async_api import TimeoutError as PlaywrightTimeout

from storozh.documents.adapters import browser
from storozh.documents.adapters.mygov_car_poa import selectors as sel
from storozh.documents.domain.masking import mask_name, mask_number, mask_plate
from storozh.documents.ports import BrowserSession, RawRecord
from storozh.shared import crypto, uri
from storozh.shared.config import settings
from storozh.shared.contracts import NormalizedDocument

_STATUS = [  # (подстрока текста статуса в нижнем регистре, статус)
    ("bekor", "revoked"), ("аннулир", "revoked"), ("отозв", "revoked"),
    ("muddati", "expired"), ("истек", "expired"), ("истёк", "expired"),
    ("faol", "active"), ("amalda", "active"), ("действ", "active"),
    ("обработано", "active"),  # заявка на выдачу исполнена; отзыв здесь не виден — его ловит vakolat.check
]
_ISSUED_BY_ME = ("выдан", "berilgan", "issued", "мной", "men")


def status_of(text: str) -> str:
    t = text.lower()
    return next((s for key, s in _STATUS if key in t), "unknown")


def parse_date(text: str | None) -> date | None:
    if not text:
        return None
    text = text.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def parse_cards(page_html: str) -> list[dict]:
    """Все карточки «Мои заявки» (кроме «Черновиков») -> словари полей. Селекторы — в selectors.py."""
    tree = lxml_html.fromstring(page_html)
    out = []
    for row in tree.cssselect(sel.ROW):
        href = row.get("href", "")
        if href.endswith(sel.SKIP_HREF_SUFFIXES) or not href[len(sel.HREF_PREFIX):].strip("/").isdigit():
            continue
        data = {}
        for key, css in sel.FIELDS.items():
            found = row.cssselect(css)
            data[key] = found[0].text_content().strip() if found else None
        data["number"] = (data["number"] or "").lstrip("#").strip() or href[len(sel.HREF_PREFIX):].strip("/")
        icon = row.cssselect(sel.DATE_ICON)
        data["issued_at"] = icon[0].getparent().text_content().strip() if icon else None
        data["detail_href"] = href
        out.append(data)
    return out


def is_poa_title(title: str | None) -> bool:
    return sel.TITLE_MARK in (title or "").lower()


def parse_list(page_html: str) -> list[RawRecord]:
    """Карточки заявок -> записи об e-доверенностях (остальные заявки читает mygov.requests)."""
    out = []
    for data in parse_cards(page_html):
        if is_poa_title(data["title"]):
            data["direction"] = "Выдана мной"  # «Мои заявки» — только заявки самого человека
            out.append(RawRecord(external_id=data["number"], data=data))
    return out


def parse_detail(page_html: str) -> dict[str, str]:
    """Подробности заявки (содержимое iframe) -> поля RawRecord.data. Пустые поля пропускаем."""
    tree = lxml_html.fromstring(page_html)
    out = {}
    for key, css in sel.DETAIL_FIELDS.items():
        found = tree.cssselect(css)
        if found and found[0].text_content().strip():
            out[key] = found[0].text_content().strip()
    return out


class MyGovCarPoaAdapter:
    source_id = "mygov.car_poa"
    title = "my.gov.uz · e-доверенности на авто"
    poll_interval_s = 20
    complete = True

    async def fetch(self, session: BrowserSession) -> list[RawRecord]:
        async with browser.page(session) as page:
            base = settings.mygov_base_url.rstrip("/")
            await page.goto(base + sel.LIST_PATH, wait_until="domcontentloaded")
            try:
                await page.wait_for_selector(sel.LOGGED_IN_MARK, timeout=20_000)
            except PlaywrightTimeout:
                raise browser.SessionExpired(self.source_id) from None
            if sel.LOGIN_PATH in page.url:
                raise browser.SessionExpired(self.source_id)
            try:  # карточки рисуются после расшифровки ответа API, позже блока профиля
                await page.wait_for_selector(sel.CARD, timeout=15_000)
            except PlaywrightTimeout:
                pass  # пустой список
            await browser.settle(page)
            records = parse_list(await page.content())
            return [RawRecord(r.external_id, {**r.data, **await self._detail(page, base, r.data["detail_href"])})
                    for r in records]

    @staticmethod
    async def _detail(page, base: str, href: str) -> dict[str, str]:
        """Открыть заявку и прочитать iframe с подробностями; не нашли — оставляем поля пустыми."""
        try:
            await page.goto(base + href, wait_until="domcontentloaded")
            src = await page.get_attribute(sel.DETAIL_IFRAME, "src", timeout=10_000)
            if not src:
                return {}
            await page.goto(urljoin(base + href, src), wait_until="domcontentloaded")
            return parse_detail(await page.content())
        except PlaywrightTimeout:
            return {}

    def normalize(self, raw: RawRecord) -> NormalizedDocument:
        d = raw.data
        number = re.sub(r"\s+", "", d["number"])
        issued_by_me = any(k in (d.get("direction") or "").lower() for k in _ISSUED_BY_ME)
        owner_role = "principal" if issued_by_me else "agent"
        other_role = "agent" if issued_by_me else "principal"
        other = {"role": other_role, "name_masked": mask_name(d.get("counterparty_name") or "")}
        if d.get("counterparty_pinfl"):
            other["pinfl_hash"] = crypto.hmac_pinfl(d["counterparty_pinfl"])
        parties = [{"role": owner_role, "name_masked": "Вы"}, other]
        return NormalizedDocument.model_validate({
            "uri": uri.build("notarius", "poa", number),
            "kind": "poa_car",
            "source": self.source_id,
            "title": "Доверенность на автомобиль",
            "status": status_of(d.get("status_text") or ""),
            "owner_role": owner_role,
            "parties": parties,
            "object": {"type": "vehicle", "id_masked": mask_plate(d["plate"]) if d.get("plate") else None,
                       "label": d.get("vehicle_model")},
            "issued_at": parse_date(d.get("issued_at")),
            "valid_until": parse_date(d.get("valid_until")),
            "issuer": {"type": "mygov", "name": "my.gov.uz"},
            "fields": {"number_masked": mask_number(number)},
            "source_ref": {"external_id": raw.external_id,
                           "url": settings.mygov_base_url.rstrip("/") + (d.get("detail_href") or sel.LIST_PATH)},
        })
