"use client";

import { Card, PageHeader } from "@/components/mygov";
import { useI18n } from "@/lib/i18n";

// Разработчик 3: Список по важности, кнопки «Это я» и «Это не я».
export function AlertsPage() {
  const { t } = useI18n();
  return (
    <>
      <PageHeader title={t("alerts.title")} subtitle={t("alerts.subtitle")} />
      <Card>TODO</Card>
    </>
  );
}
