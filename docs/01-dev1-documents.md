# ТЗ. Разработчик 1 — контекст «Документы»

Версия 1.1 · 21.11.2026 · Общие контракты, URI, схемы событий и архитектура — в `00-project-overview.md` (разделы 9–12).

## 1. Назначение и границы

Контекст собирает всё, что записано на человека в госкабинетах, приводит к единому формату, хранит версии и публикует события об изменениях. Это уровень 1 продукта (агрегация) и вход для уровня 2 (мониторинг).

| В границах контекста | Вне границ (чей контекст) |
| --- | --- |
| Сессии OneID и их проверка | Правила, тревоги, Telegram — «Сторож», Разработчик 3 |
| Адаптеры чтения: `mygov.car_poa`, `mygov.notarial_history`, `vakolat.check` | Действия (отзыв доверенности) — «Сторож», Разработчик 3 |
| Нормализация в `NormalizedDocument` и URI | Резюме, чат, черновики заявлений — «Помощник», Разработчик 2 |
| Ingestion, версии, diff, события `document.*` | Вход на сайт, `shared`, SSE — «Платформа», Разработчик 2 |
| Экраны: лента, карточка документа, «Источники» | Каркас и UI-кит MyGov — Разработчик 3 |

## 2. Зависимости

| Получаю | От кого |
| --- | --- |
| `shared.outbox.publish`, `shared.crypto`, `shared.uri`, `shared.auth.current_citizen` | Разработчик 2 |
| UI-кит MyGov (`web/components/mygov`, страница `/kit`) | Разработчик 3 |

| Отдаю | Кому |
| --- | --- |
| События `document.created`, `document.changed`, `document.status_changed`, `document.disappeared`, `source.session_expired` | «Сторож», «Помощник» |
| `documents.public`: `get_document`, `request_refresh`, `SessionProvider` | «Сторож» (исполнитель), «Помощник» |
| REST `/documents`, `/sources` | Фронтенд |

## 3. Use cases

**UC-D1. Подключить аккаунт.** Актор: участник команды.
1. Оператор запускает `storozh connect --citizen <id>`.
2. Открывается видимый Chromium на id.egov.uz.
3. Человек сам вводит логин и SMS-код.
4. Система проверяет, что открылся кабинет, шифрует storage state и сохраняет в `source_sessions`.
5. Источники гражданина переходят в `enabled`.
- Альтернатива: вход не удался или закрыто окно → ничего не сохраняется, в консоли понятная ошибка.

**UC-D2. Обнаружить новый документ.** Актор: планировщик.
1. По расписанию адаптер берёт сессию и читает страницу кабинета.
2. `normalize` приводит каждую запись к `NormalizedDocument`.
3. Сборщик отправляет `SourceSnapshot` в Ingestion API.
4. Ingestion находит новый URI → документ, версия 1, событие `document.created` в одной транзакции.
- Результат: документ в ленте и событие в outbox не позже чем через 30 с после появления в кабинете.

**UC-D3. Обнаружить изменение.** Как UC-D2, но URI уже есть и хеш другой → версия N+1, `document.changed`. Если поменялся `status` → дополнительно `document.status_changed`.

**UC-D4. Запись пропала.** Два полных снимка (`complete: true`) подряд без URI → `document.disappeared`, статус документа не меняется.

**UC-D5. Посмотреть ленту и карточку.** Актор: гражданин. Открывает «Мои документы» → видит все документы, фильтрует, открывает карточку с реквизитами и историей версий.

**UC-D6. Сравнить версии.** В карточке выбирает версию → видит изменённые поля «было → стало».

**UC-D7. Обновить сейчас.** Гражданин жмёт «Обновить» на странице «Источники» или «Сторож» вызывает `request_refresh` → внеочередной опрос источника документа.

**UC-D8. Сессия истекла.** Проверка раз в 5 минут не нашла кабинет → статус `expired`, событие `source.session_expired`, опрос этого гражданина остановлен до UC-D1.

## 4. Функциональные требования

