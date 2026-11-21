"""Журнал аудита и хранилище ключей на настоящей базе."""

import uuid

import psycopg

from storozh.shared import audit, crypto, db
from storozh.shared.config import settings
from tests.integration.conftest import requires_db

pytestmark = requires_db


async def test_audit_chain_detects_tampering():
    marker = f"test:{uuid.uuid4()}"
    async with db.connect("platform") as conn:
        for action in ("login", "action.confirmed", "logout"):
            await audit.write(conn, actor="citizen:test", action=action, target=marker)
    async with db.connect("platform") as conn:
        assert await audit.verify(conn) is None

    with psycopg.connect(settings.database_url, autocommit=True) as su:  # владелец базы, мимо ролей контекстов
        seq = su.execute("SELECT seq FROM shared.audit_log WHERE target = %s AND action = 'action.confirmed'",
                         (marker,)).fetchone()[0]
        su.execute("UPDATE shared.audit_log SET action = 'action.rejected' WHERE seq = %s", (seq,))
        try:
            async with db.connect("platform") as conn:
                assert await audit.verify(conn) == seq
        finally:
            su.execute("UPDATE shared.audit_log SET action = 'action.confirmed' WHERE seq = %s", (seq,))
    async with db.connect("platform") as conn:
        assert await audit.verify(conn) is None


def test_data_key_persisted_and_hidden_from_contexts():
    cid = uuid.uuid4()
    crypto.forget_cached_keys()
    blob = crypto.encrypt(cid, b"state")
    crypto.forget_cached_keys()  # следующий decrypt читает DEK из базы
    assert crypto.decrypt(cid, blob) == b"state"
    with psycopg.connect(settings.database_url) as conn:
        conn.execute("SET ROLE storozh_documents")
        try:
            conn.execute("SELECT * FROM shared.data_keys")
            raise AssertionError("documents role must not read data keys")
        except psycopg.errors.InsufficientPrivilege:
            pass
