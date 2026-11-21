"""Синтетические таблицы по реальным заголовкам my.soliq.uz (21.11.2026): значения вымышлены."""

EMPTY = """<table><thead><tr><th>№</th><th>Адрес</th></tr></thead><tbody><tr><td colspan="9">Информация не найдена</td></tr></tbody></table>"""

PROPERTY = """<table><thead><tr><th>№</th><th>Адрес</th><th>Кадастровый номер</th><th>Тип</th><th>Кадастровая стоимость</th>
<th>Общая площадь(м2)</th><th>Присоединённая территория (м2)</th><th>Производственная площадь</th><th>Дата возникновения права собственности</th></tr></thead>
<tbody><tr><td>1</td><td>г. Ташкент, ул. Тестовая, 1</td><td>10:05:01:02:03:0017</td><td>Нежилое помещение</td><td>150 000 000</td><td>85.5</td><td>0</td><td>0</td><td>01.03.2026</td></tr></tbody></table>"""

VEHICLES = """<table><thead><tr><th>№</th><th>Наименование</th><th>Номер автотранспорта</th><th>Год производства</th><th>Дата регистрации</th></tr></thead>
<tbody><tr><td>1</td><td>Chevrolet Cobalt</td><td>01 A 123 BC</td><td>2022</td><td>15.06.2024</td></tr></tbody></table>"""

TAXES = """<table><thead><tr><th>№</th><th>Код</th><th>Наименование</th><th>Начислено</th><th>Оплачено</th><th>Задолженность</th><th>Пеня</th><th>Переплата</th><th>Дата</th></tr></thead>
<tbody><tr><td>1</td><td>10101</td><td>Налог на прибыль</td><td>1 000 000</td><td>400 000</td><td>600 000</td><td>0</td><td>0</td><td>20.11.2026</td></tr>
<tr><td>2</td><td>10202</td><td>НДС</td><td>500 000</td><td>500 000</td><td>0</td><td>0</td><td>0</td><td>20.10.2026</td></tr></tbody></table>"""

COMPANY = """<div class="Profile_header__9rE8l"><div class="Profile_tin__vq+7w">ИНН <span>300000001</span></div><div class="Profile_title__a1">"EXAMPLE CO 1" MCHJ</div></div>
<div class="Profile_chaptercapital__rKccD"><div class="Profile_space__x">
<div><div class="Profile_info_panel__a"><div class="Profile_header__b"><span></span><span class="Profile_title__c">IVANOV IVAN PETROVICH</span></div><div class="Profile_content__d">
<div class="Profile_row__e"><div class="Profile_key__f">ИНН</div><div class="Profile_value__g"></div></div>
<div class="Profile_row__e"><div class="Profile_key__f">Доля</div><div class="Profile_value_bold__h">60%</div><div class="Profile_value__g">600 000.00 сум</div></div></div></div></div>
<div><div class="Profile_info_panel__a"><div class="Profile_header__b"><span></span><span class="Profile_title__c">"PARTNER CO" MCHJ</span><div class="Profile_badge__i">Юридическое лицо</div></div><div class="Profile_content__d">
<div class="Profile_row__e"><div class="Profile_key__f">ИНН</div><div class="Profile_value__g">300000999</div></div>
<div class="Profile_row__e"><div class="Profile_key__f">Доля</div><div class="Profile_value_bold__h">40%</div><div class="Profile_value__g">400 000.00 сум</div></div></div></div></div>
</div></div>"""