| ID | Требование | Приоритет |
| --- | --- | --- |
| FR-D-01 | CLI `storozh connect` создаёт и шифрует сессию OneID; пароль и SMS-код вводятся только на id.egov.uz | Must |
| FR-D-02 | Проверка живости сессии раз в 5 мин, при отказе — `source.session_expired` | Must |
| FR-D-03 | Адаптер `mygov.car_poa`: e-доверенности на авто, выданные человеком и ему (номер, дата, авто, другая сторона, срок, статус), опрос 20 с, `complete: true` | Must |
| FR-D-04 | Адаптер `mygov.notarial_history`: выбор года, решение арифметической капчи (текст — вычисление; картинка — Tesseract), опрос раз в 10 мин и по запросу | Must |
| FR-D-05 | Адаптер `vakolat.check`: статус каждой известной доверенности по номеру в публичном реестре, раз в 5 мин | Should |
| FR-D-06 | Нормализация в `NormalizedDocument`: ПИНФЛ — только HMAC, ФИО и госномер — маски, полный сырой снимок — в `raw_enc` | Must |
| FR-D-07 | Ingestion: проверка схемы и HMAC-подписи, идемпотентность по `snapshot_id`, upsert по `uri`, новая версия только при новом хеше | Must |
| FR-D-08 | Версия, событие и запись outbox — одной транзакцией через `shared.outbox.publish` | Must |
| FR-D-09 | `document.disappeared` — после двух полных снимков без записи | Should |
| FR-D-10 | Diff версий: список `{field, from, to}` | Must |
| FR-D-11 | `SessionProvider.get` выдаёт сессию под `pg_advisory_lock` по аккаунту: опрос и действие не идут параллельно | Must |
| FR-D-12 | `request_refresh(document_id)` — внеочередной опрос источника документа | Must |
| FR-D-13 | Статус источника в `documents.sources`: `last_poll_at`, `last_ok_at`, `last_error` | Must |
| FR-D-14 | Лента `/documents`: вкладки по типу, фильтр по статусу, поиск, метка «новое», обновление по SSE | Must |
| FR-D-15 | Карточка `/documents/[id]`: реквизиты, стороны, объект, статус, история версий; слоты `<DocumentGuard/>` (Р3) и `<DocumentAssistant/>` (Р2) | Must |
| FR-D-16 | Страница `/sources`: «последний опрос N с назад», статус, «Обновить» | Must |

## 5. Нефункциональные требования

| ID | Требование |
| --- | --- |
| NFR-D-01 | Задержка от появления записи в кабинете до события: ≤ 30 с для `mygov.car_poa`, ≤ 10 мин для истории нотариальных действий |
| NFR-D-02 | Повторный снимок без изменений не создаёт ни версии, ни события |
| NFR-D-03 | Ошибка одного адаптера не останавливает остальные; пауза при ошибках 20 → 40 → 80 с … до 10 мин |
| NFR-D-04 | Не чаще одного запроса в 20 с на источник, разброс интервала ±3 с, одна сессия на аккаунт |
| NFR-D-05 | В `payload` и логах нет ПИНФЛ, номера паспорта, полного ФИО и госномера |
| NFR-D-06 | Логи structlog в JSON с `request_id`; `/healthz`; по каждому источнику видно `last_ok_at` |
| NFR-D-07 | Все селекторы страницы в одном файле `selectors.py` на адаптер; парсеры покрыты тестами на HTML-фикстурах |

## 6. Ограничения

- Публичного API у Notarius и кабинетов MyGov нет: читаем только то, что человек видит в своём кабинете, его же сессией.
- Только аккаунты участников команды, с их согласия.
- История нотариальных действий показывает только совершённые действия, требует выбор года и капчу.
- Вёрстка кабинетов может поменяться в любой момент — отсюда фикстуры и тесты.
- Точные адреса страниц и запросов снимаем в DevTools (HAR) в первый час; они не документированы.

## 7. Данные — схема `documents`

| Таблица | Поля | Заметки |
| --- | --- | --- |
| `sources` | `source_id`, `citizen_id`, `enabled`, `last_poll_at`, `last_ok_at`, `last_error` | Одна строка на источник гражданина |
| `source_sessions` | `citizen_id`, `provider` (`oneid`), `state_enc`, `expires_at`, `status` (`active`, `expired`) | Шифрование — `shared.crypto` |
| `documents` | `uri` unique, `citizen_id`, `kind`, `source`, `status`, `owner_role`, `title`, `current_version`, `first_seen_at`, `last_seen_at`, `missing_count` | Одна строка на документ |
| `document_versions` | `document_id`, `version_no`, `content_hash`, `payload jsonb`, `raw_enc`, `snapshot_id`, `fetched_at` | Unique (`document_id`, `version_no`); только INSERT |
| `snapshots` | `snapshot_id` PK, `source`, `citizen_id`, `received_at`, `documents_count` | Для идемпотентности |

