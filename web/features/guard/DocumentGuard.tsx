import { Button, Card } from "@/components/mygov";

// Разработчик 3: тревоги по документу, «Отозвать» (POST /guard/actions -> код в Telegram -> модалка), «Скачать заявление по ст. 31».
export function DocumentGuard({ documentId }: { documentId: string }) {
  return (
    <Card title="Защита">
      <div className="flex gap-3" data-document-id={documentId}>
        <Button variant="danger" disabled>
          Bu men emasman — отозвать
        </Button>
        <Button variant="secondary" disabled>
          Заявление по ст. 31
        </Button>
      </div>
    </Card>
  );
}
