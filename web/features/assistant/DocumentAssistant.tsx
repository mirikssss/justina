import { Card } from "@/components/mygov";

// Разработчик 3: блок резюме (GET /assist/documents/{id}/summary) и боковой чат (POST /assist/chat, SSE).
// Ссылки на статьи открывают lex.uz.
export function DocumentAssistant({ documentId }: { documentId: string }) {
  return (
    <Card title="Помощник">
      <p className="text-sm text-muted" data-document-id={documentId}>
        Что это · что может другая сторона · чем рисковано · что делать
      </p>
    </Card>
  );
}
