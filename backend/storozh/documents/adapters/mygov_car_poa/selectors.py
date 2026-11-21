"""Все селекторы и адреса страницы e-доверенностей на авто — только здесь (NFR-D-07).

Что выяснено на живом my.gov.uz (21.11.2026, Nuxt + gRPC-Web):
- Данные идут через /api/<сервис>/<Метод> бинарным protobuf, ответ зашифрован (x-gw-enc), запрос подписан.
  Читать API напрямую нельзя — читаем отрисованный DOM страницы «Мои заявки».
- Карточка заявки — <a href="/ru/user/requests/<id>">: номер «#<id>», статус-бейдж, название услуги,
  дата и канал подачи. Подробности заявки открываются во вложенном iframe (BPM) — здесь не разбираем.
- В «Мои заявки» попадают только заявки самого человека, то есть доверенности, выданные им.
  Доверенности «выданные мне» этот список не покажет: нужен второй источник (TODO по HAR).

Поменялась вёрстка — правим этот файл и фикстуры в tests/fixtures/, ядро не трогаем.
"""

LIST_PATH = "/ru/user/requests"  # база — settings.mygov_base_url
LOGIN_PATH = "/login"  # редирект сюда = сессия истекла
LOGGED_IN_MARK = ".sbUser"  # блок профиля в боковой панели есть только в залогиненном кабинете
CARD = 'a[href^="/ru/user/requests/"]:not([href$="/draft"])'  # карточка заявки; рисуется после расшифровки ответа API
LIST_READY = f"{LOGGED_IN_MARK}, {CARD}"

ROW = 'a[href^="/ru/user/requests/"]'
HREF_PREFIX = "/ru/user/requests/"
SKIP_HREF_SUFFIXES = ("/draft",)  # вкладка «Черновики» — не заявка
TITLE_MARK = "доверенност"  # подстрока названия услуги (нижний регистр): отбираем e-доверенности

FIELDS = {  # селектор внутри карточки -> ключ RawRecord.data
    "number": "div.italic",
    "status_text": "span.rounded-full",
    "title": "div.font-semibold",
}
DATE_ICON = "span.i-lucide\\:calendar"  # дата подачи — текст родителя иконки календаря
CHANNEL_ICONS = {"i-lucide:smartphone": "app", "i-lucide:globe": "web"}

# Подробности заявки лежат в iframe. ВНИМАНИЕ: разметка iframe живого портала НЕ снята (нет аккаунта с доверенностью);
# DETAIL_FIELDS описывает разметку макета (documents/mockportal). Когда появится живая — поправить только этот словарь.
DETAIL_IFRAME = "iframe"
DETAIL_FIELDS = {
    "plate": '[data-field="plate"]',
    "vehicle_model": '[data-field="vehicle_model"]',
    "counterparty_name": '[data-field="counterparty_name"]',
    "direction": '[data-field="direction"]',
    "valid_until": '[data-field="valid_until"]',
}
