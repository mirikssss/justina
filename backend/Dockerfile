# Один образ на все процессы бэкенда; что запускать — решает command в docker-compose.yml.
FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ ./
COPY contracts/ /app/contracts/
RUN uv sync --frozen --no-dev
ENV PATH="/app/backend/.venv/bin:$PATH"
CMD ["python", "-m", "storozh", "api"]

# Сборщик и исполнитель действий: + Chromium для Playwright
FROM base AS browser
# libatomic1 нужен драйверу Playwright, в python:3.12-slim его нет (иначе playwright install падает с кодом 127)
RUN apt-get update && apt-get install -y --no-install-recommends libatomic1 && rm -rf /var/lib/apt/lists/* \
    && playwright install --with-deps chromium
