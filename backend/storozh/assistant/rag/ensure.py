"""Автоиндексация при деплое: `storozh rag ensure` (сервис rag-index в docker compose).

Считает отпечатки кода загрузки корпуса и индексации и сравнивает с сохранёнными в assistant.rag_state:
- корпус пуст или изменился код загрузки (список актов, парсер, разбор текста) — заново качаем акты с lex.uz;
- индекс пуст, есть чанки без эмбеддингов, изменились нарезка, индексатор или модель эмбеддингов,
  или корпус только что перезагружен — пересчитываем чанки и эмбеддинги.
Ничего не изменилось — выход за секунды, поэтому команду безопасно запускать при каждом деплое.
"""

import hashlib
import json
import logging
from pathlib import Path
from types import ModuleType

from psycopg.types.json import Jsonb

from storozh.assistant.rag.corpus import lexuz, parser, repo, sources
from storozh.assistant.rag.corpus import service as corpus
from storozh.assistant.rag.corpus import text as corpus_text
from storozh.assistant.rag.db import connection
from storozh.assistant.rag.retrieval import chunking, embeddings, index
from storozh.assistant.rag.retrieval import service as retrieval
from storozh.shared.config import settings

log = logging.getLogger(__name__)
_LOCK = 0x5702_0003  # два деплоя подряд не индексируют одновременно


def _digest(*parts: str | bytes) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p if isinstance(p, bytes) else p.encode())
        h.update(b"\x00")
    return h.hexdigest()


def _src(*modules: ModuleType) -> list[bytes]:
    return [Path(m.__file__).read_bytes() for m in modules]


def corpus_fingerprint() -> str:
    acts = json.dumps([(s.code, s.lex_id, s.unit) for s in sources.SOURCES])
    return _digest(acts, *_src(sources, parser, lexuz, corpus_text, repo))


def index_fingerprint() -> str:
    return _digest(settings.embedding_model, str(settings.embedding_dim), *_src(chunking, index, embeddings))


def _state(conn) -> dict[str, str]:
    return {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM rag_state").fetchall()}


def _save(conn, key: str, value: str, detail: dict) -> None:
    conn.execute(
        """INSERT INTO rag_state (key, value, detail, updated_at) VALUES (%s, %s, %s, now())
           ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, detail = EXCLUDED.detail, updated_at = now()""",
        (key, value, Jsonb(detail)),
    )


def _counts(conn) -> dict[str, int]:
    row = conn.execute(
        """SELECT (SELECT count(*) FROM articles) AS articles, (SELECT count(*) FROM chunks) AS chunks,
                  (SELECT count(*) FROM chunks WHERE embedding IS NULL) AS missing"""
    ).fetchone()
    return dict(row)


def _drop_removed_acts(conn) -> int:
    """Акты, убранные из sources.py, удаляются из корпуса (статьи и чанки — каскадом)."""
    codes = [s.code for s in sources.SOURCES]
    return conn.execute("DELETE FROM documents WHERE code <> ALL(%s)", (codes,)).rowcount


def ensure(force: bool = False) -> dict:
    report: dict = {"ingested": False, "reindexed": False}
    with connection() as lock_conn:
        lock_conn.execute("SELECT pg_advisory_lock(%s)", (_LOCK,))
        try:
            with connection() as conn:
                state, counts = _state(conn), _counts(conn)
            corpus_fp, index_fp = corpus_fingerprint(), index_fingerprint()
            report["before"] = counts

            if force or counts["articles"] == 0 or state.get("corpus") != corpus_fp:
                log.info("rag ensure: loading corpus from lex.uz (articles=%s)", counts["articles"])
                try:
                    stats = corpus.ingest()
                except Exception:
                    if counts["articles"] == 0:
                        raise  # корпуса нет вовсе — деплой должен это показать
                    log.exception("rag ensure: lex.uz unavailable, keeping the previous corpus")
                else:
                    with connection() as conn:
                        removed = _drop_removed_acts(conn)
                        _save(conn, "corpus", corpus_fp, {"acts": stats, "removed_documents": removed})
                    report["ingested"] = True

            with connection() as conn:
                counts = _counts(conn)
            if report["ingested"] or state.get("index") != index_fp or counts["chunks"] == 0:
                log.info("rag ensure: rebuilding chunks and embeddings (%s)", settings.embedding_model)
                report["index"] = retrieval.reindex()
                report["reindexed"] = True
            elif counts["missing"]:
                log.info("rag ensure: embedding %s chunks left from an interrupted run", counts["missing"])
                report["index"] = {"embedded": index.embed_missing()}
                report["reindexed"] = True
            if report["reindexed"]:
                with connection() as conn:
                    _save(conn, "index", index_fp, {"model": settings.embedding_model, **report["index"]})

            with connection() as conn:
                report["after"] = _counts(conn)
        finally:
            lock_conn.execute("SELECT pg_advisory_unlock(%s)", (_LOCK,))
    log.info("rag ensure: %s", report)
    return report
