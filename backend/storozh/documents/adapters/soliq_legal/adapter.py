"""soliq.* — имущество, земля, транспорт и налоги юрлица человека из налогового кабинета my.soliq.uz.

Три адаптера (по одному на смысл документа), общий разбор таблиц. Суммы и номера техники не попадают в payload в открытом виде:
кадастровый номер маскируется, госномер — только хеш в URI и маска в объекте; полные строки таблицы — в raw_enc.
"""

import hashlib
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from lxml import html as lxml_html
from playwright.async_api import TimeoutError as PlaywrightTimeout

from storozh.documents.adapters import browser
from storozh.documents.adapters.soliq_legal import selectors as sel
from storozh.documents.domain.masking import mask_name, mask_plate
from storozh.documents.ports import BrowserSession, RawRecord
from storozh.shared import uri
from storozh.shared.config import settings
from storozh.shared.contracts import NormalizedDocument


def parse_date(text: str | None) -> date | None:
    for fmt in sel.DATE_FORMATS:
        try:
            return datetime.strptime((text or "").strip()[:10], fmt).date()
        except ValueError:
            continue
    return None


def parse_money(text: str | None) -> Decimal | None:
    t = re.sub(r"[^\d,.\-]", "", (text or "").replace(" ", "").replace("\xa0", "")).replace(",", ".")
    try:
        return Decimal(t) if t else None
    except InvalidOperation:
        return None


def parse_table(page_html: str, columns: tuple[str, ...]) -> list[dict[str, str]]:
    """Строки данных таблицы -> словари по именам колонок. Строка «Информация не найдена» (одна ячейка) пропускается."""
    out = []
    for tr in lxml_html.fromstring(page_html).cssselect(sel.ROWS):
        cells = [td.text_content().strip() for td in tr.cssselect("td")]
        if len(cells) >= len(columns):
            out.append(dict(zip(columns, cells, strict=False)))
    return out


def mask_cadastre(number: str) -> str:
    """«10:05:01:02:03:0017» -> «10:05:***:0017»: район и номер участка без середины."""
    parts = [p for p in number.strip().split(":") if p]
    return number.strip() if len(parts) < 4 else f"{parts[0]}:{parts[1]}:***:{parts[-1]}"


