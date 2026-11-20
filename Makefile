# Короткие команды для всех. Запуск из корня репо.
COMPOSE = docker compose -f infra/docker-compose.yml

.PHONY: up db mock down test lint check eval gen-api web

up:            ## всё: база, миграции, API :8000, воркеры, бот, веб :3000
	$(COMPOSE) up --build

db:            ## только Postgres :5433 + миграции
	$(COMPOSE) up -d db migrate

mock:          ## Prism-мок по contracts/openapi.yaml на :4010
	$(COMPOSE) --profile mock up mock

down:
	$(COMPOSE) down

test:          ## pytest (интеграционные — если поднята база)
	cd backend && uv run pytest -q

lint:          ## ruff + границы контекстов
	cd backend && uv run ruff check . && uv run lint-imports

check: lint test   ## то же, что CI для бэкенда

eval:          ## доля попаданий RAG (FR-A-10)
	cd backend && uv run python -m storozh.assistant.eval.run

gen-api:       ## TS-типы из contracts/openapi.yaml
	cd web && npm run gen:api

web:           ## фронтенд в режиме разработки :3000
	cd web && npm run dev
