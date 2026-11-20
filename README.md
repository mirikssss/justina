# Сторож сделок

Модуль «Мои документы» в дизайне MyGov. Он читает живые записи человека из госкабинетов, сообщает о новом
за секунды и даёт отреагировать одной кнопкой. ТЗ 1.1 по разработчикам: 01-dev1-documents, 02-dev2-assistant-platform,
03-dev3-guard-frontend.

| Разработчик | Контексты | Бэкенд | Фронтенд |
|---|---|---|---|
| 1 | «Документы» | `storozh/documents/`, `migrations/documents/` | `web/features/documents/` — лента, карточка, «Источники» |
| 2 | «Помощник», «Платформа», `shared`, инфраструктура | `storozh/{assistant,platform,shared}/`, `infra/`, CI | `web/features/{assistant,platform}/` — `<DocumentAssistant/>`, вход |
| 3 | «Сторож», каркас и кит MyGov | `storozh/guard/`, `migrations/guard/` | `web/components/mygov/`, `app/(shell)/`, `web/features/guard/` |

## Устройство

Модульный монолит: один репозиторий и одна база. У каждого контекста своя схема Postgres, своя роль БД,
свои эндпоинты и свои страницы. Связь между контекстами идёт только через события (`shared.outbox`) и `public.py`.

```
contracts/                    openapi.yaml, schemas/, events/, examples/ — меняются только PR с двумя апрувами
backend/storozh/
  shared/                     Р2: config, db (пул на роль), uri, hashing, contracts, events, outbox, crypto,
                              auth, audit, problem (RFC 9457), logging (маскирование), migrate
  documents/                  Р1: domain/ ports.py public.py service.py api.py worker.py cli.py
    adapters/                 mygov_car_poa/ mygov_notarial/ (selectors.py, captcha.py, tests/fixtures) vakolat/ db/
  guard/                      Р3: domain/{actions.py, rules/} ports.py public.py service.py api.py worker.py
    adapters/                 actions/mygov_revoke_car_poa/ telegram/{bot,notifier,templates} pdf/ db/
  assistant/                  Р2: rag/ (корпус lex.uz, гибридный поиск) llm/ (port, provider, agent, prompts)
                              pii/ drafts/ eval/ public.py api.py worker.py
  platform/                   Р2: вход, граждане, /me, /stream, /audit
  migrations/<context>/       plain SQL, по папке на контекст
  main.py  cli.py             точка сборки: все роутеры и все процессы
backend/tests/                test_contracts.py, по папке на контекст, integration/ (нужна база)
web/
  app/(shell)/…  app/login/   тонкие файлы маршрутов
  features/<context>/         логика страниц каждого контекста
  components/mygov/           Р3: токены и кит, витрина /kit
  lib/api/                    клиент и типы из openapi.yaml (make gen-api)
infra/docker-compose.yml  .env.example  Makefile  .github/
frontend-mockup/              кликабельный макет — эталон дизайна для web/
```

### Границы проверяет машина

| Что | Как | Где |
|---|---|---|
| Контекст не импортирует чужой код, кроме `public.py` и `shared` | import-linter | `backend/pyproject.toml`, `make lint` |
| Контекст не читает и не пишет чужие таблицы | `SET ROLE storozh_<context>` + права только на свою схему | `shared/db.py`, `migrations/shared/000_*.sql` |
| `document_versions`, `audit_log`, `outbox` только дописываются | `REVOKE UPDATE, DELETE` | миграции |
| Код совпадает с контрактом | тест сравнивает пути FastAPI с `openapi.yaml`, примеры — со схемами и Pydantic | `tests/test_contracts.py` |
| Типы фронта совпадают с контрактом | CI перегенерирует `schema.d.ts` и падает на diff | `.github/workflows/ci.yml` |

## Запуск

```bash
cp .env.example .env
make up          # база, миграции, API :8000, воркеры, бот, веб :3000
```

Разработка своего кода без Docker:

```bash
make db                                   # Postgres :5433 + миграции
cd backend && uv sync
uv run python -m storozh api --reload     # http://localhost:8000/docs
uv run python -m storozh worker guard     # collector | guard | bot | assistant
make check                                # ruff + import-linter + pytest
```

```bash
make web                                  # http://localhost:3000
make mock                                 # Prism-мок :4010; в web/.env.local NEXT_PUBLIC_API_URL=http://localhost:4010
```

После правки `contracts/openapi.yaml` запустите `make gen-api` и закоммитьте `web/lib/api/schema.d.ts`.

Новая миграция — следующий номер в `backend/storozh/migrations/<свой контекст>/`. Применённые файлы не правим:
раннер сверяет checksum. `storozh documents connect` (вход в OneID) запускается на машине с экраном, не в Docker.

## Ветки

- Каждый работает в своей короткоживущей ветке (`dev1/...`, `dev2/...`, `dev3/...`) и вливает в `main`
  небольшими PR несколько раз в день, не реже каждой точки сборки.
- `main` защищена: зелёный CI и одно ревью. Перед PR подтяните `main` к себе.
- `contracts/` правится отдельным PR, который смотрят все трое.

## Как добавить…

- **Источник** (Р1): папка `documents/adapters/<source>/` с `adapter.py` и `selectors.py` + строка в `adapters/__init__.py`.
- **Правило** (Р3): `guard/domain/rules/gN_*.py` с `@rule("GN")` + импорт в `rules/__init__.py` + тест.
- **Действие** (Р3): `guard/adapters/actions/<type>/` с `ActionExecutor` + запись в `EXECUTORS`.
- **Событие** (все): схема `contracts/events/<type>.v1.schema.json` + строка в `TOPICS` (`shared/events.py`).
- **Эндпоинт**: сначала `openapi.yaml` (PR с двумя апрувами), потом роутер. Иначе упадёт `test_contracts`.

## Отличия от ТЗ 1.1

- **psycopg 3 без ORM.** В ТЗ у `shared` сигнатуры с `AsyncSession` (SQLAlchemy). Здесь `AsyncConnection`
  из psycopg: так уже написан RAG, и роли БД ставятся на соединение. Остальные сигнатуры совпадают.
- **Обработчик outbox получает `(event, conn)`, а не `(event)`.** Его записи в базу коммитятся вместе
  со сдвигом курсора, поэтому повтор события не даёт двойных записей.
- **`documents` уникальны по `(citizen_id, uri)`, а не по `uri`**, и `dedupe_key` событий `document.*` начинается
  с `{citizen_id}:`. Одну e-доверенность видят обе стороны; с ключом из ТЗ (`{uri}:1:created`) событие второй
  стороны отбрасывалось бы как дубль.
- **`guard.alerts` уникальны по `(event_id, rule_id)`.** Это совпадает с `dedupe_key` события `alert.created`.
- **SQL-миграции вместо Alembic:** у пяти независимых владельцев схем Alembic даёт ветки с merge-головами.
- **Компоненты фронта лежат в `web/features/<context>/`, а не в `app/(guard)/components/`.** Маршруты лежат
  в `app/(shell)/`, иначе каркас их не оборачивает.
- **RAG.** Подпапки `rag/corpus` и `rag/retrieval` вместо `ingest_lex.py`, `chunker.py`, `search.py`.
  Таблицы корпуса: `documents/articles/chunks` в схеме `assistant`, а не `lex_chunks`.
