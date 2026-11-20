"""Публичный API модуля corpus. Другие модули импортируют только отсюда."""

import logging

from storozh.assistant.rag.corpus import lexuz, repo
from storozh.assistant.rag.corpus.parser import parse_bilingual
from storozh.assistant.rag.corpus.sources import BY_CODE, SOURCES, Source
from storozh.assistant.rag.db import connection

log = logging.getLogger(__name__)

__all__ = ["SOURCES", "BY_CODE", "Source", "ingest", "articles", "articles_by_ids", "articles_by_keys",
           "referenced_articles", "article_url"]


def ingest(codes: list[str] | None = None, refresh: bool = False) -> dict[str, dict[str, int]]:
    stats: dict[str, dict[str, int]] = {}
    for src in SOURCES:
        if codes and src.code not in codes:
            continue
        page = lexuz.fetch_bilingual(src.lex_id, refresh=refresh)
        ru_id = lexuz.russian_version_id(page) or src.lex_id
        if ru_id != src.lex_id:  # узбекский оригинал: берём страницу русского перевода (ru + uz латиница)
            page = lexuz.fetch_bilingual(ru_id, refresh=refresh)
        docs = parse_bilingual(page, ru_id)
        with connection() as conn:
            for doc in docs.values():
                repo.replace_document(conn, src, doc)
        stats[src.code] = {lang: len(d.articles) for lang, d in docs.items()}
        log.info("ingested %s: %s", src.code, stats[src.code])
    return stats


def articles(lang: str | None = None, codes: list[str] | None = None) -> list[dict]:
    with connection() as conn:
        return repo.articles(conn, lang, codes)


def articles_by_ids(ids: list[int]) -> list[dict]:
    with connection() as conn:
        return repo.by_ids(conn, ids)


def articles_by_keys(keys: list[tuple[str, str]]) -> list[dict]:
    with connection() as conn:
        return repo.by_keys(conn, keys)


def referenced_articles(article_ids: list[int]) -> list[dict]:
    with connection() as conn:
        return repo.referenced(conn, article_ids)


def article_url(article: dict) -> str:
    return lexuz.doc_url(article["lex_id"], article["lang"], article["elem_id"])
