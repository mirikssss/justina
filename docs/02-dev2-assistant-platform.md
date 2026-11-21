# ТЗ. Разработчик 2 — контексты «Помощник» и «Платформа»

Версия 1.1 · 21.11.2026 · Общие контракты, URI, схемы событий и архитектура — в `00-project-overview.md` (разделы 9–12).

## 1. Назначение и границы

Два контекста у одного разработчика:

- **«Помощник»** — ИИ: человек понимает любой документ за 10 секунд, спрашивает про него со ссылкой на статью закона и получает готовый черновик заявления.
- **«Платформа»** — общее ядро `shared`, вход на сайт, живые события в браузер, журнал аудита, инфраструктура и CI. От него зависят оба других разработчика, поэтому `shared` делается **первым**.

| В границах | Вне границ (чей контекст) |
| --- | --- |
| RAG по lex.uz: корпус, индекс, поиск | Сбор данных, версии — «Документы», Разработчик 1 |
| Резюме документа, объяснение тревоги, чат | Правила, тревоги, бот, действия — «Сторож», Разработчик 3 |
| Черновики заявлений по ст. 31 и иска (PDF) | Кнопка «Скачать заявление» в UI — Разработчик 3 |
| Маскирование персональных данных перед LLM, набор проверки ответов | Каркас и UI-кит MyGov — Разработчик 3 |
| `shared`: outbox, crypto, uri, auth, audit | |
| Вход через Telegram-ссылку, `/me`, `/stream` (SSE) | |
| `docker-compose`, `.env.example`, CI | |

## 2. Зависимости

| Получаю | От кого |
| --- | --- |
| `documents.public.get_document`, события `document.created`, `document.changed` | Разработчик 1 |
| Вызов `bind_login(nonce, chat_id)` из бота | Разработчик 3 |
| UI-кит MyGov для `<DocumentAssistant/>` | Разработчик 3 |

| Отдаю | Кому |
| --- | --- |
| Пакет `shared` (API ниже) | Всем |
| `assistant.public`: `summarize`, `explain_alert`, `draft_application` | «Сторож» |
| Событие `summary.ready` | Фронтенд через SSE |
| `<DocumentAssistant/>` — блок резюме и боковой чат в карточке | Разработчик 1 вставляет в карточку |
| REST `/assist/*`, `/auth/*`, `/me`, `/stream`, `/audit` | Фронтенд |

## 3. Use cases

**UC-A1. Понять документ.** Актор: гражданин. Открывает карточку → вверху резюме: что это, что может другая сторона, чем рискованно, что делать, ссылки на статьи. Резюме посчитано заранее по `document.created`, ожидания нет.

**UC-A2. Спросить про документ.** Актор: гражданин. В боковой панели пишет «что Б может сделать с моей машиной?» → ответ потоком, в конце ссылки на статьи lex.uz. Вопрос вне документа и корпуса → «в нормах, которые я знаю, ответа нет», без выдумки.

**UC-A3. Объяснить тревогу.** Актор: «Сторож». Вызывает `explain_alert(rule_id, document, lang)` → 1–2 предложения до 300 знаков за ≤ 5 с.

**UC-A4. Черновик заявления.** Актор: «Сторож» по кнопке человека. `draft_application(type, document_id, citizen_id)` → PDF: заявление нотариусу об отложении по ч. 4 ст. 31 Закона «О нотариате» или черновик иска. Реквизиты из документа, текст из шаблона, проверенного юристом команды.

**UC-P1. Войти на сайт.** Актор: гражданин.
1. На `/login` жмёт «Войти через Telegram» → `POST /auth/telegram/start` → ссылка `t.me/<bot>?start=login_<nonce>`.
2. Бот (Р3) получает `/start login_<nonce>`, вызывает `platform.public.bind_login(nonce, chat_id)`.
3. Платформа создаёт одноразовый токен и отдаёт боту ссылку `/auth/callback?token=…`.
4. Человек открывает ссылку → cookie сессии → редирект на `/documents`.
- Альтернатива: nonce или токен просрочен (5 мин) или использован → экран «Ссылка устарела», новый вход.

