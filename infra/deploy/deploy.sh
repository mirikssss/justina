#!/usr/bin/env bash
# Деплой/обновление на сервере. Запуск из корня клона: bash infra/deploy/deploy.sh [ветка]
set -euo pipefail
BRANCH="${1:-main}"
cd "$(dirname "$0")/../.."

git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

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
$C build
$C up -d
$C ps
