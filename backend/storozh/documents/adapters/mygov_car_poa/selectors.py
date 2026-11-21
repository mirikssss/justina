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

LIST_URL = "https://my.gov.uz/ru/user/requests"
LOGIN_PATH = "/login"  # редирект сюда = сессия истекла
LOGGED_IN_MARK = ".sbUser"  # блок профиля в боковой панели есть только в залогиненном кабинете
LIST_READY = f'{LOGGED_IN_MARK}, a[href^="/ru/user/requests/"]'  # список рисуется после расшифровки ответа

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

# Нет в списке, лежит в iframe заявки — пока None (TODO по HAR/DOM iframe):
#   plate, vehicle_model, counterparty_name, valid_until
