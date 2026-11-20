# contracts/ — фиксируем первыми, втроём

Пока контракт не влит, код по нему не пишем. После — каждый работает независимо:
фронтенд берёт ответы из Prism-мока (`make mock`, порт 4010),
бэкенд реализует ровно эти пути и схемы.

| Файл | Что | Зеркало в коде |
|---|---|---|
| `openapi.yaml` | HTTP API для веба | роутеры `*/api.py`, типы `web/lib/api/schema.d.ts` (`make gen-api`) |
| `schemas/normalized_document.schema.json` | Нормализованный документ | `storozh/shared/contracts.py` |
| `schemas/source_snapshot.schema.json` | Снимок источника — единственный вход данных | `storozh/shared/contracts.py` |
| `events/envelope.schema.json` | Конверт события | `storozh/shared/events.py` |
| `events/<type>.v1.schema.json` | Данные каждого события | `TOPICS` в `storozh/shared/events.py` |
| `examples/*.json` | Примеры — их же гоняют тесты и мок | — |

## Правила

- Меняется только PR с **двумя апрувами** (ветка `main` защищена).
- Версии событий: новое поле — можно в `/v1`; удалить или переименовать — только `/v2`,
  старую версию продюсер шлёт, пока её читают.
- URI документа: `uz:{реестр}:{тип}:{номер}`, не меняется никогда (таблица типов — на доске).
- Хеш версии = SHA-256 канонического JSON (ключи по алфавиту, без `source_ref.url`).
- `backend/tests/test_contracts.py` падает, если:
  - путь из `openapi.yaml` не реализован в FastAPI или наоборот;
  - пример не проходит JSON Schema или Pydantic-модель;
  - тип события есть в коде, но нет схемы (и наоборот).
