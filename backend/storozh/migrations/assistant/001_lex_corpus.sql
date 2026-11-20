-- Корпус норм lex.uz (Помощник). Расширение vector создаётся в shared/000.

-- Один нормативный акт на одном языке (ru / uz = узбекская латиница).
CREATE TABLE documents (
    id           bigserial PRIMARY KEY,
    lex_id       bigint      NOT NULL,          -- id документа на lex.uz (общий для языков)
    lang         text        NOT NULL,
    code         text        NOT NULL,          -- короткий ключ: gk1, tk, sk ...
    title        text        NOT NULL,
    url          text        NOT NULL,
    fetched_at   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (lex_id, lang)
);

-- Статья — атомарная юридическая единица и единица цитирования.
CREATE TABLE articles (
    id           bigserial PRIMARY KEY,
    document_id  bigint  NOT NULL REFERENCES documents ON DELETE CASCADE,
    lex_id       bigint  NOT NULL,
    lang         text    NOT NULL,
    code         text    NOT NULL,
    elem_id      bigint  NOT NULL,              -- якорь на lex.uz: url#elem_id
    number       text    NOT NULL,              -- "1", "12-1"
    title        text    NOT NULL,
    path         text[]  NOT NULL,              -- Раздел > Глава > ...
    body         text    NOT NULL,
    amendments   text[]  NOT NULL DEFAULT '{}',
    ordinal      int     NOT NULL,
    UNIQUE (document_id, elem_id)
);
CREATE INDEX articles_key ON articles (code, number, lang);

-- Ссылки статьи на другие акты/статьи (граф для раскрытия контекста).
CREATE TABLE refs (
    src_article_id bigint NOT NULL REFERENCES articles ON DELETE CASCADE,
    dst_lex_id     bigint NOT NULL,
    dst_elem_id    bigint,
    anchor         text
);
CREATE INDEX refs_src ON refs (src_article_id);
CREATE INDEX refs_dst ON refs (dst_lex_id, dst_elem_id);

-- Чанки для поиска (обычно 1 статья = 1 чанк, длинные режутся по частям).
CREATE TABLE chunks (
    id           bigserial PRIMARY KEY,
    article_id   bigint  NOT NULL REFERENCES articles ON DELETE CASCADE,
    lang         text    NOT NULL,
    part         int     NOT NULL DEFAULT 0,
    content      text    NOT NULL,              -- то, что видит LLM и пользователь
    context      text,                          -- contextual retrieval: LLM-пояснение
    tsv          tsvector,
    embedding    vector(1024)
);
CREATE INDEX chunks_article ON chunks (article_id);
CREATE INDEX chunks_tsv ON chunks USING gin (tsv);
CREATE INDEX chunks_emb ON chunks USING hnsw (embedding vector_cosine_ops);

-- retrieval/index.py::ensure_dim пересоздаёт колонку embedding под размерность модели: нужен владелец.
ALTER TABLE chunks OWNER TO storozh_assistant;
