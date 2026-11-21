"use client";

import { Button, Card } from "@/components/mygov";
import { useT } from "@/lib/i18n";

// TODO(Разработчик 2): POST /auth/telegram/start -> ссылка на бота -> /auth/callback
export function LoginScreen() {
  const t = useT();
  return (
    <div className="mx-auto mt-24 max-w-md">
      <Card title={t("«Mening hujjatlarim»ga kirish")}>
        <p className="mb-4 text-sm text-muted">{t("Telegram-bot orqali kirish: havola bir martalik va 5 daqiqa amal qiladi.")}</p>
        <Button disabled>{t("Telegram orqali kirish")}</Button>
      </Card>
    </div>
  );
}
