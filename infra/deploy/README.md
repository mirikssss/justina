# Деплой на justina.clusteros.co.uz

Сервер общий с соседним проектом (Hetzner, 49.13.148.21, пользователь `clusteros`, алиас `ssh clusteros-dev`).
Подключайтесь одним общим соединением: сервер режет всплески новых подключений.

```bash
ssh -o ControlMaster=auto -o ControlPath=$TMPDIR/cm-dev -o ControlPersist=30m -o ConnectTimeout=60 clusteros-dev
```

## Обновить

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
