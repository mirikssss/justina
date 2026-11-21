# ТЗ. Разработчик 3 — контекст «Сторож» и фронтенд MyGov

Версия 1.1 · 21.11.2026 · Общие контракты, URI, схемы событий и архитектура — в `00-project-overview.md` (разделы 9–12).

## 1. Назначение и границы

Каркас MyGov уже готов. Дальше — контекст «Сторож»: событие превращается в тревогу, тревога — в подтверждённое действие, а результат действия виден в самом источнике. Это уровень 3 продукта (защита) и уведомления уровня 2.

| В границах | Вне границ (чей контекст) |
| --- | --- |
| Каркас MyGov, UI-кит, страница `/kit`, навигация по всем разделам | Лента, карточка, «Источники» — Разработчик 1 (на твоём ките) |
| Правила G1–G7, тревоги | Сбор данных и сессии OneID — Разработчик 1 |
| Telegram-бот: привязка, тревоги, кнопки, коды | Тексты объяснений, резюме, PDF-заявления — Разработчик 2 |
| Действия: подтверждение, исполнитель `revoke_car_poa`, проверка по источнику | Вход на сайт, `shared`, SSE, журнал аудита — Разработчик 2 |
| Семья и согласия | |
| Экраны: уведомления, `<DocumentGuard/>`, подтверждение, ход действия, семья | |

## 2. Зависимости

| Получаю | От кого |
| --- | --- |
| События `document.*`, `source.session_expired` | Разработчик 1 |
| `documents.public.SessionProvider`, `get_document`, `request_refresh` | Разработчик 1 |
| `assistant.public.explain_alert`, `draft_application` | Разработчик 2 |
| `shared.outbox`, `shared.crypto`, `shared.auth`, `shared.audit`, `platform.public.bind_login` | Разработчик 2 |

| Отдаю | Кому |
| --- | --- |
| События `alert.created`, `action.updated` | Фронтенд через SSE |
| `<DocumentGuard/>` для карточки документа | Разработчик 1 вставляет в карточку |
| UI-кит и каркас | Разработчики 1 и 2 |

## 3. Use cases

**UC-G1. Получить тревогу.** Актор: гражданин.
1. Приходит `document.created` с `kind=poa_car`, `owner_role=principal`.
2. Срабатывает G1, создаётся тревога `critical`.
3. `explain_alert` за ≤ 5 с даёт объяснение; не успел — шаблонный текст, объяснение дописывается правкой сообщения.
4. В Telegram: «От вашего имени выдана доверенность на авто ***45. Это вы?» и кнопки «Bu men emasman / Это не я», «Это я», «Открыть».
- Результат: сообщение в Telegram ≤ 5 с после события.

**UC-G2. «Это я».** Тревога получает `verdict=me`, статус `closed`, в аудит.

**UC-G3. «Это не я» → отзыв.**
1. В Telegram «Это не я» → ссылка на карточку документа на сайте.
2. На сайте (сессия обязательна) «Отозвать доверенность» → `POST /guard/actions` с `Idempotency-Key`.
3. В Telegram приходит 6-значный код. Человек вводит его на сайте → `POST /guard/actions/{id}/confirm`.
4. Исполнитель берёт сессию из `SessionProvider`, проходит аннулирование в my.gov.uz, сохраняет скриншот результата.
5. `request_refresh` → ждём `document.status_changed` со статусом `revoked`, до 120 с.
6. Действие `done`, в Telegram и на экране: «Отозвано. Подтверждено источником».
- Альтернативы: код неверный 3 раза → `expired`; исполнитель упал до отправки формы → один автоматический повтор; после отправки формы — никогда; нет подтверждения источника за 120 с → `failed`, «проверьте кабинет», скриншот приложен.

**UC-G4. Заявление по ст. 31.** Тревога G2 → «Скачать заявление по ст. 31» → `assistant.public.draft_application("art31_postpone", …)` → PDF.

**UC-G5. Привязать Telegram.** На сайте «Подключить Telegram» → ссылка `t.me/<bot>?start=link_<token>` (10 мин) → бот сохраняет `chat_id_enc`.

**UC-G6. Вход через бота.** Бот получает `/start login_<nonce>` → вызывает `platform.public.bind_login` → отправляет человеку ссылку входа.

**UC-G7. Семья.** Владелец выдаёт доступ родственнику по коду с правами `read_documents` и/или `receive_alerts`; родственник видит ленту только для чтения; каждый просмотр — в аудит; отзыв доступа действует сразу. G7 копирует `critical`-тревоги родственнику.

**UC-G8. Переподключить источник.** `source.session_expired` → G6 → в Telegram «Переподключите источник» → человек просит участника команды запустить `storozh connect`.

## 4. Функциональные требования

