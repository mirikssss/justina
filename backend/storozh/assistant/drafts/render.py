"""HTML-шаблон юриста + реквизиты из документа -> PDF (WeasyPrint). Модель здесь не участвует (FR-A-09)."""

from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from storozh.shared.contracts import NormalizedDocument

TEMPLATES = Path(__file__).with_name("templates")
_env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html"]))


def _fmt(d: date | None) -> str | None:
    return d.strftime("%d.%m.%Y") if d else None


def context(doc: NormalizedDocument, applicant: dict[str, Any], lang: str) -> dict[str, Any]:
    """Реквизиты для шаблона. ФИО и ПИНФЛ заявителя — только здесь, в PDF; в модель они не попадают."""
    obj = None
    if doc.object:
        obj = " ".join(x for x in (doc.object.label, doc.object.id_masked) if x) or None
    counterparty = ", ".join(p.name_masked for p in doc.parties if p.role != doc.owner_role) or None
    return {
        "lang": lang,
        "today": date.today().strftime("%d.%m.%Y"),
        "notary": (doc.issuer.name if doc.issuer and doc.issuer.name else None) or "________________",
        "applicant": {"name": applicant.get("display_name") or "________________", "pinfl": applicant.get("pinfl")},
        "doc": {"title": doc.title, "number": doc.source_ref.external_id, "issued_at": _fmt(doc.issued_at),
                "object": obj, "counterparty": counterparty},
    }


def render_html(draft_type: str, ctx: dict[str, Any]) -> str:
    return _env.get_template(f"{draft_type}.html").render(**ctx)


def render_pdf(draft_type: str, ctx: dict[str, Any]) -> bytes:
    from weasyprint import HTML  # тяжёлый импорт — только когда нужен PDF

    return HTML(string=render_html(draft_type, ctx), base_url=str(TEMPLATES)).write_pdf()
