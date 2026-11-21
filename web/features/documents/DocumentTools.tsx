"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Badge, Button, Card } from "@/components/mygov";
import { api, type Schemas } from "@/lib/api/client";
import { useT } from "@/lib/i18n";

import { fmtDateTime } from "./labels";

type Share = Schemas["ShareLink"];

// «Поделиться» замаскированным документом на 24 часа (с журналом просмотров) и доказательный пакет PDF.
export function DocumentTools({ id }: { id: string }) {
  const t = useT();
  const qc = useQueryClient();
  const [fresh, setFresh] = useState<Share | null>(null);
  const [copied, setCopied] = useState(false);
  const shares = useQuery({
    queryKey: ["shares", id],
    queryFn: async () => {
      const { data, error } = await api.GET("/documents/{document_id}/shares", { params: { path: { document_id: id } } });
      if (error !== undefined || !data) throw new Error("shares");
      return data;
    },
  });
  const create = useMutation({
    mutationFn: async (): Promise<Share> => {
      const { data, error } = await api.POST("/documents/{document_id}/share", { params: { path: { document_id: id } } });
      if (error !== undefined || !data) throw new Error("share");
      return data;
    },
    onSuccess: (d) => { setFresh(d); setCopied(false); qc.invalidateQueries({ queryKey: ["shares", id] }); },
  });
  const revoke = useMutation({
    mutationFn: async (shareId: string) => { await api.DELETE("/shares/{share_id}", { params: { path: { share_id: shareId } } }); },
    onSuccess: () => { setFresh(null); qc.invalidateQueries({ queryKey: ["shares", id] }); },
  });

  return (
    <Card title={t("Hujjat bilan ishlash")} icon="send">
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <Button small onClick={() => create.mutate()} disabled={create.isPending}>{t("Ulashish (24 soat)")}</Button>
        <a className="btn btn-ghost btn-sm" href={`/api/documents/${id}/evidence.pdf`} download>{t("Dalil paketi (PDF)")}</a>
      </div>
      {fresh ? (
        <div style={{ marginTop: 12 }}>
          <input readOnly value={fresh.url} onFocus={(e) => e.currentTarget.select()}
            style={{ width: "100%", background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 10, padding: "10px 12px", color: "var(--fg)", fontSize: 13 }} />
          <div style={{ marginTop: 8, display: "flex", gap: 10, alignItems: "center" }}>
            <Button small variant="ghost" onClick={() => { navigator.clipboard?.writeText(fresh.url); setCopied(true); }}>{copied ? t("Nusxalandi") : t("Nusxalash")}</Button>
            <small style={{ color: "var(--muted)" }}>{t("Havola maskalangan hujjatni ko'rsatadi, kirish talab qilinmaydi")}</small>
          </div>
        </div>
      ) : null}
      {(shares.data ?? []).length > 0 ? (
        <div style={{ marginTop: 14, display: "grid", gap: 8, fontSize: 13 }}>
          <b>{t("Ko'rishlar jurnali")}</b>
          {(shares.data ?? []).map((s) => (
            <div key={s.share_id} style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
              <span>{fmtDateTime(s.created_at)} · {s.views} {t("ko'rish")}{s.last_view_at ? ` · ${fmtDateTime(s.last_view_at)}` : ""}</span>
              {s.active
                ? <Button small variant="ghost" onClick={() => revoke.mutate(s.share_id)}>{t("Bekor qilish")}</Button>
                : <Badge tone="info">{t("Tugagan")}</Badge>}
            </div>
          ))}
        </div>
      ) : null}
      {create.isError ? <p style={{ color: "var(--crit)", fontSize: 13 }}>{t("Xato")}</p> : null}
    </Card>
  );
}
