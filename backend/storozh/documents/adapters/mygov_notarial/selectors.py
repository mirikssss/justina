"""История нотариальных действий (my.gov.uz, услуга №693). Снято с живого портала 21.11.2026.

Услуга рендерится в iframe из старого портала: https://oldmy.gov.uz:4433/ru/notary-history (Yii2, форма POST с CSRF).
Playwright работает с cross-origin iframe: открываем https://my.gov.uz/ru/service/get/693#notary-history и берём frame
по url «oldmy.gov.uz». Сессия my.gov.uz для oldmy.gov.uz нужна ли отдельно — не проверено (страница открылась без входа).

Форма:
- год:  select#notaryhistory-year  (name NotaryHistory[year]), варианты 2019 … 2026 («Выберите год» — пустой)
- код проверки: input#notaryhistory-verifycode (name NotaryHistory[verifyCode], type=number), рядом img#captcha-image —
  арифметическое действие в картинке («Введите ответ арифметического действия»)
- кнопка: button#butt_for_sub «Проверить»
Услуга показывает совершённые нотариальные действия с 2019 года, из базы Минюста в реальном времени.

НЕ СНЯТО: разметка страницы результата (таблица действий). Капчу прошёл бы человек; автоматически мы её не проходим.
Поменялась вёрстка — правим этот файл и фикстуры.
"""

SERVICE_URL = "https://my.gov.uz/ru/service/get/693#notary-history"
IFRAME_URL_MARK = "oldmy.gov.uz"
DIRECT_URL = "https://oldmy.gov.uz:4433/ru/notary-history"
YEAR_SELECT = "select#notaryhistory-year"
CAPTCHA_IMG = "img#captcha-image"
CAPTCHA_INPUT = "input#notaryhistory-verifycode"
SUBMIT = "button#butt_for_sub"
YEARS = tuple(range(2019, 2027))
