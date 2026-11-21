"""storozh rag ensure: при деплое работает только то, что изменилось (тяжёлые шаги подменены)."""

import pytest

from storozh.assistant.rag import ensure as ens
from storozh.assistant.rag.db import connection
from storozh.shared.config import settings
from tests.integration.conftest import requires_db

pytestmark = requires_db


@pytest.fixture
def calls(monkeypatch):
    seen = {"ingest": 0, "reindex": 0}
    monkeypatch.setattr(ens.corpus, "ingest", lambda: seen.__setitem__("ingest", seen["ingest"] + 1) or {})
    monkeypatch.setattr(ens.retrieval, "reindex", lambda: seen.__setitem__("reindex", seen["reindex"] + 1)
                        or {"chunks": 0, "embedded": 0})
    monkeypatch.setattr(ens, "_drop_removed_acts", lambda conn: 0)  # корпус разработчика не трогаем
    # подменённый ingest ничего не вставляет: считаем корпус непустым, иначе в чистой базе (CI) каждый запуск «загружал» бы заново
    monkeypatch.setattr(ens, "_counts", lambda conn: {"articles": 10, "chunks": 10, "missing": 0})
    with connection() as conn:
        saved = conn.execute("SELECT key, value, detail FROM rag_state").fetchall()
        conn.execute("DELETE FROM rag_state")
    yield seen
    with connection() as conn:  # вернуть состояние базы разработчика
        conn.execute("DELETE FROM rag_state")
        for r in saved:
            ens._save(conn, r["key"], r["value"], r["detail"])


def test_ensure_runs_only_what_changed(calls, monkeypatch):
    first = ens.ensure()
    assert first["ingested"] and first["reindexed"] and calls == {"ingest": 1, "reindex": 1}

    second = ens.ensure()  # ничего не менялось — ни скачивания, ни индексации
    assert not second["ingested"] and not second["reindexed"] and calls == {"ingest": 1, "reindex": 1}

    monkeypatch.setattr(settings, "embedding_model", "BAAI/bge-m3")  # сменили модель — только переиндексация
    third = ens.ensure()
    assert not third["ingested"] and third["reindexed"] and calls == {"ingest": 1, "reindex": 2}


def test_lexuz_down_keeps_existing_corpus(calls, monkeypatch):
    def boom():
        raise ConnectionError("lex.uz down")

    monkeypatch.setattr(ens.corpus, "ingest", boom)
    monkeypatch.setattr(ens, "_counts", lambda conn: {"articles": 10, "chunks": 10, "missing": 0})
    report = ens.ensure()  # корпус уже есть: деплой не падает, старый корпус остаётся
    assert not report["ingested"]
