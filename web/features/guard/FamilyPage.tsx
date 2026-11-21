"use client";

import { Card, PageHeader } from "@/components/mygov";
import { useI18n } from "@/lib/i18n";

// Разработчик 3: Кто имеет доступ к моим данным и к чьим имею я.
export function FamilyPage() {
  const { t } = useI18n();
  return (
    <>
      <PageHeader title={t("family.title")} subtitle={t("family.subtitle")} />
      <Card>TODO</Card>
    </>
  );
}
