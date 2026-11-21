#!/usr/bin/env bash
# Деплой/обновление на сервере. Запуск из корня кода: bash infra/deploy/deploy.sh
# Репо приватное, токена GitHub на сервере нет: код заливается архивом (git archive) в ~/justina.
# Если на сервере есть клон с доступом — SKIP_PULL=0 bash infra/deploy/deploy.sh [ветка]
set -euo pipefail
BRANCH="${1:-main}"
cd "$(dirname "$0")/../.."

if [ "${SKIP_PULL:-1}" = "0" ]; then
  git fetch origin "$BRANCH" && git checkout "$BRANCH" && git pull --ff-only origin "$BRANCH"
fi

if [ ! -f .env ]; then
  echo "Создаю .env с новыми секретами"
  rnd() { python3 -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"; }
  cp .env.example .env
  sed -i "s|^ENV=.*|ENV=dev|" .env   # TODO(Р2): ENV=demo, когда будет вход через Telegram; пока гражданин-заглушка
  for k in MASTER_KEY PINFL_HMAC_KEY INGEST_HMAC_KEY CALLBACK_HMAC_KEY; do sed -i "s|^$k=.*|$k=$(rnd)|" .env; done
  sed -i "s|^PUBLIC_WEB_URL=.*|PUBLIC_WEB_URL=https://justina.clusteros.co.uz|" .env
  sed -i "s|^API_INTERNAL_URL=.*|API_INTERNAL_URL=http://api:8000|" .env
  chmod 600 .env
fi

C="docker compose -p justina -f infra/docker-compose.yml -f infra/docker-compose.prod.yml"
# Сервер общий с соседним проектом: собираем по одному образу и с низким приоритетом, чтобы не душить соседей
COMPOSE_PARALLEL_LIMIT=1 nice -n 19 $C build
$C up -d

# Caddy сервера живёт в сети clusteros-net. Подключаем веб вручную: через compose сервис получил бы
# сетевой алиас «web», который в этой сети уже занят соседним проектом. Повторять после каждого up.
PROXY_NET="${PROXY_NET:-clusteros-net}"
if docker network inspect "$PROXY_NET" >/dev/null 2>&1; then
  docker network connect "$PROXY_NET" justina-web-1 2>/dev/null || true
fi
$C ps
