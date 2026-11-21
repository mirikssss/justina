"use client";

import { useEffect, useState } from "react";

import { Button, Card } from "@/components/mygov";
import { api } from "@/lib/api/client";

// UC-P1: POST /auth/telegram/start -> ссылка на бота (5 минут) -> бот присылает одноразовую ссылку
// /api/auth/callback?token=… -> cookie сессии -> /documents. Просроченная ссылка возвращает сюда с ?error=expired.
export function LoginScreen() {
  const [link, setLink] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("error") === "expired") {
      setError("Ссылка устарела или уже использована. Войдите ещё раз.");
    }
  }, []);

  async function start() {
    setBusy(true);
    setError(null);
    const { data, error: e } = await api.POST("/auth/telegram/start");
    setBusy(false);
    if (e !== undefined || !data) {
      setError("Не удалось начать вход. Попробуйте ещё раз.");
      return;
    }
    setLink(data.deep_link);
    window.open(data.deep_link, "_blank", "noopener");
  }

  return (
    <div className="mx-auto mt-24 max-w-md">
      <Card title="Вход в «Мои документы»">
        <p className="mb-4 text-sm text-muted">
          Вход через Telegram-бота: ссылка одноразовая и действует 5 минут. Бот пришлёт ссылку для входа на сайт.
        </p>
        {error ? <p className="mb-4 text-sm" role="alert">{error}</p> : null}
        <Button onClick={start} disabled={busy}>{busy ? "…" : "Войти через Telegram"}</Button>
        {link ? (
          <p className="mt-4 text-sm">
            Если Telegram не открылся: <a href={link} target="_blank" rel="noopener noreferrer">{link}</a>
          </p>
        ) : null}
      </Card>
    </div>
  );
}
