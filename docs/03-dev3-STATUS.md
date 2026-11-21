# Dev-3 (Сторож / guard) — статус и хендофф

Ветка: **`feat/guard-frontend`** (на GitHub). Последние коммиты:
`7d2f738` guard-frontend: экраны · `e0e37bd` guard-frontend: переключатель uz/ru.
Сверка с ТЗ — `docs/03-dev3-guard-frontend.md`.

Короткий итог: **фронтенд сделан полностью и проверен; правила G1–G7 и потребитель событий готовы с тестами (тревоги появляются в `/alerts`); действия, бот, исполнитель — ещё заглушки.**

Ветка смёрджена с `main` (21.11): конфликты в `DocumentAssistant.tsx` и `LoginScreen.tsx` решены — логика из `main`, строки через `t()`.

---

## ✅ Сделано — фронтенд (FR-G-14, FR-G-15)

Всё в `web/`. `npm run typecheck` чистый, `npm run build` собирает все 10 роутов.

| Что | Файлы |
| --- | --- |
| **`/alerts`** — список тревог по важности, «Это я / Это не я», live по `alert.created` (SSE) | `web/features/guard/AlertsPage.tsx` |
| **`<DocumentGuard/>`** — тревоги по документу + действия защиты; отзыв → `POST /guard/actions` c `Idempotency-Key` → модалка; ст.31/иск → `POST /guard/drafts` | `web/features/guard/DocumentGuard.tsx` |
| **Модалка подтверждения** — поле кода (6 цифр), отсчёт 2 мин, 3 попытки, обработка 429 | `web/features/guard/ConfirmModal.tsx` |
| **`/actions/[id]`** — машина состояний живыми шагами по `action.updated`, «Подтверждено источником» + скриншот evidence | `web/features/guard/ActionPage.tsx` |
| **`/family`** — i_share_with / shared_with_me, инвайт по коду со скоупами, приём кода, отзыв | `web/features/guard/FamilyPage.tsx` |
| Данные/запросы (TanStack Query + SSE), узб. подписи | `web/features/guard/queries.ts`, `labels.ts` |
| Кит: `Modal`, `Toaster`/`toast()` | `web/components/mygov/Modal.tsx`, `Toast.tsx` |
| **FR-G-15:** каркас-навигация + **переключатель uz/ru** + метка «прототип» вместо герба | `web/components/mygov/Shell.tsx`, `web/lib/i18n/` |

**i18n (переключатель uz/ru):** лёгкая замена next-intl без зависимости. Узбекская строка = ключ,
русский перевод в `web/lib/i18n/messages.ts`, fallback на узбекский. Выбор в `localStorage`,
отражается в `<html lang>`. Покрыты: shell, documents, alerts, actions, family, sources, assistant, login.

> Важно: экраны написаны под контракт REST из §8 ТЗ, но эндпоинты `/guard/*` на бэкенде пока заглушки,
> поэтому **сквозной** (end-to-end) сценарий не заработает, пока не сделан бэкенд (ниже).

---

## ❌ Осталось — бэкенд-контекст «Сторож» (FR-G-01 … FR-G-13 + DoD)

На диске (`backend/storozh/guard/`) есть только скелет. Размеры выдают заглушки:

