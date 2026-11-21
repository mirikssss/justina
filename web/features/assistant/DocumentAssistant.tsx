"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { Card, Icon, Skeleton } from "@/components/mygov";
import { API_BASE, api, type Schemas } from "@/lib/api/client";
import { useI18n } from "@/lib/i18n";
import { useStream } from "@/lib/stream";

type Lang = Schemas["Lang"];
type Summary = Schemas["Summary"];
type Citation = Schemas["Citation"];
type ChatMessage = Schemas["ChatMessage"];

// FR-A-11. Резюме: GET /assist/documents/{id}/summary — 200 или 202 (считается, придёт summary.ready в /stream).
// Чат: POST /assist/chat отвечает потоком SSE (token, citations, done); история — GET /assist/chat/{id}.

const SUMMARY_POLL_MS = 5_000; // запасной опрос, пока резюме считается (основной сигнал — summary.ready)

async function fetchSummary(id: string, lang: Lang): Promise<Summary | null> {
  const r = await fetch(`${API_BASE}/assist/documents/${id}/summary?lang=${lang}`, { credentials: "include" });
  if (r.status === 202) return null;
  if (!r.ok) throw new Error(`summary ${r.status}`);
  return (await r.json()) as Summary;
}

function Citations({ items, numbered = false }: { items: Citation[]; numbered?: boolean }) {
  if (!items.length) return null;
  return (
    <div className="cite">
      {items.map((c, i) => (
        <div key={`${c.url}-${i}`}>
          <a href={c.url} target="_blank" rel="noopener noreferrer">
            {numbered ? `[${i + 1}] ` : ""}
            {c.act_title}, {c.article}
          </a>
        </div>
      ))}
    </div>
  );
}

export function AssistantSummary({ documentId }: { documentId: string }) {
  const { lang, t } = useI18n(); // резюме — на языке интерфейса (по умолчанию узбекский)
  const qc = useQueryClient();
  const key = ["summary", documentId, lang];
  const summary = useQuery({
    queryKey: key,
    queryFn: () => fetchSummary(documentId, lang),
    refetchInterval: (q) => (q.state.data === null ? SUMMARY_POLL_MS : false),
  });
  useStream(["summary.ready"], (e) => {
    if (e.data.document_id === documentId) qc.invalidateQueries({ queryKey: ["summary", documentId] });
  });
  const s = summary.data;

  return (
    <Card title={t("ai.summary")} icon="bolt" tag="AI • lex.uz RAG">
      <div className="ai-sum" data-document-id={documentId}>
        {summary.isError ? <p>{t("ai.error")}</p> : null}
        {summary.isLoading || s === null ? (
          <>
            <p>{t("ai.pending")}</p>
            <Skeleton rows={2} />
          </>
        ) : null}
        {s ? (
          <>
            <p><b>{s.what_is_it}</b></p>
            <Section title={t("ai.can")} items={s.counterparty_can} />
            <Section title={t("ai.risks")} items={s.risks} />
            <Section title={t("ai.todo")} items={s.what_to_do} />
            <Citations items={s.citations} />
          </>
        ) : null}
      </div>
    </Card>
  );
}

function Section({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <>
      <p style={{ marginBottom: 4 }}><b>{title}</b></p>
      <ul style={{ margin: "0 0 10px 18px" }}>
        {items.map((x, i) => <li key={i}>{x}</li>)}
      </ul>
    </>
  );
}

/** Разбор text/event-stream из fetch: вызывает onEvent(event, data) на каждое сообщение. */
async function readSse(body: ReadableStream<Uint8Array>, onEvent: (event: string, data: string) => void) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
    let sep: number;
    while ((sep = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, sep);
      buf = buf.slice(sep + 2);
      let event = "message";
      const data: string[] = [];
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
      }
      if (data.length) onEvent(event, data.join("\n"));
    }
  }
}

type Live = { question: string; answer: string; citations: Citation[] } | null;

export function AssistantChat({ documentId }: { documentId: string }) {
  const { t } = useI18n(); // интерфейс чата — на языке сайта; ответ модели — на языке вопроса
  const qc = useQueryClient();
  const history = useQuery({
    queryKey: ["chat", documentId],
    queryFn: async () => {
      const { data, error } = await api.GET("/assist/chat/{document_id}", { params: { path: { document_id: documentId } } });
      if (error !== undefined) throw error;
      return (data ?? []) as ChatMessage[];
    },
  });
  const [input, setInput] = useState("");
  const [live, setLive] = useState<Live>(null);
  const [busy, setBusy] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight });
  }, [history.data, live]);

  async function send(e: FormEvent) {
    e.preventDefault();
    const message = input.trim();
    if (!message || busy) return;
    setInput("");
    setBusy(true);
    setLive({ question: message, answer: "", citations: [] });
    try {
      const r = await fetch(`${API_BASE}/assist/chat`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify({ document_id: documentId, message }),
      });
      if (!r.ok || !r.body) throw new Error(`chat ${r.status}`);
      await readSse(r.body, (event, data) => {
        if (event === "token") setLive((l) => (l ? { ...l, answer: l.answer + data } : l));
        else if (event === "citations") setLive((l) => (l ? { ...l, citations: JSON.parse(data) as Citation[] } : l));
      });
      await qc.invalidateQueries({ queryKey: ["chat", documentId] });
      setLive(null);
    } catch {
      setLive((l) => (l ? { ...l, answer: l.answer || t("chat.error") } : l));
    } finally {
      setBusy(false);
    }
  }

  const messages = history.data ?? [];
  return (
    <div className="chat" data-document-id={documentId}>
      <div className="chat-h">
        <div className="ca"><Icon name="bolt" /></div>
        <div><h3>{t("chat.title")}</h3><small>{t("chat.sub")}</small></div>
        <span className="lv"><Icon name="shield" size={12} /> lex.uz</span>
      </div>
      <div className="chat-body" ref={bodyRef}>
        <div className="msg bot">{t("chat.hello")}</div>
        {messages.map((m) => (
          <div key={m.id} className={`msg ${m.role === "user" ? "me" : "bot"}`}>
            {m.text}
            {m.role === "assistant" ? <Citations items={m.citations} numbered /> : null}
          </div>
        ))}
        {live ? (
          <>
            <div className="msg me">{live.question}</div>
            <div className="msg bot">
              {live.answer || "…"}
              <Citations items={live.citations} numbered />
            </div>
          </>
        ) : null}
      </div>
      <form className="chat-in" onSubmit={send}>
        <input placeholder={t("chat.placeholder")} autoComplete="off" maxLength={2000} value={input}
               onChange={(e) => setInput(e.target.value)} disabled={busy} />
        <button type="submit" aria-label={t("chat.send")} disabled={busy}><Icon name="send" /></button>
      </form>
    </div>
  );
}

/** Совместимость: оба блока вместе. */
export function DocumentAssistant({ documentId }: { documentId: string }) {
  return <AssistantSummary documentId={documentId} />;
}