def _short_hash(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


async def _page_html(session: BrowserSession, slug: str, source_id: str, ready: str = "table") -> str:
    async with browser.page(session) as page:
        await page.goto(settings.soliq_base_url.rstrip("/") + sel.BASE_PATH + slug, wait_until="domcontentloaded")
        try:
            await page.wait_for_selector(ready, timeout=20_000)
        except PlaywrightTimeout:
            raise browser.SessionExpired(source_id) from None
        if sel.CABINET_MARK not in page.url:
            raise browser.SessionExpired(source_id)
        await page.wait_for_load_state("networkidle")
        return await page.content()


_ISSUER = {"type": "tax", "name": "my.soliq.uz"}


def parse_company(page_html: str) -> dict | None:
    """Шапка и панели учредителей «Состава уставного капитала» -> {inn, name, founders[]}. Нет шапки — None."""
    tree = lxml_html.fromstring(page_html)
    tin = tree.xpath('//*[contains(@class, "Profile_tin")]')
    if not tin:
        return None
    inn = "".join(tin[0].xpath("./span//text()")).strip()
    title = tin[0].getparent().xpath('./*[contains(@class, "Profile_title")]')
    founders = []
    for panel in tree.cssselect(sel.FOUNDER_PANEL):
        name = panel.cssselect(sel.FOUNDER_NAME)
        if not name:
            continue
        row = {"name": name[0].text_content().strip(), "legal_entity": bool(panel.cssselect(sel.FOUNDER_LEGAL_BADGE)),
               "inn": "", "share": "", "amount": ""}
        for r in panel.cssselect(sel.FOUNDER_ROW):
            key = "".join(r.xpath('./*[contains(@class, "Profile_key")]//text()')).strip().lower()
            if key.startswith("инн"):
                row["inn"] = "".join(r.xpath('./*[contains(@class, "Profile_value")][1]//text()')).strip()
            elif key.startswith("доля"):
                row["share"] = "".join(r.xpath('./*[contains(@class, "Profile_value_bold")]//text()')).strip()
                row["amount"] = "".join(r.xpath('./*[@class and contains(@class, "Profile_value") and not(contains(@class, "bold"))]//text()')).strip()
        founders.append(row)
    return {"inn": inn, "name": title[0].text_content().strip() if title else "", "founders": founders}


class SoliqPropertyAdapter:
    """Недвижимость и земельные участки юрлица (kind real_estate_right, URI по кадастровому номеру)."""

    source_id = "soliq.property"
    title = "my.soliq.uz · имущество и земля"
    poll_interval_s = 1800
    complete = True

    async def fetch(self, session: BrowserSession) -> list[RawRecord]:
        out: list[RawRecord] = []
        for slug, kind in sel.PROPERTY_PAGES.items():
            for row in parse_table(await _page_html(session, slug, self.source_id), sel.PROPERTY_COLUMNS):
                if row["cadastre"]:
                    out.append(RawRecord(external_id=row["cadastre"], data={**row, "category": kind}))
        return out

    def normalize(self, raw: RawRecord) -> NormalizedDocument:
        d = raw.data
        masked = mask_cadastre(d["cadastre"])
        land = d["category"] == "land"
        return NormalizedDocument.model_validate({
            "uri": uri.build("kadastr", "object", d["cadastre"]),
            "kind": "real_estate_right",
            "source": self.source_id,
            "title": ("Yer uchastkasi" if land else "Ko‘chmas mulk") + (f": {d['type']}" if d.get("type") else ""),
            "status": "active",
            "owner_role": "party",
            "parties": [{"role": "party", "name_masked": "Юрлицо"}],
            "object": {"type": "land" if land else "real_estate", "id_masked": masked, "label": d.get("type") or None},
            "issued_at": parse_date(d.get("right_date")),
            "issuer": _ISSUER,
            "fields": {"cadastre_value": d.get("cadastre_value"), "area_total_m2": d.get("area_total")},
            "source_ref": {"external_id": masked},
        })


class SoliqVehiclesAdapter:
    """Автотранспорт юрлица (kind vehicle). Госномер — только маска; в URI хеш."""

    source_id = "soliq.vehicles"
    title = "my.soliq.uz · автотранспорт"
    poll_interval_s = 1800
    complete = True

    async def fetch(self, session: BrowserSession) -> list[RawRecord]:
        rows = parse_table(await _page_html(session, sel.VEHICLE_PAGE, self.source_id), sel.VEHICLE_COLUMNS)
        return [RawRecord(external_id=r["plate"], data=r) for r in rows if r["plate"]]

    def normalize(self, raw: RawRecord) -> NormalizedDocument:
        d = raw.data
        key = _short_hash(d["plate"].replace(" ", "").upper())
        return NormalizedDocument.model_validate({
            "uri": uri.build("mvd", "vehicle", key),
            "kind": "vehicle",
            "source": self.source_id,
            "title": f"Avtotransport: {d['name']}" if d.get("name") else "Avtotransport",
            "status": "active",
            "owner_role": "party",
            "parties": [{"role": "party", "name_masked": "Юрлицо"}],
            "object": {"type": "vehicle", "id_masked": mask_plate(d["plate"]), "label": d.get("name") or None},
            "issued_at": parse_date(d.get("registered")),
            "issuer": _ISSUER,
            "fields": {"year": d.get("year")},
            "source_ref": {"external_id": key},
        })


class SoliqTaxesAdapter:
    """Налоговые начисления юрлица (kind tax_assessment): долг > 0 — active, иначе completed."""

    source_id = "soliq.taxes"
    title = "my.soliq.uz · налоги"
    poll_interval_s = 900
    complete = True

    async def fetch(self, session: BrowserSession) -> list[RawRecord]:
        rows = parse_table(await _page_html(session, sel.TAX_PAGE, self.source_id), sel.TAX_COLUMNS)
        return [RawRecord(external_id=f"{r['code']}-{r['date']}", data=r) for r in rows if r["code"]]

    def normalize(self, raw: RawRecord) -> NormalizedDocument:
        d = raw.data
        debt, penalty = parse_money(d.get("debt")), parse_money(d.get("penalty"))
        owes = bool((debt or 0) > 0 or (penalty or 0) > 0)
        return NormalizedDocument.model_validate({
            "uri": uri.build("soliq", "tax", f"{d['code']}-{d['date']}".replace(" ", "")),
            "kind": "tax_assessment",
            "source": self.source_id,
            "title": d.get("name") or f"Soliq {d['code']}",
            "status": "active" if owes else "completed",
            "owner_role": "debtor" if owes else "party",
            "parties": [{"role": "debtor" if owes else "party", "name_masked": "Юрлицо"}],
            "issued_at": parse_date(d.get("date")),
            "issuer": _ISSUER,
            "fields": {k: d.get(k) for k in ("code", "accrued", "paid", "debt", "penalty", "overpaid")},
            "source_ref": {"external_id": raw.external_id},
        })


class SoliqCompanyAdapter:
    """Юрлицо в налоговом реестре: ИНН, название, учредители и доли (kind company, URI по ИНН).

    Учредитель-человек — только маска имени, юрлицо-учредитель — название и ИНН как есть. Какой из учредителей сам владелец
    кабинета, со страницы не видно: роль владельца `party`, доли лежат в fields.founders.
    """

    source_id = "soliq.company"
    title = "my.soliq.uz · юрлицо, учредители и доли"
    poll_interval_s = 1800
    complete = True

    async def fetch(self, session: BrowserSession) -> list[RawRecord]:
        page_html = await _page_html(session, sel.COMPANY_PAGE, self.source_id, ready=sel.COMPANY_READY)
        company = parse_company(page_html)
        return [RawRecord(external_id=company["inn"], data=company)] if company and company["inn"] else []

    def normalize(self, raw: RawRecord) -> NormalizedDocument:
        d = raw.data
        founders = [{
            "name_masked": f["name"] if f["legal_entity"] else mask_name(f["name"]),
            "legal_entity": f["legal_entity"], "inn": f["inn"] if f["legal_entity"] else "",
            "share_percent": parse_money(f["share"]) and str(parse_money(f["share"])),
            "amount": f["amount"],
        } for f in d["founders"]]
        return NormalizedDocument.model_validate({
            "uri": uri.build("soliq", "company", d["inn"]),
            "kind": "company",
            "source": self.source_id,
            "title": d["name"] or f"INN {d['inn']}",
            "status": "active",
            "owner_role": "party",
            "parties": [{"role": "founder", "name_masked": f["name_masked"]} for f in founders],
            "issuer": _ISSUER,
            "fields": {"inn": d["inn"], "founders": founders},
            "source_ref": {"external_id": d["inn"]},
        })