| Требование | Что есть сейчас | Что нужно |
| --- | --- | --- |
| ~~FR-G-02/03 — правила G1–G7~~ ✅ | `domain/rules/g1…g7_*.py`, тесты `tests/guard/test_rules.py` (23 шт.) | G4 — на внутреннем событии `guard.daily_check` + `RuleContext.today`; G7 — на `alert.created` + `RuleContext.family_consent` (оценивается на каждого родственника с `receive_alerts`). Планировщик G4 и разводка G7 — в worker (шаг 2) |
| ~~FR-G-01 — потребитель событий~~ ✅ | `service.handle_event`, `worker.py` (consume + суточный G4 раз в час), `adapters/db` | Тревога на `(event_id, rule_id, citizen_id)` unique; `explain_alert` с таймаутом 5 с → иначе `explanation=null` (FR-G-04). G7: guard слушает и свой `alert.created`. G4: guard ведёт свою таблицу `poa_watch` (схему documents читать нельзя). Тесты: `tests/integration/test_guard_consumer.py` (7 шт.) |
| **FR-G-05 — Telegram-бот** | `adapters/telegram/{bot,notifier}.py`, `templates/{uz,ru}.py` — все заглушки | `/start link_<token>`, `/start login_<nonce>`, тревоги uz/ru, HMAC-подпись `callback_data`, проверка `chat_id` |
| **FR-G-07/08 — машина действий + код** | `domain/actions.py` ~0.9 КБ | переходы только вперёд, аудит + `action.updated`; код: 6 цифр, **хеш** в БД, 2 мин, 3 попытки |
| **FR-G-09 — идемпотентность** | — | `Idempotency-Key` на `POST /guard/actions` возвращает то же действие |
| **FR-G-10/11 — исполнитель `revoke_car_poa`** | `adapters/actions/mygov_revoke_car_poa/executor.py` ~0.7 КБ | белый список типов, сессия из `SessionProvider`, скриншот в `evidence_enc`, проверка через `request_refresh`; повтор — только до отправки формы (NFR-G-04) |
| **FR-G-12 — ст.31 / иск** | `adapters/pdf/__init__.py` ~0.1 КБ | вызов `assistant.public.draft_application`, отдача PDF |
| **FR-G-13 — семья/согласия** | — | сервер `consents`/`invite_codes`, RLS по активному согласию |
| **§7 — схема БД** | `001_init.sql` + `002_alerts_family_poa_watch.sql` (unique с `citizen_id`, `alerts.buttons`, `poa_watch`) | таблицы `alerts, actions, telegram_links, link_tokens, consents, invite_codes` |
| **§8 — REST** | ✅ `GET /guard/alerts` (курсор, сначала открытые и важные), `POST /alerts/{id}/verdict` (+аудит), `GET /documents/{id}/alerts`; остальное — заглушки | действия, черновики, Telegram, семья |
| **§9 — события** | ✅ `alert.created` (`{event_id}:{rule_id}`, у копий G7 — `…:{grantee}`) | `action.updated` (`{action_id}:{status}`); `status_changed → revoked` закрывает действие в `verifying` — в шаге 3 |

### §12 Definition of Done — чек-лист (всё бэкенд/интеграция, пока не закрыто)
- [ ] Новая e-доверенность → тревога в Telegram ≤ 5 с.
- [ ] «Это не я» → код → отзыв → «Подтверждено источником» < 1 мин, 3 прогона.
- [ ] Повтор события и повтор `confirm` не дают второй тревоги/исполнения (тесты).
- [ ] Подделанный `callback_data` и 4-я попытка кода отклоняются (тесты).
- [x] Каждое правило G1–G7 покрыто тестом.
- [x] Все экраны собраны из `/kit`, переключатель uz/ru работает на всех страницах.
- [x] `import-linter` зелёный (5 контрактов, проверять после каждого шага).

---

## Рекомендуемый порядок (с чего продолжить)

1. ~~**Правила G1–G7 + тесты**~~ ✅ — самодостаточно, не нужны ни Telegram, ни браузер. Закрывает строку DoD «каждое правило покрыто тестом».
2. ~~**Потребитель событий + публикация**~~ ✅ (`worker.py`, `alert.created`) — тревоги начинают появляться в `/alerts`.
3. **Машина действий + код + идемпотентность** (`domain/actions.py`, `api.py`) — оживает модалка и `/actions/[id]`.
4. **Telegram-бот** (привязка, тревоги, кнопки с HMAC, код).
5. **Исполнитель `revoke_car_poa`** (сессия, скриншот, проверка через источник) — последний, нужен живой аккаунт/HAR (см. §13 открытые вопросы).

## Интеграционные тесты без Docker

Нужен Postgres с миграциями на :5433 (`make db`). Если Docker нет, а в системе нет pgvector: локальный кластер
PG18 + пустая заглушка расширения `vector` через `extension_control_path`, миграции без `assistant/` — для guard хватает.
Ключи `MASTER_KEY` и др. — любые 32 байта base64 в env.

## Как запустить / проверить фронтенд
```bash
cd web
npm ci            # зависимости
npm run typecheck # чисто
npm run build     # собирает /alerts, /actions/[id], /family, /documents/[id], ...
npm run dev       # http://localhost:3000  (проксит /api → API_PROXY_URL, по умолч. :8000)
```

## Где что лежит
- Фронтенд guard: `web/features/guard/*`, кит `web/components/mygov/*`, i18n `web/lib/i18n/*`.
- Бэкенд guard: `backend/storozh/guard/*`, тесты `backend/tests/guard/*`, миграции `backend/storozh/migrations/guard/*`.
- Контракт API/событий: `contracts/openapi.yaml`, общий обзор `docs/00-project-overview.md` §9–12.
