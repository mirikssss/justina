"""Одно FastAPI-приложение: роутеры всех контекстов. Каждый контекст подключает только свой api.py."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from storozh.assistant.api import router as assistant_router
from storozh.documents.api import internal as documents_internal
from storozh.documents.api import router as documents_router
from storozh.guard.api import router as guard_router
from storozh.platform import public as platform_public
from storozh.platform.api import router as platform_router
from storozh.shared import auth, db, problem


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await db.close_all()


def create_app() -> FastAPI:
    app = FastAPI(title="Сторож сделок", version="0.1.0", lifespan=lifespan)
    problem.install(app)
    auth.set_session_resolver(platform_public.session_citizen)
    for r in (platform_router, documents_router, documents_internal, guard_router, assistant_router):
        app.include_router(r)

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
