import { Card, PageHeader } from "@/components/mygov";

// Разработчик 3: шаги состояния вживую по SSE (action.updated), в конце — «Подтверждено источником: отозвана» и скриншот.
export function ActionPage({ id }: { id: string }) {
  return (
    <>
      <PageHeader title="Ход действия" subtitle={id} />
      <Card>TODO: proposed → awaiting_confirmation → confirmed → executing → verifying → done</Card>
    </>
  );
}
