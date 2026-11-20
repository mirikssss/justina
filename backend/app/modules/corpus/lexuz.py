"""HTTP-клиент lex.uz с дисковым кэшем и паузой между запросами (бережём сайт)."""

import re
import time

import httpx

from app.core.config import settings

BASE = "https://lex.uz"
# otherlang=4 -> страница с параллельным текстом: русский + узбекская латиница
BILINGUAL = "/ru/docs/{lex_id}?otherlang=4"
_last_request = 0.0


def doc_url(lex_id: int, lang: str = "ru", elem_id: int | None = None) -> str:
    prefix = "ru" if lang == "ru" else "uz"
    url = f"{BASE}/{prefix}/docs/{lex_id}"
    return f"{url}#{elem_id}" if elem_id is not None else url


def fetch_bilingual(lex_id: int, refresh: bool = False, delay: float = 1.5) -> str:
    global _last_request
    path = settings.cache_dir / f"{lex_id}_bi.html"
    if path.exists() and not refresh:
        return path.read_text(encoding="utf-8")

    wait = delay - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    resp = httpx.get(
        BASE + BILINGUAL.format(lex_id=lex_id),
        headers={"User-Agent": "Mozilla/5.0 (compatible; justina-legal-rag/0.1)"},
        follow_redirects=True,
        timeout=60,
    )
    _last_request = time.monotonic()
    resp.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(resp.text, encoding="utf-8")
    return resp.text


_RU_LINK = re.compile(r"openUrl\('/ru/docs/(\d+)'\)\"\s+title=\"На русском\"")


def russian_version_id(page: str) -> int | None:
    """Если документ — узбекский оригинал, у русского перевода на lex.uz свой id."""
    m = _RU_LINK.search(page)
    return int(m.group(1)) if m else None
