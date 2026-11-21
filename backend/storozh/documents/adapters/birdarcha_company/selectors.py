"""Birdarcha.uz (Business Registration, new.birdarcha.uz) — заявки на регистрацию юрлица. Снято с живого портала 21.11.2026.

Вход общий через OneID; токен портал держит в localStorage (`persist:auth`), поэтому storage state сессии должен включать
этот origin (см. `documents connect`). Данные идут REST-ом на api.birdarcha.uz с Bearer-токеном, но токен мы не извлекаем:
читаем отрисованную страницу, запросы делает сама страница.

Список: /applications/LEGAL_ENTITY/list — таблица Ant Design. Колонки по порядку:
№ | Ariza raqami (номер заявки) | Nomi (название) | STIR (ИНН) | Ariza turi (тип заявки) | Holati (статус) | Sana (дата).
Строки без ссылок; страница заявки: /application/LEGAL_ENTITY_REGISTRATION/view/{номер}. Вкладка «Jismoniy shaxs» — ИП/самозанятые,
здесь не читаем (TODO). Интерфейс на uz; статусы и типы на ru/en не проверены. Поменялась вёрстка — правим этот файл.
"""

LIST_PATH = "/applications/LEGAL_ENTITY/list"
VIEW_PATH = "/application/LEGAL_ENTITY_REGISTRATION/view/{number}"
ROWS = "tr.ant-table-row"
READY = ".ant-table-tbody tr"  # есть и строка «нет данных», поэтому пустой список не путается с выходом из системы
COLUMNS = ("no", "application_no", "name", "inn", "application_type", "status_text", "date")
DATE_FORMAT = "%d.%m.%Y"
STATUS = [  # (подстрока в нижнем регистре, статус)
    ("muvaffaqiyatli", "completed"), ("успешно", "completed"), ("successful", "completed"),
]
