# Деплой на justina.clusteros.co.uz

Сервер общий с соседним проектом (Hetzner, 49.13.148.21, пользователь `clusteros`, алиас `ssh clusteros-dev`).
Подключайтесь одним общим соединением: сервер режет всплески новых подключений.

```bash
ssh -o ControlMaster=auto -o ControlPath=$TMPDIR/cm-dev -o ControlPersist=30m -o ConnectTimeout=60 clusteros-dev
```

## Автодеплой (GitHub Actions)

После зелёного `ci` на `main` workflow `.github/workflows/deploy.yml` сам заливает код архивом и запускает `deploy.sh`,
потом проверяет сайт. Один раз нужно добавить секреты репозитория (Settings → Secrets and variables → Actions):

| Секрет | Что |
| --- | --- |
| `DEPLOY_SSH_KEY` | приватный ключ деплоя; публичная часть в `~/.ssh/authorized_keys` пользователя на сервере |
| `DEPLOY_HOST` | адрес сервера |
| `DEPLOY_USER` | пользователь на сервере |
| `DEPLOY_KNOWN_HOSTS` | вывод `ssh-keyscan -t ed25519 <host>` (проверка отпечатка сервера) |

Без секретов workflow ничего не ломает: пишет предупреждение и пропускает деплой. Ручной запуск с заливкой демо-данных:
Actions → deploy → Run workflow → `seed`. Ниже — ручной способ на случай, если Actions недоступны.

## Обновить вручную

Репо приватное, токена GitHub на сервере нет — код заливается архивом:

```bash
git archive --format=tar.gz origin/main | ssh clusteros-dev 'mkdir -p ~/justina && tar -xz -C ~/justina'
```

```bash
ssh clusteros-dev 'cd ~/justina && bash infra/deploy/deploy.sh > ~/justina-deploy.log 2>&1'
```

`deploy.sh` при первом запуске создаёт `.env` с новыми ключами (потом не трогает), собирает образы,
поднимает проект `justina` и подключает `justina-web-1` к сети `clusteros-net`.

## Caddy (один раз)

Прокси сервера — Caddy в контейнере `clusteros-caddy-1`, конфиг `/opt/clusteros/infra/server/Caddyfile`.
Блок — `Caddyfile-justina`. Порядок: бэкап → дописать блок → `caddy validate` → `caddy reload`.
Контейнер Caddy не перезапускаем: это простой соседнего проекта.

Подвох: файл смонтирован в контейнер по inode. Если Caddyfile на хосте заменили целиком (редактор, `sed -i`),
контейнер видит старую версию, и `caddy reload` отвечает «config is unchanged». Тогда скопируйте файл внутрь
контейнера (`docker cp`) и сделайте `caddy reload --config <копия>`; при следующем плановом рестарте Caddy
подхватит файл с хоста.

## Проверка

```bash
curl -sI https://justina.clusteros.co.uz/documents | head -1
```

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://justina.clusteros.co.uz/api/internal/ingest/snapshots
```

Первая должна вернуть 200, вторая — 404. Соседний `clusteros.co.uz` должен по-прежнему отвечать 200.

## Пока нет входа

`ENV=dev`: вместо входа — гражданин-заглушка, сайт видят все. На сервере только демо-данные
(`storozh documents seed`). Живую сессию OneID через `connect` сюда не подключать, пока Р2 не сделал вход.

## RAG: корпус lex.uz и индекс — автоматически

Отдельно запускать ничего не нужно. Разовый сервис `rag-index` стартует при каждом `deploy.sh` (после `migrate`)
и выполняет `storozh rag ensure`:

- **база пустая** (первый деплой) — скачивает акты с lex.uz (~1 мин) и считает эмбеддинги (~3–4 мин на CPU);
- **изменился код RAG** — список актов в `sources.py`, парсер, нарезка на чанки, индексатор или модель эмбеддингов
  (`EMBEDDING_MODEL` в `.env`) — перезагружает корпус и/или пересчитывает индекс;
- **ничего не менялось** — выходит за секунды.

Отпечатки хранятся в `assistant.rag_state`. Индексация идёт в фоне и не блокирует сайт; пока она идёт, поиск
работает по полнотексту, эмбеддинги догружаются. Модель Hugging Face и кэш lex.uz лежат в томах `hfcache` и
`lexcache` и переживают пересборку контейнеров. lex.uz недоступен, а корпус уже есть — деплой не падает,
остаётся прежний корпус.

```bash
docker compose -p justina -f infra/docker-compose.yml -f infra/docker-compose.prod.yml logs -f rag-index
```

Принудительно всё пересчитать: `... run --rm rag-index python -m storozh rag ensure --force`.
