"""ТЕСТОВЫЙ МАКЕТ my.gov.uz: страницы «Мои заявки» с той же разметкой, что у живого портала.

Зачем: ни у кого в команде нет аккаунта с автомобилем и e-доверенностью, а настоящий адаптер mygov.car_poa
надо прогонять целиком (Playwright -> разбор карточек -> ingest -> события). Макет отдаёт карточки в разметке,
снятой с живого /ru/user/requests, а подробности заявки — во вложенном iframe, как на портале.

Что в макете выдумано, а не снято с живого портала (на странице макета это подписано):
- разметка iframe с подробностями (атрибуты data-field) — у живого портала она неизвестна;
- статус «Аннулировано» в списке: у живого портала отзыв в списке заявок не виден (его ловит vakolat.check).

Запуск: python -m storozh documents mockportal  (порт 8765). Управление: страница /_mock или POST /_mock/issue,
POST /_mock/revoke/{номер}. Состояние в памяти процесса. Все данные вымышленные.
"""

from datetime import date, timedelta
from html import escape

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

POA_TITLE = "Выдача электронной доверенности физическим лицам на управление автотранспортным средством"
STATUS_TEXT = {"active": "Обработано", "revoked": "Аннулировано"}

_requests: dict[str, dict] = {}
_counter = 900_000_100


def reset() -> None:
    """Начальное состояние: одна справка, доверенностей нет."""
    global _counter
    _requests.clear()
    _counter = 900_000_100
    _requests["900000001"] = {"id": "900000001", "title": "Справка о трудовой деятельности", "status": "active",
                              "issued": date(2026, 11, 12), "channel": "app", "poa": None}


reset()
app = FastAPI(title="Макет my.gov.uz (тестовый)")


def _card(r: dict) -> str:
    icon, label = ("smartphone", "Приложение MyGov") if r["channel"] == "app" else ("globe", "my.gov.uz")
    return f"""
  <a href="/ru/user/requests/{r['id']}" class="text-left rounded p-4 flex flex-col">
    <div class="flex items-start justify-between gap-3">
      <div class="text-gray-500 text-sm font-light italic">#{r['id']}</div>
      <span class="inline-flex items-center rounded-full px-3 py-1 gap-1 text-[12px]"><span class="iconify i-lucide:circle-check"></span>{STATUS_TEXT[r['status']]}</span>
    </div>
    <div class="font-semibold text-gray-900">{escape(r['title'])}</div>
    <div class="flex items-center text-[14px] gap-3 mt-auto">
      <div class="flex items-center gap-2"><span class="iconify i-lucide:calendar"></span>{r['issued']:%d.%m.%Y}</div>
      <div class="flex items-center gap-2"><span class="iconify i-lucide:{icon}"></span>{label}</div>
    </div>
  </a>"""


def _page(body: str) -> str:
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Мои заявки (МАКЕТ)</title></head><body>
<div style="background:#fde68a;padding:8px;font:14px sans-serif">ТЕСТОВЫЙ МАКЕТ my.gov.uz. Данные вымышленные. <a href="/_mock">Управление</a></div>
<div class="sbUser"><a href="/ru/user">Тестовый Пользователь</a></div>{body}</body></html>"""


@app.get("/ru/user/requests", response_class=HTMLResponse)
def requests_list() -> str:
    cards = "".join(_card(r) for r in reversed(list(_requests.values())))
    return _page(f'<h1>Мои заявки</h1><a href="/ru/user/requests/draft" class="tab">Черновики</a><div class="grid">{cards}</div>')


@app.get("/ru/user/requests/{request_id}", response_class=HTMLResponse)
def request_page(request_id: str) -> str:
    if request_id not in _requests:
        raise HTTPException(404)
    return _page(f'<h2>{escape(_requests[request_id]["title"])}</h2><div class="iframe"><iframe src="/bpm/requests/{request_id}"></iframe></div>')


@app.get("/bpm/requests/{request_id}", response_class=HTMLResponse)
def request_details(request_id: str) -> str:
    r = _requests.get(request_id)
    if r is None:
        raise HTTPException(404)
    p = r["poa"] or {}
    rows = "".join(f'<tr><th>{k}</th><td data-field="{k}">{escape(str(v))}</td></tr>' for k, v in p.items())
    return f"<!doctype html><meta charset=utf-8><body><p>МАКЕТ: разметка этого окна выдумана</p><table>{rows}</table></body>"


class Issue(BaseModel):
    plate: str = "01 A 123 BC"
    vehicle: str = "Chevrolet Cobalt"
    counterparty: str = "Каримов Бахтиёр Алишерович"
    valid_days: int = 30


@app.post("/_mock/issue")
def issue(body: Issue | None = None) -> dict:
    """Оформить доверенность на авто (появится новой карточкой «Обработано»)."""
    global _counter
    body = body or Issue()
    _counter += 1
    number = str(_counter)
    today = date.today()
    _requests[number] = {
        "id": number, "title": POA_TITLE, "status": "active", "issued": today, "channel": "web",
        "poa": {"plate": body.plate, "vehicle_model": body.vehicle, "counterparty_name": body.counterparty,
                "direction": "Выдана мной", "valid_until": f"{today + timedelta(days=body.valid_days):%d.%m.%Y}"},
    }
    return {"number": number}


@app.post("/_mock/revoke/{number}")
def revoke(number: str) -> dict:
    r = _requests.get(number)
    if r is None or r["poa"] is None:
        raise HTTPException(404, "доверенность не найдена")
    r["status"] = "revoked"
    return {"number": number, "status": "revoked"}


@app.post("/_mock/reset")
def reset_state() -> dict:
    reset()
    return {"ok": True}


@app.get("/_mock", response_class=HTMLResponse)
def control() -> str:
    return """<!doctype html><meta charset=utf-8><title>Макет: управление</title><body style="font:16px sans-serif;padding:24px">
<h1>Макет my.gov.uz: управление</h1><p>Вымышленные данные для разработки.</p>
<button onclick="act('/_mock/issue')">Оформить доверенность на авто</button>
<button onclick="act('/_mock/reset')">Сбросить</button>
<p>Отозвать: <input id=n placeholder="номер заявки"> <button onclick="act('/_mock/revoke/'+n.value)">Аннулировать</button></p>
<pre id=out></pre><script>async function act(u){const r=await fetch(u,{method:'POST'});out.textContent=await r.text()}</script>"""
