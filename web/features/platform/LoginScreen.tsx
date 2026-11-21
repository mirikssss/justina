"use client";

import { useEffect, useState } from "react";

import { Button, Card } from "@/components/mygov";
import { api } from "@/lib/api/client";
import { useT } from "@/lib/i18n";

// UC-P1: POST /auth/telegram/start -> ссылка на бота (5 минут) -> бот присылает одноразовую ссылку
// /api/auth/callback?token=… -> cookie сессии -> /documents. Просроченная ссылка возвращает сюда с ?error=expired.
export function LoginScreen() {
  const t = useT();
  const [link, setLink] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("error") === "expired") {
      setError("expired");
    }
  }, []);

  async function start() {
    setBusy(true);
    setError(null);
    const { data, error: e } = await api.POST("/auth/telegram/start");
    setBusy(false);
    if (e !== undefined || !data) {
      setError("start");
      return;
    }
    setLink(data.deep_link);
    window.open(data.deep_link, "_blank", "noopener");
  }

  return (
    <div className="mx-auto mt-24 max-w-md">
      <Card title={t("«Mening hujjatlarim»ga kirish")}>
        <p className="mb-4 text-sm text-muted">
          {t("Telegram-bot orqali kirish: havola bir martalik va 5 daqiqa amal qiladi. Bot saytga kirish uchun havola yuboradi.")}
        </p>
        {error ? (
          <p className="mb-4 text-sm" role="alert">
            {error === "expired"
              ? t("Havola eskirgan yoki allaqachon ishlatilgan. Qaytadan kiring.")
              : t("Kirishni boshlab bo'lmadi. Qayta urinib ko'ring.")}
          </p>
        ) : null}
        <Button onClick={start} disabled={busy}>{busy ? "…" : t("Telegram orqali kirish")}</Button>
        {link ? (
          <p className="mt-4 text-sm">
            {t("Telegram ochilmagan bo'lsa:")} <a href={link} target="_blank" rel="noopener noreferrer">{link}</a>
          </p>
        ) : null}
      </Card>
    </div>
  );
}
