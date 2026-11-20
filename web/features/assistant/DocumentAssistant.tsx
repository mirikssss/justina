import { Card, Icon } from "@/components/mygov";

// Разработчик 2: резюме (GET /assist/documents/{id}/summary, скелетон пока 202 -> summary.ready)
// и чат (POST /assist/chat, SSE: token, citations, done; история — GET /assist/chat/{id}).
// Вид перенесён из макета; данные пока не подключены.

export function AssistantSummary({ documentId }: { documentId: string }) {
  return (
    <Card title="AI xulosa" icon="bolt" tag="AI • lex.uz RAG">
      <div className="ai-sum" data-document-id={documentId}>
        <p>Bu nima · boshqa tomon nima qila oladi · xavflar · nima qilish kerak — havolalar bilan.</p>
      </div>
    </Card>
  );
}

export function AssistantChat({ documentId }: { documentId: string }) {
  return (
    <div className="chat" data-document-id={documentId}>
      <div className="chat-h">
        <div className="ca"><Icon name="bolt" /></div>
        <div><h3>AI yordamchi</h3><small>Ushbu hujjat bo&apos;yicha</small></div>
        <span className="lv"><Icon name="shield" size={12} /> lex.uz</span>
      </div>
      <div className="chat-body">
        <div className="msg bot">Assalomu alaykum. Ushbu hujjat bo&apos;yicha savollaringizga lex.uz bazasi asosida javob beraman.</div>
      </div>
      <form className="chat-in" onSubmit={(e) => e.preventDefault()}>
        <input placeholder="Hujjat haqida savol bering..." autoComplete="off" />
        <button type="submit" aria-label="Yuborish"><Icon name="send" /></button>
      </form>
    </div>
  );
}

/** Совместимость: оба блока вместе. */
export function DocumentAssistant({ documentId }: { documentId: string }) {
  return <AssistantSummary documentId={documentId} />;
}
