"""Индексация: статьи -> чанки (tsvector + эмбеддинги). Таблица chunks принадлежит этому модулю."""

import logging

from storozh.assistant.rag.corpus import service as corpus
from storozh.assistant.rag.corpus.text import uz_terms
from storozh.assistant.rag.db import connection
from storozh.assistant.rag.retrieval import embeddings
from storozh.assistant.rag.retrieval.chunking import chunk_article
from storozh.shared.config import settings

log = logging.getLogger(__name__)
EMBED_PAGE = 128


def _fts(a: dict, text: str) -> tuple[str, str, str]:
    """(regconfig, заголовок, текст) для tsvector. Заголовок статьи получает вес A — он самый информативный."""
    if a["lang"] == "ru":
        return "russian", a["title"], text
    return "simple", " ".join(uz_terms(a["title"])), " ".join(uz_terms(text))


_TSV = "setweight(to_tsvector(%s::regconfig, %s), 'A') || to_tsvector(%s::regconfig, %s)"


def rebuild_chunks(codes: list[str] | None = None) -> int:
    arts = corpus.articles(codes=codes)
    ids = [a["id"] for a in arts]
    rows = []
    for a in arts:
        for c in chunk_article(a):
            cfg, title, text = _fts(a, c.content)
            rows.append((c.article_id, c.lang, c.part, c.content, cfg, title, cfg, text))
    with connection() as conn:
        conn.execute("DELETE FROM chunks WHERE article_id = ANY(%s)", (ids,))
        with conn.cursor() as cur:
            cur.executemany(
                f"INSERT INTO chunks (article_id, lang, part, content, tsv) VALUES (%s, %s, %s, %s, {_TSV})",
                rows,
            )
    return len(rows)


def refresh_tsv() -> int:
    """Пересчитать только tsvector (без эмбеддингов) — после изменений в нормализации текста."""
    by_id = {a["id"]: a for a in corpus.articles()}
    with connection() as conn:
        chunks = conn.execute("SELECT id, article_id, content FROM chunks").fetchall()
        rows = []
        for c in chunks:
            cfg, title, text = _fts(by_id[c["article_id"]], c["content"])
            rows.append((cfg, title, cfg, text, c["id"]))
        with conn.cursor() as cur:
            cur.executemany(f"UPDATE chunks SET tsv = {_TSV} WHERE id = %s", rows)
    return len(rows)


def ensure_dim() -> None:
    """Подгоняем размерность колонки под текущую модель (при смене модели эмбеддинги пересчитываются)."""
    dim = settings.embedding_dim
    with connection() as conn:
        cur = conn.execute(
            "SELECT atttypmod FROM pg_attribute WHERE attrelid = 'chunks'::regclass AND attname = 'embedding'"
        ).fetchone()["atttypmod"]
        if cur != dim:
            log.info("embedding dim %s -> %s, пересоздаю колонку", cur, dim)
            conn.execute("DROP INDEX IF EXISTS chunks_emb")
            conn.execute("ALTER TABLE chunks DROP COLUMN embedding")
            conn.execute(f"ALTER TABLE chunks ADD COLUMN embedding vector({dim})")
            conn.execute("CREATE INDEX chunks_emb ON chunks USING hnsw (embedding vector_cosine_ops)")


def embed_missing() -> int:
    ensure_dim()
    done = 0
    while True:
        with connection() as conn:
            batch = conn.execute(
                "SELECT id, content, context FROM chunks WHERE embedding IS NULL ORDER BY id LIMIT %s", (EMBED_PAGE,)
            ).fetchall()
        if not batch:
            return done
        texts = [f"{r['context']}\n{r['content']}" if r["context"] else r["content"] for r in batch]
        vecs = embeddings.embed(texts)
        with connection() as conn, conn.cursor() as cur:
            cur.executemany(
                "UPDATE chunks SET embedding = %s::vector WHERE id = %s",
                [(v, r["id"]) for v, r in zip(vecs, batch)],
            )
        done += len(batch)
        log.info("embedded %d chunks", done)
