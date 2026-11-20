"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { useStream } from "@/lib/stream";

// Пока /stream не готов, ленту держим свежей опросом; SSE ускорит до секунд (NFR-D-01: ≤ 30 с).
const POLL_MS = 10_000;

async function unwrap<T>(p: Promise<{ data?: T; error?: unknown }>): Promise<T> {
  const { data, error } = await p;
  if (error !== undefined || data === undefined) throw error ?? new Error("empty response");
  return data;
}

export function useDocumentsLive() {
  const qc = useQueryClient();
  useStream(["document.created", "document.changed", "document.status_changed", "document.disappeared"], () => {
    qc.invalidateQueries({ queryKey: ["documents"] });
    qc.invalidateQueries({ queryKey: ["document"] });
  });
}

export function useFeed(params: { kind?: string; status?: string; q?: string }) {
  return useQuery({
    queryKey: ["documents", params],
    queryFn: () => unwrap(api.GET("/documents", { params: { query: params as never } })),
    refetchInterval: POLL_MS,
  });
}

export function useDocument(id: string) {
  return useQuery({
    queryKey: ["document", id],
    queryFn: () => unwrap(api.GET("/documents/{document_id}", { params: { path: { document_id: id } } })),
    refetchInterval: POLL_MS,
  });
}

export function useVersions(id: string) {
  return useQuery({
    queryKey: ["document", id, "versions"],
    queryFn: () => unwrap(api.GET("/documents/{document_id}/versions", { params: { path: { document_id: id } } })),
    refetchInterval: POLL_MS,
  });
}

export function useDiff(id: string, versionNo: number, enabled: boolean) {
  return useQuery({
    queryKey: ["document", id, "diff", versionNo],
    enabled,
    queryFn: () => unwrap(api.GET("/documents/{document_id}/versions/{version_no}/diff",
      { params: { path: { document_id: id, version_no: versionNo } } })),
  });
}

export function useSources() {
  return useQuery({ queryKey: ["sources"], queryFn: () => unwrap(api.GET("/sources")), refetchInterval: 5_000 });
}
