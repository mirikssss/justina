"""Налоговый кабинет юрлица my.soliq.uz (/legal/cabinet/profile-new/...). Снято с живого портала 21.11.2026 (компания без имущества:
таблицы пустые, строка «Информация не найдена», но заголовки и адреса настоящие). SPA на React, данные через /api/cabinet-profile-api/...
(не читаем напрямую: читаем отрисованные таблицы).

Страницы и колонки <table> (порядок <td> в строке):
- general_info/nonresidentialproperty «Недвижимое имущество»: № | Адрес | Кадастровый номер | Тип | Кадастровая стоимость | Общая площадь(м2) |
  Присоединённая территория (м2) | Производственная площадь | Дата возникновения права собственности
- general_info/landplots «Земельные участки»: те же колонки
- general_info/automobiles «Автотранспорт»: № | Наименование | Номер автотранспорта | Год производства | Дата регистрации
  (порядок колонок предположение: на живом аккаунте строк не было)
- general_info/taxes «Налоги»: № | Код | Наименование | Начислено | Оплачено | Задолженность | Пеня | Переплата | Дата
Не разобраны: «Уставной капитал»/«Учредители» (доли, это роль человека в юрлице), «Сотрудники», «Инкассовые поручения».
Кабинет физлица (налоги на имущество и землю человека) — другая часть my.soliq.uz, не смотрели.
Поменялась вёрстка — правим этот файл и фикстуры.
"""

BASE_PATH = "/legal/cabinet/profile-new/general_info/"
CABINET_MARK = "/legal/cabinet"  # в адресе после загрузки; иначе нас вернули на вход
ROWS = "table tbody tr"

PROPERTY_PAGES = {"nonresidentialproperty": "nonresidential", "landplots": "land"}
PROPERTY_COLUMNS = ("no", "address", "cadastre", "type", "cadastre_value", "area_total", "area_attached", "area_industrial", "right_date")
VEHICLE_PAGE = "automobiles"
VEHICLE_COLUMNS = ("no", "name", "plate", "year", "registered")
TAX_PAGE = "taxes"
TAX_COLUMNS = ("no", "code", "name", "accrued", "paid", "debt", "penalty", "overpaid", "date")
DATE_FORMATS = ("%d.%m.%Y", "%Y-%m-%d")

# «Состав уставного капитала»: general_info/chartercapital. CSS-модули с хешем в конце класса — берём по префиксу.
COMPANY_PAGE = "chartercapital"
COMPANY_READY = '[class*="Profile_tin"]'            # шапка: «ИНН <span>…</span>», рядом [class*="Profile_title"] — название
FOUNDER_PANEL = '[class*="Profile_info_panel"]'      # одна панель на учредителя
FOUNDER_NAME = '[class*="Profile_title"]'
FOUNDER_LEGAL_BADGE = '[class*="Profile_badge"]'     # значок «Юридическое лицо» только у организаций
FOUNDER_ROW = '[class*="Profile_row"]'               # строки «ИНН» и «Доля»: [class*="Profile_key"] / _value_bold (процент) / _value (сумма)
