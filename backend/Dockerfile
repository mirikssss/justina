# Один образ на все процессы бэкенда; что запускать — решает command в docker-compose.yml.
# Порядок слоёв важен на общем сервере: тяжёлое (apt, зависимости, Chromium) — выше копирования исходников,
# чтобы правка кода не пересобирала их заново и не грузила соседей.
FROM python:3.12-slim AS deps
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1 PATH="/app/backend/.venv/bin:$PATH"
# WeasyPrint (PDF-черновики «Помощника»): Pango и шрифт с кириллицей
RUN apt-get update && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Сборщик и исполнитель действий: + Chromium для Playwright (ставится до копирования кода)
FROM deps AS browser-deps
# libatomic1 нужен драйверу Playwright, в python:3.12-slim его нет (иначе playwright install падает с кодом 127)
RUN apt-get update && apt-get install -y --no-install-recommends libatomic1 && rm -rf /var/lib/apt/lists/* \
    && playwright install --with-deps chromium

FROM deps AS base
COPY backend/ ./
COPY contracts/ /app/contracts/
RUN uv sync --frozen --no-dev
CMD ["python", "-m", "storozh", "api"]

FROM browser-deps AS browser
COPY backend/ ./
COPY contracts/ /app/contracts/
RUN uv sync --frozen --no-dev
CMD ["python", "-m", "storozh", "api"]