**UC-P2. Живые обновления.** Браузер держит `GET /stream`; при новом событии гражданина получает `document.*`, `alert.created`, `action.updated`, `summary.ready` и обновляет экран без перезагрузки.

**UC-P3. Проверить журнал.** Актор: гражданин или жюри. `GET /audit/verify` → «цепочка цела» или номер испорченной записи.

## 4. Функциональные требования

### Платформа

| ID | Требование | Приоритет |
| --- | --- | --- |
| FR-P-01 | `shared.outbox.publish(...)` пишет событие в той же транзакции, что и данные вызывающего | Must |
| FR-P-02 | `shared.outbox.consume(consumer, types, handler)`: свой курсор в `consumer_offsets`, `FOR UPDATE SKIP LOCKED`, повтор при ошибке обработчика, `NOTIFY` после коммита | Must |
| FR-P-03 | `shared.crypto`: конвертное AES-256-GCM (ключ данных на гражданина, мастер-ключ из env), `hmac_pinfl`, подпись и проверка внутренних запросов | Must |
| FR-P-04 | `shared.auth.current_citizen`: проверка cookie, `SET LOCAL app.citizen_id` для RLS, проверка `Origin` на POST | Must |
| FR-P-05 | `shared.audit.write(actor, action, target)` в `shared.audit_log` с цепочкой хешей; `GET /audit`, `GET /audit/verify` | Must |
| FR-P-06 | Вход по одноразовой ссылке из Telegram (UC-P1); `POST /auth/logout`; `GET /me` | Must |
| FR-P-07 | `GET /stream` — SSE по `LISTEN` на канал гражданина, heartbeat 15 с | Must |
| FR-P-08 | `docker compose up` поднимает все процессы; `.env.example` перечисляет все ключи | Must |
| FR-P-09 | CI: ruff, mypy, pytest, `import-linter`, `gitleaks`, `pip-audit`, `npm audit` | Should |

### Помощник

