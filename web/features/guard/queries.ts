"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type Schemas } from "@/lib/api/client";
import { useStream } from "@/lib/stream";

// Данные контекста «Сторож» для фронтенда. Пока /stream не готов, держим свежесть опросом;
// SSE (alert.created, action.updated) ускоряет до секунд (NFR-G-01, FR-G-14).
const POLL_MS = 8_000;

async function unwrap<T>(p: Promise<{ data?: T; error?: unknown }>): Promise<T> {
  const { data, error } = await p;
  if (error !== undefined || data === undefined) throw error ?? new Error("empty response");
  return data;
}

/** Тревоги живыми держит событие alert.created (FR-G-01, NFR-G-01). */
export function useAlertsLive() {
  const qc = useQueryClient();
  useStream(["alert.created"], () => {
    qc.invalidateQueries({ queryKey: ["alerts"] });
    qc.invalidateQueries({ queryKey: ["document-alerts"] });
  });
}

export function useAlerts(status?: Schemas["AlertStatus"]) {
  return useQuery({
    queryKey: ["alerts", status ?? "all"],
    queryFn: () => unwrap(api.GET("/guard/alerts", { params: { query: status ? { status } : {} } })),
    refetchInterval: POLL_MS,
  });
}

export function useDocumentAlerts(documentId: string) {
  return useQuery({
    queryKey: ["document-alerts", documentId],
    queryFn: () => unwrap(api.GET("/guard/documents/{document_id}/alerts", { params: { path: { document_id: documentId } } })),
    refetchInterval: POLL_MS,
  });
}

export function useSetVerdict() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { alertId: string; verdict: "me" | "not_me" }) =>
      unwrap(api.POST("/guard/alerts/{alert_id}/verdict", { params: { path: { alert_id: v.alertId } }, body: { verdict: v.verdict } })),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alerts"] });
      qc.invalidateQueries({ queryKey: ["document-alerts"] });
    },
  });
}

/** Действие с живыми шагами по action.updated (FR-G-07, FR-G-14). */
export function useActionLive(id: string) {
  const qc = useQueryClient();
  useStream(["action.updated"], (e) => {
    const data = e.data as { action_id?: string } | undefined;
    if (!data?.action_id || data.action_id === id) qc.invalidateQueries({ queryKey: ["action", id] });
  });
}

export function useAction(id: string, enabled = true) {
  return useQuery({
    queryKey: ["action", id],
    enabled,
    queryFn: () => unwrap(api.GET("/guard/actions/{action_id}", { params: { path: { action_id: id } } })),
    // Пока статус не финальный — часто обновляем на случай, если SSE недоступен.
    refetchInterval: (q) => {
      const s = (q.state.data as Schemas["Action"] | undefined)?.status;
      return s && ["done", "failed", "expired"].includes(s) ? false : 3_000;
    },
  });
}

/** Шаг 1: запросить действие. Idempotency-Key обязателен — повтор возвращает то же действие (FR-G-09). */
export function createAction(documentId: string, type: Schemas["ActionType"], idempotencyKey: string) {
  return unwrap(
    api.POST("/guard/actions", {
      params: { header: { "Idempotency-Key": idempotencyKey } },
      body: { document_id: documentId, type },
    }),
  );
}

/** Шаг 2: подтвердить кодом. 429 после 3 попыток (FR-G-08). Возвращаем статус ответа для разбора. */
export async function confirmAction(actionId: string, code: string): Promise<{ action?: Schemas["Action"]; status: number }> {
  const { data, error, response } = await api.POST("/guard/actions/{action_id}/confirm", {
    params: { path: { action_id: actionId } },
    body: { code },
  });
  if (error !== undefined || data === undefined) return { status: response.status };
  return { action: data, status: response.status };
}

/** Черновик заявления (ст. 31 / иск) через assistant.draft_application (FR-G-12). */
export function createDraft(documentId: string, type: Schemas["DraftType"]) {
  return unwrap(api.POST("/guard/drafts", { body: { document_id: documentId, type } }));
}

// ---- Семья и согласия (UC-G7, FR-G-13) ----
export function useFamily() {
  return useQuery({ queryKey: ["family"], queryFn: () => unwrap(api.GET("/guard/family")), refetchInterval: 10_000 });
}

export function useInvite() {
  return useMutation({
    mutationFn: (scopes: Schemas["ConsentScope"][]) => unwrap(api.POST("/guard/consents/invite", { body: { scopes } })),
  });
}

export function useAcceptInvite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (code: string) => unwrap(api.POST("/guard/consents/accept", { body: { code } })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["family"] }),
  });
}

export function useRevokeConsent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (consentId: string) =>
      api.DELETE("/guard/consents/{consent_id}", { params: { path: { consent_id: consentId } } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["family"] }),
  });
}

export function useTelegramLink() {
  return useMutation({ mutationFn: () => unwrap(api.POST("/guard/telegram/link")) });
}