| ID | Требование | Приоритет |
| --- | --- | --- |
| FR-G-01 | Потребитель `guard` на `document.*` и `source.session_expired` через `shared.outbox.consume`; одна тревога на событие (`event_id` unique) | Must |
| FR-G-02 | Правило — чистая функция `(event, document, ctx) -> AlertDraft | None` с `id`, версией и тестом | Must |
| FR-G-03 | Правила G1–G7 (таблица ниже) | Must: G1, G2, G3, G6. Should: G4, G5, G7 |
| FR-G-04 | Тревога не ждёт ИИ: таймаут 5 с, потом шаблон | Must |
| FR-G-05 | Бот: `/start link_<token>`, `/start login_<nonce>`, тревоги на `uz` и `ru`, кнопки с HMAC-подписью `callback_data`, проверка `chat_id` | Must |
| FR-G-06 | В тексте тревоги нет ФИО, ПИНФЛ, адреса, суммы и ссылок на вход; единственная ссылка — на карточку на нашем домене | Must |
| FR-G-07 | Действие: состояния `proposed → awaiting_confirmation → confirmed → executing → verifying → done`, плюс `failed`, `expired`; переходы только вперёд; каждый — в аудит и `action.updated` | Must |
| FR-G-08 | Код подтверждения: 6 цифр, в базе хеш, 2 мин, 3 попытки, отправка только в привязанный Telegram | Must |
| FR-G-09 | `Idempotency-Key` на `POST /guard/actions`: повтор возвращает то же действие | Must |
| FR-G-10 | Исполнитель `revoke_car_poa`: белый список типов, сессия из `SessionProvider`, скриншот результата в `evidence_enc`, проверка через `request_refresh` | Must |
| FR-G-11 | Повтор исполнителя — только до шага отправки формы | Must |
| FR-G-12 | Заявление по ст. 31 и иск — вызов `draft_application`, отдача PDF | Should |
| FR-G-13 | Семья и согласия (UC-G7) | Should |
| FR-G-14 | Экраны: `/alerts`, `<DocumentGuard/>`, модалка подтверждения (поле кода, отсчёт, попытки), `/actions/[id]` (шаги по SSE, скриншот), `/family` | Must |
| FR-G-15 | Каркас: навигация «Мои документы», «Уведомления», «Источники», «Семья»; переключатель uz/ru; метка «прототип модуля MyGov» вместо герба и логотипа | Must |

### Правила прототипа

| ID | Условие | Важность | Кнопки |
| --- | --- | --- | --- |
| G1 | `document.created`, `kind` = `poa_car` или `poa_notarial`, `owner_role` = `principal` | critical | «Это не я — отозвать», «Это я» |
| G2 | `document.created`, `kind` = `notarial_act`, владелец — участник | high | «Это не я — заявление по ст. 31», «Это я» |
| G3 | `document.status_changed` | info | «Открыть» |
| G4 | Доверенность истекает через ≤ 7 дней (проверка раз в сутки) | info | «Открыть» |
| G5 | `document.disappeared` | high | «Открыть» |
| G6 | `source.session_expired` | high | «Переподключить» |
| G7 | Создана `critical`-тревога у человека, давшего семье `receive_alerts` | копия родственнику | «Открыть» |

Правила R1–R8 из общего файла — для стороны нотариуса в целевом состоянии, в прототипе не делаем.

## 5. Нефункциональные требования

| ID | Требование |
| --- | --- |
| NFR-G-01 | Тревога в Telegram ≤ 5 с после события |
| NFR-G-02 | От «Это не я» до статуса «отозвана» в источнике — меньше минуты на живом аккаунте |
| NFR-G-03 | Повтор события не создаёт вторую тревогу; повтор `confirm` не запускает второе исполнение |
| NFR-G-04 | Исполнитель никогда не отправляет форму аннулирования дважды |
| NFR-G-05 | Фронтенд: строгий CSP, HSTS, `frame-ancestors 'none'` — модалку подтверждения нельзя встроить в чужую страницу |
| NFR-G-06 | Экраны совпадают с MyGov по сетке, цветам, шрифтам и компонентам; на телефоне без горизонтальной прокрутки |

## 6. Ограничения

- Вживую исполняется только `revoke_car_poa`: у my.gov.uz есть онлайн-аннулирование, бесплатно.
- Отзыв нотариальной доверенности и отложение по ст. 31 онлайн сейчас невозможны — только PDF-черновик и подсказка, куда нести.
- Пауза сделки по ст. 31 вживую требует события из Notarius до удостоверения — его нет, показываем как целевое состояние.
- Канал прототипа — Telegram; в целевом состоянии — push MyGov и подтверждение через MyID.
- Герб и логотип MyGov не копируем; сайт на нашем домене.

## 7. Данные — схема `guard`

