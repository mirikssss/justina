"""T8: ограничение частоты на вход и подтверждение действий (скользящее окно в памяти процесса).

Один процесс api в прототипе — памяти достаточно. В целевом состоянии — тот же интерфейс поверх Redis или шлюза.
Ключ — IP клиента (первый адрес X-Forwarded-For от нашего прокси, иначе адрес соединения): API наружу не
опубликован, до него доходят только запросы через web/nginx.
"""

import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import FastAPI, Request

from storozh.shared.config import settings
from storozh.shared.problem import problem


@dataclass(frozen=True)
class Limit:
    method: str
    path: re.Pattern[str]
    max_requests: int
    window_s: float


LIMITS = (
    Limit("POST", re.compile(r"^/auth/telegram/start$"), 10, 60),
    Limit("GET", re.compile(r"^/auth/callback$"), 20, 60),
    Limit("POST", re.compile(r"^/guard/actions/[^/]+/confirm$"), 10, 60),
    Limit("POST", re.compile(r"^/guard/actions$"), 20, 60),
    Limit("POST", re.compile(r"^/guard/telegram/link$"), 10, 60),
)


class SlidingWindow:
    def __init__(self) -> None:
        self._hits: dict[tuple[int, str], deque[float]] = defaultdict(deque)

    def allow(self, rule: int, key: str, limit: Limit, now: float | None = None) -> tuple[bool, int]:
        """(разрешено, через сколько секунд можно снова)."""
        now = time.monotonic() if now is None else now
        q = self._hits[(rule, key)]
        while q and q[0] <= now - limit.window_s:
            q.popleft()
        if len(q) >= limit.max_requests:
            return False, max(1, int(q[0] + limit.window_s - now) + 1)
        q.append(now)
        if len(self._hits) > 50_000:  # защита памяти: выкидываем пустые окна
            for k in [k for k, v in self._hits.items() if not v]:
                del self._hits[k]
        return True, 0

    def reset(self) -> None:
        self._hits.clear()


window = SlidingWindow()


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def _rate_limit(request: Request, call_next):
        if settings.rate_limit_enabled:
            for i, limit in enumerate(LIMITS):
                if request.method == limit.method and limit.path.match(request.url.path):
                    ok, retry = window.allow(i, client_ip(request), limit)
                    if not ok:
                        resp = problem(429, "Too many requests")
                        resp.headers["Retry-After"] = str(retry)
                        return resp
                    break
        return await call_next(request)
