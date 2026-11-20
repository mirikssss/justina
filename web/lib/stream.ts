"use client";

import { useEffect } from "react";

import { API_URL } from "./api/client";

export type StreamEventType =
  | "document.created"
  | "document.changed"
  | "document.status_changed"
  | "document.disappeared"
  | "alert.created"
  | "action.updated"
  | "summary.ready";

export type StreamEvent = { id: string; type: StreamEventType; subject: string; data: Record<string, unknown> };

/** Подписка на GET /stream (SSE). Обычно в обработчике — queryClient.invalidateQueries(...). */
export function useStream(types: StreamEventType[], onEvent: (e: StreamEvent) => void) {
  const key = types.join(",");
  useEffect(() => {
    const es = new EventSource(`${API_URL}/stream`, { withCredentials: true });
    const listener = (msg: MessageEvent) => onEvent(JSON.parse(msg.data) as StreamEvent);
    for (const t of types) es.addEventListener(t, listener);
    return () => es.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
}
