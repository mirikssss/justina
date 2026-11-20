# Justina backend — legal RAG по кодексам Узбекистана

Модульный монолит на FastAPI + Postgres (pgvector). Модули общаются только через свои `service.py`
(проверяет `uv run lint-imports`).

```
app/modules/
  corpus/     lex.uz -> разбор -> documents / articles / refs   (владелец корпуса)
  retrieval/  чанки, tsvector, эмбеддинги, гибридный поиск        (владелец chunks)
  reasoning/  агент на Claude: поиск через инструменты, ответ со ссылками, проверка ссылок
```

## Как это работает

1. **Загрузка.** Для каждого акта из `corpus/sources.py` качаем с lex.uz двуязычную страницу
   (`?otherlang=4`: русский + узбекская латиница). Если документ — узбекский оригинал, сначала находим id
   русского перевода. HTML кэшируется в `data/lexuz_cache/`.
2. **Разбор.** Структура lex.uz: `TEXT_HEADER_DEFAULT` (часть/раздел/глава), `CLAUSE_DEFAULT` (статья),
   `ACT_TEXT` (абзац), `CHANGES_ORIGINS` (история изменений). Единица — **статья**: номер, заголовок,
   путь «Раздел > Глава», текст, якорь `elem_id` (ссылка `lex.uz/ru/docs/<id>#<elem_id>`),
   ссылки на другие статьи (граф `refs`). ru и uz версии одной статьи связаны ключом `(code, number)`.
3. **Индекс.** Статья -> чанк с «хлебными крошками» (длинные режутся по абзацам).
   Полнотекст: `russian` для ru, для узбекского — префиксы слов (агглютинация: *shartnomaning → shartn*),
   кириллица транслитерируется в латиницу. Плюс dense-эмбеддинги (HNSW).
4. **Поиск.** Точные ссылки («ст. 150 ГК», «217-modda MK») -> полнотекст + вектора -> RRF ->
   (опционально) cross-encoder rerank -> +1 шаг по графу ссылок. Ответ — на языке запроса.
5. **Ответ.** Claude (`claude-opus-5-5`) с инструментами `search_law` / `get_article` сам делает несколько
   поисков. Ссылки в ответе пишутся как `[[gk1:150]]`. Ссылки на статьи, которых агент не получал из корпуса,
   вырезаются.

## Запуск

```bash
docker compose up -d                       # из корня репо, Postgres на :5433
cd backend && uv sync
cp .env.example .env                       # ANTHROPIC_API_KEY=... (нужен для /ask)
uv run python -m app.cli ingest            # ~11 актов, ~30 сек (с кэшем — мгновенно)
uv run python -m app.cli index             # чанки + эмбеддинги
uv run python -m app.cli search "сосед затопил квартиру"
uv run python -m app.cli ask "Сколько дней отпуска мне положено?"
uv run python -m eval.run                  # recall@5 / MRR на eval/golden.jsonl
uv run uvicorn app.main:app --reload       # GET /search?q=..., POST /ask
```

Модель эмбеддингов задаётся в `.env`:
`EMBEDDING_MODEL=BAAI/bge-m3`, `EMBEDDING_DIM=1024` (лучше) или
`intfloat/multilingual-e5-small`, `384` (лёгкая, по умолчанию). После смены — `app.cli index`.
`RERANK_ENABLED=true` включает `bge-reranker-v2-m3`.
