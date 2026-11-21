"use client";

import { Card, PageHeader } from "@/components/mygov";
import { useI18n } from "@/lib/i18n";

// Разработчик 3: шаги состояния вживую по SSE (action.updated), в конце — «Подтверждено источником: отозвана» и скриншот.
export function ActionPage({ id }: { id: string }) {
  const { t } = useI18n();
  return (
    <>
      <PageHeader title={t("action.title")} subtitle={id} />
      <Card>TODO: proposed → awaiting_confirmation → confirmed → executing → verifying → done</Card>
    </>
  );
}
