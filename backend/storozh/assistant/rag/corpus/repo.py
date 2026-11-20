"""Запись/чтение корпуса в Postgres. Пишет в таблицы documents/articles/refs только этот модуль."""

from psycopg import Connection

from storozh.assistant.rag.corpus.lexuz import doc_url
from storozh.assistant.rag.corpus.parser import ParsedDoc
from storozh.assistant.rag.corpus.sources import Source


def replace_document(conn: Connection, src: Source, doc: ParsedDoc) -> int:
    lex_id = doc.lex_id or src.lex_id
    conn.execute("DELETE FROM documents WHERE code = %s AND lang = %s", (src.code, doc.lang))
    doc_id = conn.execute(
        "INSERT INTO documents (lex_id, lang, code, title, url) VALUES (%s,%s,%s,%s,%s) RETURNING id",
        (lex_id, doc.lang, src.code, doc.title or src.name_ru, doc_url(lex_id, doc.lang)),
    ).fetchone()["id"]

    for i, a in enumerate(doc.articles):
        art_id = conn.execute(
            """INSERT INTO articles (document_id, lex_id, lang, code, elem_id, number, title, path, body, amendments, ordinal)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (document_id, elem_id) DO NOTHING RETURNING id""",
            (doc_id, lex_id, doc.lang, src.code, a.elem_id, a.number, a.title, a.path, a.body, a.amendments, i),
        ).fetchone()
        if art_id and a.refs:
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO refs (src_article_id, dst_lex_id, dst_elem_id, anchor) VALUES (%s,%s,%s,%s)",
                    [(art_id["id"], r.lex_id, r.elem_id, r.anchor[:200]) for r in a.refs],
                )
    return doc_id


_ART_COLS = "a.id, a.lex_id, a.lang, a.code, a.elem_id, a.number, a.title, a.path, a.body, d.title AS doc_title"


def articles(conn: Connection, lang: str | None = None, codes: list[str] | None = None) -> list[dict]:
    sql = f"SELECT {_ART_COLS} FROM articles a JOIN documents d ON d.id = a.document_id WHERE true"
    args: list = []
    if lang:
        sql += " AND a.lang = %s"
        args.append(lang)
    if codes:
        sql += " AND a.code = ANY(%s)"
        args.append(codes)
    return conn.execute(sql + " ORDER BY a.code, a.lang, a.ordinal", args).fetchall()


def by_ids(conn: Connection, ids: list[int]) -> list[dict]:
    return conn.execute(
        f"SELECT {_ART_COLS} FROM articles a JOIN documents d ON d.id = a.document_id WHERE a.id = ANY(%s)", (ids,)
    ).fetchall()


def by_keys(conn: Connection, keys: list[tuple[str, str]]) -> list[dict]:
    """keys = [(code, number)] -> статьи на всех языках."""
    if not keys:
        return []
    codes, numbers = zip(*keys)
    return conn.execute(
        f"""SELECT {_ART_COLS} FROM articles a JOIN documents d ON d.id = a.document_id
            JOIN unnest(%s::text[], %s::text[]) AS k(code, number) ON k.code = a.code AND k.number = a.number""",
        (list(codes), list(numbers)),
    ).fetchall()


def referenced(conn: Connection, article_ids: list[int]) -> list[dict]:
    """Статьи, на которые ссылаются данные (1 шаг по графу; только то, что есть в корпусе)."""
    return conn.execute(
        f"""SELECT DISTINCT ON (a.id) r.src_article_id, {_ART_COLS}
            FROM refs r
            JOIN articles a ON a.lex_id = r.dst_lex_id AND a.elem_id = r.dst_elem_id
            JOIN documents d ON d.id = a.document_id
            WHERE r.src_article_id = ANY(%s)""",
        (article_ids,),
    ).fetchall()