| Таблица | Поля | Заметки |
| --- | --- | --- |
| `alerts` | `event_id` unique, `citizen_id`, `document_id`, `rule_id`, `rule_version`, `severity`, `title`, `explanation`, `verdict` (`me`, `not_me`, null), `status` (`new`, `seen`, `closed`), `tg_message_id` | |
| `actions` | `alert_id`, `document_id`, `type`, `status`, `idempotency_key` unique, `confirm_code_hash`, `confirm_expires_at`, `attempts`, `submitted_at`, `evidence_enc`, `result jsonb` | `submitted_at` ≠ null → повтор запрещён |
| `telegram_links` | `citizen_id`, `chat_id_enc`, `chat_id_hmac` unique, `linked_at` | |
| `link_tokens` | `token_hash`, `citizen_id`, `expires_at`, `used_at` | |
| `consents` | `grantor_id`, `grantee_id`, `scopes text[]`, `granted_at`, `revoked_at` | |
| `invite_codes` | `code_hash`, `grantor_id`, `scopes`, `expires_at`, `used_at` | |

Аудит пишется через `shared.audit.write` в `shared.audit_log` (Разработчик 2). RLS по `citizen_id`; для семьи — политика по активному `consents`.

## 8. REST API

| Метод и путь | Ответ | Заметки |
| --- | --- | --- |
| `GET /guard/alerts?status&cursor` | `{items: Alert[], next_cursor}` | |
| `POST /guard/alerts/{id}/verdict` | `Alert` | Тело `{verdict: "me" \| "not_me"}` |
| `GET /guard/documents/{id}/alerts` | `Alert[]` | Для `<DocumentGuard/>` |
| `POST /guard/actions` | `201 Action` | Тело `{document_id, type}`, заголовок `Idempotency-Key` |
| `POST /guard/actions/{id}/confirm` | `Action` | Тело `{code}`; `429` после 3 попыток |
| `GET /guard/actions/{id}` | `Action` | |
| `GET /guard/actions/{id}/evidence` | `image/png` | Скриншот результата |
| `POST /guard/drafts` | `{draft_id, url}` | Тело `{document_id, type}` → `draft_application` |
| `POST /guard/telegram/link` | `{deep_link}` | |
| `GET /guard/family` | `{i_share_with: [], shared_with_me: []}` | |
| `POST /guard/consents/invite` | `{code}` | Тело `{scopes}` |
| `POST /guard/consents/accept` | `Consent` | Тело `{code}` |
| `DELETE /guard/consents/{id}` | `204` | |

```json
// Action
{"id": "uuid", "type": "revoke_car_poa", "document_id": "uuid", "status": "verifying",
 "steps": [{"status": "confirmed", "at": "…"}, {"status": "executing", "at": "…"}],
 "attempts_left": 2, "confirm_expires_at": "…", "result": null}
```

## 9. События

| Потребляю | Что делаю |
| --- | --- |
| `document.created`, `document.changed`, `document.status_changed`, `document.disappeared` | Правила G1–G5, G7; `status_changed` к `revoked` закрывает действие в `verifying` |
| `source.session_expired` | G6 |

| Публикую | `dedupe_key` |
| --- | --- |
| `alert.created` | `{event_id}:{rule_id}` |
| `action.updated` | `{action_id}:{status}` |

## 10. Порты

```python
class ActionExecutor(Protocol):
    action_type: str                       # "revoke_car_poa"
    async def execute(self, req: ActionRequest, session: BrowserSession) -> ActionResult: ...

Rule = Callable[[Event, NormalizedDocument | None, RuleContext], AlertDraft | None]

class Notifier(Protocol):                  # Telegram сейчас, push MyGov потом
    async def send_alert(self, citizen_id: UUID, alert: Alert) -> str: ...      # message id
    async def edit_alert(self, citizen_id: UUID, message_id: str, alert: Alert) -> None: ...
    async def send_code(self, citizen_id: UUID, code: str) -> None: ...
```

## 11. Структура

```
backend/storozh/guard/
  domain/rules/   g1_new_poa.py … g7_family_copy.py  tests/
  domain/actions.py            # машина состояний
  ports.py  public.py  service.py  api.py  worker.py
  adapters/actions/mygov_revoke_car_poa/  executor.py  selectors.py
  adapters/telegram/          notifier.py  bot.py  templates/{uz,ru}.py
  adapters/db/
web/components/mygov/          # кит (готов)
web/app/(shell)/  web/app/kit/  web/app/alerts/  web/app/actions/  web/app/family/
web/app/(guard)/components/DocumentGuard.tsx
```

## 12. Definition of Done

- [ ] Новая e-доверенность на живом аккаунте → тревога в Telegram ≤ 5 с после события.
- [ ] «Это не я» → код → отзыв → «Подтверждено источником» меньше чем за минуту, три прогона подряд.
- [ ] Повтор события и повтор `confirm` не дают второй тревоги и второго исполнения (тесты).
- [ ] Подделанный `callback_data` и четвёртая попытка кода отклоняются (тесты).
- [ ] Каждое правило G1–G7 покрыто тестом.
- [ ] Все экраны собраны из `/kit`, переключатель uz/ru работает на всех страницах.
- [ ] `import-linter` зелёный.

## 13. Открытые вопросы

- Шаги и селекторы аннулирования e-доверенности в my.gov.uz — снять HAR при первом ручном отзыве.
- Нужно ли подтверждение SMS-кодом MyGov при аннулировании — если да, исполнитель ждёт код от человека.
