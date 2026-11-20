import { Card, PageHeader } from "@/components/mygov";
import { DocumentAssistant } from "@/features/assistant";
import { DocumentGuard } from "@/features/guard";

// Разработчик 1: реквизиты, стороны, объект, статус, история версий с подсветкой изменённых полей.
// Два слота принадлежат другим контекстам: <DocumentGuard/> (Разработчик 3) и <DocumentAssistant/> (Разработчик 2).
export function DocumentPage({ id }: { id: string }) {
  return (
    <>
      <PageHeader title="Документ" subtitle={id} />
      <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
        <div className="space-y-5">
          <Card title="Реквизиты">TODO</Card>
          <Card title="История версий">TODO</Card>
          <DocumentGuard documentId={id} />
        </div>
        <DocumentAssistant documentId={id} />
      </div>
    </>
  );
}
