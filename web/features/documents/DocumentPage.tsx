"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge, Card, EmptyState, Icon, Skeleton } from "@/components/mygov";
import { AssistantChat, AssistantSummary } from "@/features/assistant";
import { DocumentGuard } from "@/features/guard";

import { FIELD, KIND, ROLE, SOURCE, STATUS, fmtDate, fmtDateTime } from "./labels";
import { useDiff, useDocument, useDocumentsLive, useVersions } from "./queries";

// FR-D-15: реквизиты, стороны, объект, статус, история версий.
// Слоты чужих контекстов: <AssistantSummary/>, <AssistantChat/> (Разработчик 2) и <DocumentGuard/> (Разработчик 3).
export function DocumentPage({ id }: { id: string }) {
  useDocumentsLive();
  const doc = useDocument(id);

  if (doc.isLoading) return <Skeleton rows={4} />;
  if (doc.isError || !doc.data) return <EmptyState title="Hujjat topilmadi" hint="Ro'yxatga qayting" />;
  const d = doc.data;
  const k = KIND[d.kind];
  const st = STATUS[d.status];
  const others = (d.parties ?? []).filter((p) => p.role !== d.owner_role);
  const number = (d.fields as Record<string, unknown> | undefined)?.number_masked as string | undefined;

  return (
    <>
      <Link href="/documents" className="back"><Icon name="back" /> Mening hujjatlarim</Link>
      <div className="detail">
        <div className="dcol">
          <div className="dhead">
            <div className="row">
              <div className="bigic"><Icon name={k.icon} /></div>
              <div style={{ minWidth: 0 }}>
                <h1>{d.title}</h1>
                <div className="sub">{SOURCE[d.source]?.label ?? d.source}{number ? ` • № ${number}` : ""}</div>
                <div style={{ marginTop: 9, display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <Badge tone={st.tone}>{st.label}</Badge>
                  <span className="vcount"><Icon name="layers" size={14} /> {d.versions_count} versiya</span>
                </div>
              </div>
            </div>
            <div className="kv">
              <div><span>Turi</span><b>{k.label}</b></div>
              <div><span>Sizning rolingiz</span><b>{ROLE[d.owner_role] ?? d.owner_role}</b></div>
              {others.map((p) => (
                <div key={p.role}><span>{ROLE[p.role]?.replace(" (siz)", "") ?? p.role}</span><b>{p.name_masked}</b></div>
              ))}
              {d.object ? (
                <div><span>Obyekt</span><b>{[d.object.label, d.object.id_masked].filter(Boolean).join(" · ")}</b></div>
              ) : null}
              <div><span>Berilgan sana</span><b>{fmtDate(d.issued_at)}</b></div>
              <div><span>Amal qilish muddati</span><b>{fmtDate(d.valid_until)}</b></div>
              <div><span>Kim tomonidan</span><b>{d.issuer?.name ?? "—"}</b></div>
              <div><span>Birinchi marta ko'rildi</span><b>{fmtDateTime(d.first_seen_at)}</b></div>
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
  const versions = useVersions(id);
  const [open, setOpen] = useState<number | null>(null);
  const rows = versions.data ?? [];
  return (
    <Card title="Versiyalar tarixi" icon="layers">
      {versions.isLoading ? <Skeleton rows={2} /> : null}
      <div className="tl">
        {rows.map((v, i) => (
          <div key={v.version_no} className={`ev${i === 0 ? " cur" : ""}${v.changed_fields.includes("status") ? " alert" : ""}`}>
            <span className="dot" />
            <div className="ec">
              <b>{v.version_no === 1 ? "Hujjat paydo bo'ldi" : `${v.version_no}-versiya`}</b>
              <span className="dt">{fmtDateTime(v.fetched_at)}</span>
              {v.version_no > 1 ? (
                <p>
                  O'zgardi: {v.changed_fields.map((f) => FIELD[f] ?? f).join(", ") || "—"}{" "}
                  <button type="button" className="back" style={{ padding: 0, margin: 0, display: "inline" }}
                    onClick={() => setOpen(open === v.version_no ? null : v.version_no)}>
                    {open === v.version_no ? "yashirish" : "nima o'zgardi?"}
                  </button>
                </p>
              ) : <p>Manbada birinchi marta topildi</p>}
              {open === v.version_no ? <Diff id={id} versionNo={v.version_no} /> : null}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function Diff({ id, versionNo }: { id: string; versionNo: number }) {
  const diff = useDiff(id, versionNo, true);
  return (
    <div className="diff">
      {(diff.data ?? []).map((e) => (
        <div key={e.field}>
          <code>{FIELD[e.field] ?? e.field}</code> <s>{show(e.from)}</s> → <ins>{show(e.to)}</ins>
        </div>
      ))}
    </div>
  );
}

function show(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "string") return STATUS[v as keyof typeof STATUS]?.label ?? v;
  return JSON.stringify(v);
}