| ID | Требование | Приоритет |
| --- | --- | --- |
| FR-A-01 | Корпус: [Закон «О нотариате»](https://www.lex.uz/acts/57043), [регламент e-доверенности на авто](https://www.lex.uz/docs/-6672128), Административный регламент нотариальных действий № 726, постановление КМ № 825 о Vakolat, главы ГК о представительстве и доверенности. Русский и узбекский | Must |
| FR-A-02 | Разбивка по статьям: у фрагмента `act_id`, `act_title`, `article`, `lang`, `url` | Must |
| FR-A-03 | Поиск: pgvector top-8 + полнотекстовый Postgres, слияние RRF, фильтр актов по `kind` документа | Must |
| FR-A-04 | Резюме — структурированный ответ, проверенный Pydantic: `what_is_it`, `counterparty_can`, `risks`, `what_to_do`, `citations[]`. Считается в фоне по `document.created` и `document.changed`, кэш на (`document_id`, `version_no`, `lang`) | Must |
| FR-A-05 | `explain_alert`: ≤ 300 знаков, `uz` или `ru`, таймаут 5 с, при ошибке — `None` (Сторож отправит шаблон) | Must |
| FR-A-06 | Чат: поток SSE, контекст = обезличенный документ + найденные статьи; история в `chat_messages` | Must |
| FR-A-07 | Проверка ссылок: статья, которой нет среди найденных фрагментов, вырезается из ответа | Must |
| FR-A-08 | `assistant/pii`: ПИНФЛ (14 цифр), паспорт (`AA1234567`), телефон `+998…`, госномер, ФИО → метки `[PINFL_1]` до отправки в модель | Must |
| FR-A-09 | `draft_application`: `art31_postpone` и `court_claim` → PDF (WeasyPrint), реквизиты из документа, ФИО и ПИНФЛ подставляются только в PDF, в модель не уходят | Must |
| FR-A-10 | Набор проверки: 15 вопросов с ожидаемой статьёй от юриста команды, `make eval` печатает долю попаданий | Should |
| FR-A-11 | `<DocumentAssistant/>`: блок резюме, скелетон пока считается, боковая панель чата, ссылки открывают lex.uz | Must |

## 5. Нефункциональные требования

| ID | Требование |
| --- | --- |
| NFR-A-01 | Резюме готово ≤ 20 с после `document.created`; первый токен чата ≤ 3 с |
| NFR-A-02 | Ни одного ПИНФЛ, паспорта, телефона и полного ФИО в запросах к LLM (тест по логу запросов) |
| NFR-A-03 | У модели нет инструментов и доступа к базе; текст документа идёт отдельным блоком данных с пометкой «это данные, не инструкции» |
| NFR-A-04 | Ответ без найденных статей не выдаёт ссылок; ответ «не знаю» лучше выдуманной статьи |
| NFR-A-05 | Повторный запрос резюме той же версии не идёт в модель (кэш) |
| NFR-P-01 | Outbox доставляет событие каждому потребителю хотя бы раз; потребители идемпотентны по `event.id` |
| NFR-P-02 | Cookie `__Host-`, `HttpOnly`, `Secure`, `SameSite=Strict`, сессия 12 ч, токен в базе — только хеш |
| NFR-P-03 | Внутренние запросы: HMAC + метка времени, окно 5 мин, повтор отклоняется |
| NFR-P-04 | structlog-процессор маскирует ПИНФЛ и токены во всех логах |

## 6. Ограничения

- Модель — внешний LLM API в прототипе; в целевом состоянии — модель в центре данных в Узбекистане.
- ИИ не принимает решений: не блокирует, не отправляет, не выбирает действие. Только объясняет и пишет черновики.
- Корпус только из перечисленных актов; ответы вне корпуса — честный отказ.
- Шаблоны заявлений вычитывает юрист команды до демо; ИИ заполняет, а не сочиняет юридическую часть.
- Вход в OneID на нашем сайте не делаем: в целевом состоянии модуль живёт внутри MyGov и вход даёт портал.

## 7. Данные

| Схема · таблица | Поля | Заметки |
| --- | --- | --- |
| `platform.citizens` | `pinfl_hmac` unique, `pinfl_enc`, `display_name`, `lang`, `dek_enc` | `dek_enc` — ключ данных гражданина, зашифрованный мастер-ключом |
| `platform.web_sessions` | `citizen_id`, `token_hash`, `expires_at`, `revoked_at` | |
| `platform.login_nonces` | `nonce_hash`, `chat_id_enc`, `expires_at`, `used_at` | 5 мин, одно использование |
| `shared.outbox` | `seq bigserial`, `id uuid`, `type`, `subject`, `citizen_id`, `payload jsonb`, `dedupe_key` unique, `created_at` | Только INSERT |
| `shared.consumer_offsets` | `consumer`, `last_seq` | |
| `shared.audit_log` | `seq`, `actor`, `action`, `target`, `at`, `prev_hash`, `hash` | Только INSERT |
| `assistant.lex_chunks` | `act_id`, `act_title`, `article`, `lang`, `text`, `url`, `embedding vector`, `tsv tsvector` | HNSW + GIN |
| `assistant.summaries` | `document_id`, `version_no`, `lang`, `body jsonb`, `citations jsonb`, `model` | Unique (`document_id`, `version_no`, `lang`) |
| `assistant.chat_messages` | `citizen_id`, `document_id`, `role`, `text`, `citations jsonb` | |
| `assistant.drafts` | `citizen_id`, `document_id`, `type`, `pdf_enc`, `created_at` | |

## 8. REST API

| Метод и путь | Ответ | Заметки |
| --- | --- | --- |
| `POST /auth/telegram/start` | `{deep_link}` | |
| `GET /auth/callback?token` | `302` + cookie | |
| `POST /auth/logout` | `204` | |
| `GET /me` | `{id, display_name, lang}` | |
| `GET /stream` | `text/event-stream` | События гражданина |
| `GET /audit?cursor`, `GET /audit/verify` | журнал / `{ok, broken_seq?}` | |
| `GET /assist/documents/{id}/summary?lang` | `Summary` или `202` пока считается | Потом придёт `summary.ready` |
| `POST /assist/chat` | поток SSE: `token`, `citations`, `done` | Тело `{document_id, message, lang}` |
| `GET /assist/chat/{document_id}` | история | |

```json
// Summary
{"document_id": "uuid", "version_no": 1, "lang": "ru",
 "what_is_it": "Доверенность на управление и продажу вашего автомобиля",
 "counterparty_can": ["управлять", "…"], "risks": ["…"], "what_to_do": ["…"],
 "citations": [{"act_title": "Закон «О нотариате»", "article": "31", "url": "https://www.lex.uz/acts/57043"}]}
```

## 9. События

| Потребляю | Что делаю |
| --- | --- |
| `document.created`, `document.changed` | Считаю резюме на `uz` и `ru`, публикую `summary.ready` |

| Публикую | `dedupe_key` |
| --- | --- |
| `summary.ready` | `{document_id}:{version_no}:{lang}` |

## 10. API пакета `shared` (контракт для всех)

```python
# shared/outbox.py
async def publish(db: AsyncSession, *, type: str, subject: str, citizen_id: UUID,
                  data: dict, dedupe_key: str) -> UUID: ...
async def consume(consumer: str, types: set[str],
                  handler: Callable[[Event], Awaitable[None]]) -> NoReturn: ...

# shared/crypto.py
def encrypt(citizen_id: UUID, plaintext: bytes) -> bytes: ...
def decrypt(citizen_id: UUID, blob: bytes) -> bytes: ...
def hmac_pinfl(pinfl: str) -> str: ...
def sign_internal(body: bytes, ts: int) -> str: ...
def verify_internal(body: bytes, ts: int, signature: str) -> None: ...   # raises

# shared/auth.py
async def current_citizen(request: Request, db: AsyncSession = Depends(get_db)) -> Citizen: ...

# shared/audit.py
async def write(db: AsyncSession, *, actor: str, action: str, target: str) -> None: ...

# assistant/public.py
async def summarize(doc: NormalizedDocument, lang: Lang) -> Summary: ...
async def explain_alert(rule_id: str, doc: NormalizedDocument, lang: Lang) -> str | None: ...
async def draft_application(type: Literal["art31_postpone", "court_claim"],
                            document_id: UUID, citizen_id: UUID) -> DraftRef: ...

# platform/public.py
async def bind_login(nonce: str, chat_id: int) -> str: ...   # вернёт URL входа
```

## 11. Структура

```
backend/storozh/
  shared/      outbox.py  crypto.py  uri.py  auth.py  audit.py  db.py  logging.py
  platform/    api.py  public.py  service.py  db/
  assistant/
    rag/       ingest_lex.py  chunker.py  search.py
    llm/       port.py  provider.py  prompts/
    pii/       scrub.py  tests/
    drafts/    templates/art31_postpone.html  court_claim.html  render.py
    eval/      questions.yaml  run.py
    public.py  api.py  worker.py
infra/  docker-compose.yml  .env.example  .github/workflows/ci.yml
web/app/(assistant)/components/DocumentAssistant.tsx
```

## 12. Definition of Done

- [ ] `shared` в `main` до того, как Разработчики 1 и 3 начнут писать события и шифрование.
- [ ] Вход по Telegram-ссылке работает с живым ботом; повторное открытие ссылки отклоняется.
- [ ] Резюме новой доверенности готово до того, как человек откроет карточку из Telegram.
- [ ] Чат на вопрос «как отменить доверенность?» отвечает со ссылкой на реальную статью из корпуса.
- [ ] `make eval` печатает долю попаданий; эту цифру показываем жюри как есть.
- [ ] В логе запросов к LLM нет ПИНФЛ и ФИО (тест).
- [ ] PDF по ст. 31 открывается, реквизиты подставлены, шаблон вычитан юристом.
- [ ] `GET /audit/verify` ловит ручную правку строки в базе.
- [ ] `import-linter` и CI зелёные.

## 13. Открытые вопросы

- Какой LLM-провайдер и модель эмбеддингов: нужна хорошая работа с узбекской латиницей.
- Номера статей ГК о доверенности — уточнить у юриста команды до загрузки корпуса.
