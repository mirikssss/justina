# assistant/rag — legal RAG по кодексам Узбекистана

Часть контекста «Помощник». Таблицы — в схеме `assistant` (миграция `migrations/assistant/001_lex_corpus.sql`).
Подмодули общаются через свои `service.py`.

```
assistant/rag/
  corpus/     lex.uz -> разбор -> documents / articles / refs   (владелец корпуса)
  retrieval/  чанки, tsvector, эмбеддинги, гибридный поиск        (владелец chunks)
  ../llm/     агент на Claude: поиск через инструменты, ответ со ссылками, проверка ссылок
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
make db                                    # из корня репо: Postgres на :5433 + миграции
cd backend && uv sync
uv run python -m storozh rag ingest        # ~11 актов, ~30 сек (с кэшем — мгновенно)
uv run python -m storozh rag index         # чанки + эмбеддинги
uv run python -m storozh rag search "сосед затопил квартиру"
uv run python -m storozh rag ask "Сколько дней отпуска мне положено?"   # нужен ANTHROPIC_API_KEY
uv run python -m storozh.assistant.eval.run                  # recall@5 / MRR на assistant/eval/golden.jsonl
uv run python -m storozh api --reload      # GET /assist/search?q=..., POST /assist/ask
```

Модель эмбеддингов задаётся в `.env` (корень репо):
`EMBEDDING_MODEL=BAAI/bge-m3`, `EMBEDDING_DIM=1024` (лучше) или
`intfloat/multilingual-e5-small`, `384` (лёгкая, по умолчанию). После смены — `storozh rag index`.
`RERANK_ENABLED=true` включает `bge-reranker-v2-m3`.
