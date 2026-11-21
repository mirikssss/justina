"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge, Card, EmptyState, Icon, Skeleton } from "@/components/mygov";
import { AssistantChat, AssistantSummary } from "@/features/assistant";
import { DocumentGuard } from "@/features/guard";

import { useI18n } from "@/lib/i18n";

import { KIND, STATUS, fmtDate, fmtDateTime, useLabels } from "./labels";
import { useDiff, useDocument, useDocumentsLive, useVersions } from "./queries";

// FR-D-15: реквизиты, стороны, объект, статус, история версий.
// Слоты чужих контекстов: <AssistantSummary/>, <AssistantChat/> (Разработчик 2) и <DocumentGuard/> (Разработчик 3).
export function DocumentPage({ id }: { id: string }) {
  const { t } = useI18n();
  const L = useLabels();
  useDocumentsLive();
  const doc = useDocument(id);

  if (doc.isLoading) return <Skeleton rows={4} />;
  if (doc.isError || !doc.data) return <EmptyState title={t("doc.notfound")} hint={t("doc.notfound.hint")} />;
  const d = doc.data;
  const k = KIND[d.kind];
  const st = STATUS[d.status];
  const others = (d.parties ?? []).filter((p) => p.role !== d.owner_role);
  const number = (d.fields as Record<string, unknown> | undefined)?.number_masked as string | undefined;

  return (
    <>
      <Link href="/documents" className="back"><Icon name="back" /> {t("app.name")}</Link>
      <div className="detail">
        <div className="dcol">
          <div className="dhead">
            <div className="row">
              <div className="bigic"><Icon name={k.icon} /></div>
              <div style={{ minWidth: 0 }}>
                <h1>{d.title}</h1>
                <div className="sub">{L.source(d.source)}{number ? ` • № ${number}` : ""}</div>
                <div style={{ marginTop: 9, display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <Badge tone={st.tone}>{L.status(d.status)}</Badge>
                  <span className="vcount"><Icon name="layers" size={14} /> {t("doc.versions", { n: d.versions_count })}</span>
                </div>
              </div>
            </div>
            <div className="kv">
              <div><span>{t("doc.kind")}</span><b>{L.kind(d.kind)}</b></div>
              <div><span>{t("doc.your_role")}</span><b>{L.role(d.owner_role, true)}</b></div>
              {others.map((p) => (
                <div key={p.role}><span>{L.role(p.role)}</span><b>{p.name_masked}</b></div>
              ))}
              {d.object ? (
                <div><span>{t("doc.object")}</span><b>{[d.object.label, d.object.id_masked].filter(Boolean).join(" · ")}</b></div>
              ) : null}
              <div><span>{t("doc.issued")}</span><b>{fmtDate(d.issued_at)}</b></div>
              <div><span>{t("doc.valid_until")}</span><b>{fmtDate(d.valid_until)}</b></div>
              <div><span>{t("doc.issuer")}</span><b>{d.issuer?.name ?? "—"}</b></div>
              <div><span>{t("doc.first_seen")}</span><b>{fmtDateTime(d.first_seen_at)}</b></div>
            </div>
          </div>

          <AssistantSummary documentId={id} />
          <Versions id={id} />
          <DocumentGuard documentId={id} status={d.status} />
        </div>
        <AssistantChat documentId={id} />
      </div>
    </>
  );
}

function Versions({ id }: { id: string }) {
  const { t } = useI18n();
  const L = useLabels();
  const versions = useVersions(id);
  const [open, setOpen] = useState<number | null>(null);
  const rows = versions.data ?? [];
  return (
    <Card title={t("ver.title")} icon="layers">
      {versions.isLoading ? <Skeleton rows={2} /> : null}
      <div className="tl">
        {rows.map((v, i) => (
          <div key={v.version_no} className={`ev${i === 0 ? " cur" : ""}${v.changed_fields.includes("status") ? " alert" : ""}`}>
            <span className="dot" />
            <div className="ec">
              <b>{v.version_no === 1 ? t("ver.appeared") : t("ver.n", { n: v.version_no })}</b>
              <span className="dt">{fmtDateTime(v.fetched_at)}</span>
              {v.version_no > 1 ? (
                <p>
                  {t("ver.changed")} {v.changed_fields.map((f) => L.field(f)).join(", ") || "—"}{" "}
                  <button type="button" className="back" style={{ padding: 0, margin: 0, display: "inline" }}
                    onClick={() => setOpen(open === v.version_no ? null : v.version_no)}>
                    {open === v.version_no ? t("ver.hide") : t("ver.what")}
                  </button>
                </p>
              ) : <p>{t("ver.first")}</p>}
              {open === v.version_no ? <Diff id={id} versionNo={v.version_no} /> : null}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function Diff({ id, versionNo }: { id: string; versionNo: number }) {
  const L = useLabels();
  const diff = useDiff(id, versionNo, true);
  return (
    <div className="diff">
      {(diff.data ?? []).map((e) => (
        <div key={e.field}>
          <code>{L.field(e.field)}</code> <s>{show(e.from, L.status)}</s> → <ins>{show(e.to, L.status)}</ins>
        </div>
      ))}
    </div>
  );
}

function show(v: unknown, status: (s: string) => string): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "string") return v in STATUS ? status(v) : v;
  return JSON.stringify(v);
}