RLS по `citizen_id` на всех таблицах. Роль `documents_rw` пишет только в свою схему.

## 8. REST API

| Метод и путь | Ответ | Заметки |
| --- | --- | --- |
| `GET /documents?kind&status&q&cursor` | `{items: DocumentListItem[], next_cursor}` | Сортировка по `updated_at` desc |
| `GET /documents/{id}` | `DocumentDetail` | `NormalizedDocument` + `id`, `current_version`, `versions_count`, `first_seen_at`, `last_seen_at` |
| `GET /documents/{id}/versions` | `[{version_no, content_hash, fetched_at, changed_fields}]` | |
| `GET /documents/{id}/versions/{n}/diff` | `[{field, from, to}]` | Сравнение с версией n−1 |
| `GET /sources` | `[{source_id, title, status, last_poll_at, last_ok_at, last_error}]` | `status`: `ok`, `error`, `expired`, `disabled` |
| `POST /sources/{source_id}/refresh` | `202` | Не чаще раза в 20 с |
| `POST /internal/ingest/snapshots` | `202 {new_versions}` | HMAC в `X-Signature` + `X-Timestamp`, окно 5 мин |
| `POST /internal/documents/{id}/refresh` | `202` | HMAC |

```json
// DocumentListItem
{"id": "uuid", "uri": "uz:notarius:poa:{№}", "kind": "poa_car", "title": "Доверенность на автомобиль",
 "status": "active", "owner_role": "principal", "counterparty_masked": "Б***р К.",
 "issued_at": "2026-11-21", "is_new": true, "updated_at": "2026-11-21T10:00:20+05:00"}
```

Ошибки — `application/problem+json`. Все ответы несут `X-Request-Id`.

## 9. События (шина `shared.outbox`)

| Публикую | Когда | `dedupe_key` |
| --- | --- | --- |
| `document.created` | Новый URI | `{uri}:1:created` |
| `document.changed` | Новый хеш | `{uri}:{version_no}:changed` |
| `document.status_changed` | Изменился `status` | `{uri}:{version_no}:status` |
| `document.disappeared` | Два полных снимка без записи | `{uri}:{snapshot_id}:gone` |
| `source.session_expired` | Сессия не прошла проверку | `{citizen_id}:{provider}:{expired_at}` |

Конверт события и `data` — в общем файле, раздел 10. Потребляю: ничего.

## 10. Порты

```python
class SourceAdapter(Protocol):
    source_id: str                    # "mygov.car_poa"
    poll_interval_s: int
    async def fetch(self, session: BrowserSession) -> list[RawRecord]: ...
    def normalize(self, raw: RawRecord) -> NormalizedDocument: ...

# documents/public.py
class SessionProvider(Protocol):
    @asynccontextmanager
    async def get(self, citizen_id: UUID, provider: str = "oneid") -> AsyncIterator[BrowserSession]: ...
async def get_document(document_id: UUID) -> NormalizedDocument: ...
async def request_refresh(document_id: UUID) -> None: ...
```

## 11. Структура

```
backend/storozh/documents/
  domain/          # NormalizedDocument, hashing, diff
  ports.py  public.py  service.py  api.py  worker.py  cli.py
  adapters/
    mygov_car_poa/      adapter.py  selectors.py  tests/fixtures/*.html
    mygov_notarial/     adapter.py  selectors.py  captcha.py  tests/fixtures/*.html
    vakolat/            adapter.py
    db/                 models.py  repo.py
web/app/documents/  web/app/sources/
```

## 12. Definition of Done

- [ ] Доверенность, выданная в my.gov.uz на живом аккаунте, появляется в ленте за 30 с; её отзыв меняет статус за 30 с.
- [ ] Повторный снимок без изменений не создаёт версии и события (тест).
- [ ] Тест-регулярка: в `payload` нет ПИНФЛ (14 цифр), паспорта, телефона +998.
- [ ] Парсеры трёх источников покрыты тестами на фикстурах.
- [ ] `SessionProvider` не даёт двум процессам одну сессию одновременно (тест).
- [ ] Экраны лента, карточка, «Источники» собраны из компонентов `/kit`.
- [ ] `import-linter` зелёный: нет импортов из чужих контекстов, кроме `public.py` и `shared`.

## 13. Открытые вопросы

- Адреса страниц и формат ответов my.gov.uz — снять HAR в первый час.
- Видна ли в истории нотариальных действий исполнительная надпись должнику.
- Есть ли у Vakolat.uz ограничение на частоту проверки по номеру.
