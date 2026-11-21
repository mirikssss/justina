"use client";

import { useEffect, useState } from "react";

import { Button, Card } from "@/components/mygov";
import { api } from "@/lib/api/client";
import { useI18n } from "@/lib/i18n";

// UC-P1: POST /auth/telegram/start -> ссылка на бота (5 минут) -> бот присылает одноразовую ссылку
// /api/auth/callback?token=… -> cookie сессии -> /documents. Просроченная ссылка возвращает сюда с ?error=expired.
export function LoginScreen() {
  const { t } = useI18n();
  const [link, setLink] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("error") === "expired") {
      setError(t("login.expired"));
    }
  }, [t]);

  async function start() {
    setBusy(true);
    setError(null);
    const { data, error: e } = await api.POST("/auth/telegram/start");
    setBusy(false);
    if (e !== undefined || !data) {
      setError(t("login.failed"));
      return;
    }
    setLink(data.deep_link);
    window.open(data.deep_link, "_blank", "noopener");
  }

  return (
    <div className="mx-auto mt-24 max-w-md">
      <Card title={t("login.title")}>
        <p className="mb-4 text-sm text-muted">{t("login.lead")}</p>
        {error ? <p className="mb-4 text-sm" role="alert">{error}</p> : null}
        <Button onClick={start} disabled={busy}>{busy ? "…" : t("login.button")}</Button>
        {link ? (
          <p className="mt-4 text-sm">
            {t("login.fallback")} <a href={link} target="_blank" rel="noopener noreferrer">{link}</a>
          </p>
        ) : null}
      </Card>
    </div>
  );
}
