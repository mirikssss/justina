"""T8: лимит частоты и закрытая схема API."""

import httpx
import pytest

from storozh.shared import ratelimit
from storozh.shared.config import settings


def test_sliding_window_blocks_and_recovers():
    w = ratelimit.SlidingWindow()
    lim = ratelimit.Limit("POST", ratelimit.re.compile("x"), 3, 60)
    assert all(w.allow(0, "ip", lim, now=t)[0] for t in (0, 1, 2))
    ok, retry = w.allow(0, "ip", lim, now=3)
    assert not ok and 1 <= retry <= 58
    assert w.allow(0, "other-ip", lim, now=3)[0]  # у другого адреса своё окно
    assert w.allow(0, "ip", lim, now=61)[0]  # окно сдвинулось


@pytest.fixture
def app_factory(monkeypatch):
    from storozh import main

    ratelimit.window.reset()

    def make(**over):
        for k, v in over.items():
            monkeypatch.setattr(settings, k, v)
        return main.create_app()

    yield make
    ratelimit.window.reset()


async def test_confirm_is_rate_limited_per_ip(app_factory):
    app = app_factory()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://x") as cl:
        url = "/guard/actions/00000000-0000-0000-0000-000000000000/confirm"
        codes = [(await cl.post(url, json={"code": "12"}, headers={"x-forwarded-for": "1.2.3.4"})).status_code
                 for _ in range(11)]
        assert codes[:10] == [422] * 10 and codes[10] == 429  # 11-й запрос за минуту
        r = await cl.post(url, json={"code": "12"}, headers={"x-forwarded-for": "5.6.7.8"})
        assert r.status_code == 422


async def test_docs_closed_when_disabled(app_factory):
    app = app_factory(docs_enabled=False)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://x") as cl:
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert (await cl.get(path)).status_code == 404
