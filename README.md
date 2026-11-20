# Сторож сделок

Модуль «Мои документы» в дизайне MyGov: читает живые записи человека из госкабинетов, сообщает о новом
за секунды и даёт отреагировать одной кнопкой. ТЗ, обоснование и C4-диаграммы — в документах команды.

## Устройство

Модульный монолит: один репозиторий, одна база, но у каждого контекста своя схема Postgres, своя роль БД,
свои эндпоинты и свои страницы. Связь между контекстами — только события (`shared.outbox`) и `public.py`.

```
contracts/                    openapi.yaml, schemas/, events/, examples/ — фиксируем первыми, PR с двумя апрувами
backend/
  storozh/
    shared/                   Разр. 3 — config, db (пул на роль), uri, hashing, contracts, events, outbox,
                              crypto, auth, audit, problem (RFC 9457), logs (маскирование), migrate
    documents/                Разр. 1 — domain/ ports.py public.py service.py api.py worker.py
      adapters/               mygov_car_poa/ mygov_notarial/ vakolat/ db/
    guard/                    Разр. 2 — domain/{actions.py, rules/} ports.py public.py service.py api.py worker.py bot/
      adapters/               actions/mygov_revoke_car_poa/ pdf/ db/
    assistant/                Разр. 3 — rag/ (корпус lex.uz + гибридный поиск) llm/ (агент) pii/ public.py api.py worker.py
    platform/                 Разр. 3 — вход, граждане, /me, /stream
    migrations/<context>/     plain SQL, по папке на контекст
    main.py  cli.py           точка сборки: все роутеры, все процессы
  tests/                      test_contracts.py, по папке на контекст, integration/ (нужна база)
  eval/                       оценка RAG
web/
  app/(shell)/…  app/login/   тонкие файлы маршрутов
  features/<context>/         логика страниц: documents (1), guard (2), assistant и platform (3)
  components/mygov/           Разр. 3 — токены и кит; витрина /kit
  lib/api/                    клиент и типы из openapi.yaml (npm run gen:api)
docker-compose.yml  .env.example  .github/
frontend-mockup/              кликабельный макет (референс для дизайна)
```

### Границы проверяет машина

| Что | Как | Где |
|---|---|---|
| Контекст не импортирует чужой код, кроме `public.py` и `shared` | import-linter | `backend/pyproject.toml`, `uv run lint-imports` |
| Контекст не читает и не пишет чужие таблицы | `SET ROLE storozh_<context>` + права только на свою схему | `shared/db.py`, `migrations/shared/000_*.sql` |
| `document_versions`, `audit_log`, `outbox` только дописываются | `REVOKE UPDATE, DELETE` | миграции |
| Код совпадает с контрактом | тест сравнивает пути FastAPI с `openapi.yaml`, примеры — со схемами и Pydantic | `tests/test_contracts.py` |
| Типы фронта совпадают с контрактом | CI перегенерирует `schema.d.ts` и падает на diff | `.github/workflows/ci.yml` |

## Запуск

```bash
cp .env.example .env
docker compose up                         # база, миграции, API :8000, воркеры, бот, веб :3000
```

Разработка без Docker для своего кода:

```bash
docker compose up -d db migrate           # только Postgres :5433 + миграции
cd backend && uv sync
uv run python -m storozh api --reload     # http://localhost:8000/docs
uv run python -m storozh worker guard     # collector | guard | bot | assistant
uv run pytest && uv run lint-imports && uv run ruff check .
```

```bash
cd web && npm install && npm run dev      # http://localhost:3000
docker compose --profile mock up mock     # Prism-мок на :4010; NEXT_PUBLIC_API_URL=http://localhost:4010
```

После правки `contracts/openapi.yaml`: `cd web && npm run gen:api` и закоммитить `lib/api/schema.d.ts`.

Новая миграция: следующий номер в `backend/storozh/migrations/<свой контекст>/`, применённые файлы не правим
(раннер сверяет checksum). `storozh connect` (вход в OneID) запускается на машине с экраном, не в Docker.

## Как добавить…

- **Источник** (Разр. 1): папка `documents/adapters/<source>/adapter.py` с `SourceAdapter` + строка в `adapters/__init__.py`.
- **Правило** (Разр. 2): `guard/domain/rules/gN_*.py` с `@rule("GN")` + импорт в `rules/__init__.py` + тест.
- **Действие** (Разр. 2): `guard/adapters/actions/<type>/` с `ActionExecutor` + запись в `EXECUTORS`.
- **Событие** (все): схема `contracts/events/<type>.v1.schema.json` + строка в `TOPICS` (`shared/events.py`).
- **Эндпоинт**: сначала `openapi.yaml` (PR с двумя апрувами), потом роутер — иначе упадёт `test_contracts`.

## Отличия от ТЗ

- **SQL-миграции вместо Alembic.** Пять независимых владельцев схем дают у Alembic пять веток с merge-головами.
  Здесь — plain SQL в папке контекста и мини-раннер (`shared/migrate.py`) с учётом в `shared.schema_migrations`.
- **psycopg 3 без ORM.** Так уже написан RAG, и запросы прозрачны. SQLAlchemy можно добавить в своём `adapters/db/`.
- **Роль на контекст через `SET ROLE`**, а не отдельные логины: без паролей в git, а права те же.
- **Страницы внутри `app/(shell)/`**, логика — в `web/features/<context>/`: иначе каркас не оборачивает страницы,
  а маршруты разных разработчиков смешиваются с их компонентами.
- **Next.js 15** вместо 14: поддерживаемая ветка с патчами безопасности; переход с 14 почти бесплатный (params стали Promise).
- **`docker-compose.yml` в корне**, а не в `infra/`: `docker compose up` работает без `-f`.
- **Прежний RAG сохранён** и переехал в `assistant/rag` + `assistant/llm`, таблицы — в схему `assistant`.
  `GET /assist/search` и `POST /assist/ask` работают уже сейчас.
