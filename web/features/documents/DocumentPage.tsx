"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge, Card, EmptyState, Icon, Skeleton } from "@/components/mygov";
import { AssistantChat, AssistantSummary } from "@/features/assistant";
import { DocumentGuard } from "@/features/guard";
import { useT } from "@/lib/i18n";

import { FIELD, KIND, ROLE, SOURCE, STATUS, fmtDate, fmtDateTime } from "./labels";
import { useDiff, useDocument, useDocumentsLive, useVersions } from "./queries";

// FR-D-15: реквизиты, стороны, объект, статус, история версий.
// Слоты чужих контекстов: <AssistantSummary/>, <AssistantChat/> (Разработчик 2) и <DocumentGuard/> (Разработчик 3).
export function DocumentPage({ id }: { id: string }) {
  const t = useT();
  useDocumentsLive();
  const doc = useDocument(id);

  if (doc.isLoading) return <Skeleton rows={4} />;
  if (doc.isError || !doc.data) return <EmptyState title={t("Hujjat topilmadi")} hint={t("Ro'yxatga qayting")} />;
  const d = doc.data;
  const k = KIND[d.kind];
  const st = STATUS[d.status];
  const others = (d.parties ?? []).filter((p) => p.role !== d.owner_role);
  const number = (d.fields as Record<string, unknown> | undefined)?.number_masked as string | undefined;

  return (
    <>
      <Link href="/documents" className="back"><Icon name="back" /> {t("Mening hujjatlarim")}</Link>
      <div className="detail">
        <div className="dcol">
          <div className="dhead">
            <div className="row">
              <div className="bigic"><Icon name={k.icon} /></div>
              <div style={{ minWidth: 0 }}>
                <h1>{d.title}</h1>
                <div className="sub">{SOURCE[d.source] ? t(SOURCE[d.source].label) : d.source}{number ? ` • № ${number}` : ""}</div>
                <div style={{ marginTop: 9, display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <Badge tone={st.tone}>{t(st.label)}</Badge>
                  <span className="vcount"><Icon name="layers" size={14} /> {t("{n} versiya", { n: d.versions_count })}</span>
                </div>
              </div>
            </div>
            <div className="kv">
              <div><span>{t("Turi")}</span><b>{t(k.label)}</b></div>
              <div><span>{t("Sizning rolingiz")}</span><b>{ROLE[d.owner_role] ? t(ROLE[d.owner_role]) : d.owner_role}</b></div>
              {others.map((p) => (
                <div key={p.role}><span>{ROLE[p.role] ? t(ROLE[p.role]) : p.role}</span><b>{p.name_masked}</b></div>
              ))}
              {d.object ? (
                <div><span>{t("Obyekt")}</span><b>{[d.object.label, d.object.id_masked].filter(Boolean).join(" · ")}</b></div>
              ) : null}
              <div><span>{t("Berilgan sana")}</span><b>{fmtDate(d.issued_at)}</b></div>
              <div><span>{t("Amal qilish muddati")}</span><b>{fmtDate(d.valid_until)}</b></div>
              <div><span>{t("Kim tomonidan")}</span><b>{d.issuer?.name ?? "—"}</b></div>
              <div><span>{t("Birinchi marta ko'rildi")}</span><b>{fmtDateTime(d.first_seen_at)}</b></div>
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
  const t = useT();
  const versions = useVersions(id);
  const [open, setOpen] = useState<number | null>(null);
  const rows = versions.data ?? [];
  return (
    <Card title={t("Versiyalar tarixi")} icon="layers">
      {versions.isLoading ? <Skeleton rows={2} /> : null}
      <div className="tl">
        {rows.map((v, i) => (
          <div key={v.version_no} className={`ev${i === 0 ? " cur" : ""}${v.changed_fields.includes("status") ? " alert" : ""}`}>
            <span className="dot" />
            <div className="ec">
              <b>{v.version_no === 1 ? t("Hujjat paydo bo'ldi") : t("{n}-versiya", { n: v.version_no })}</b>
              <span className="dt">{fmtDateTime(v.fetched_at)}</span>
              {v.version_no > 1 ? (
                <p>
                  {t("O'zgardi:")} {v.changed_fields.map((f) => (FIELD[f] ? t(FIELD[f]) : f)).join(", ") || "—"}{" "}
                  <button type="button" className="back" style={{ padding: 0, margin: 0, display: "inline" }}
                    onClick={() => setOpen(open === v.version_no ? null : v.version_no)}>
                    {open === v.version_no ? t("yashirish") : t("nima o'zgardi?")}
                  </button>
                </p>
              ) : <p>{t("Manbada birinchi marta topildi")}</p>}
              {open === v.version_no ? <Diff id={id} versionNo={v.version_no} /> : null}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function Diff({ id, versionNo }: { id: string; versionNo: number }) {
  const t = useT();
  const diff = useDiff(id, versionNo, true);
  return (
    <div className="diff">
      {(diff.data ?? []).map((e) => (
        <div key={e.field}>
          <code>{FIELD[e.field] ? t(FIELD[e.field]) : e.field}</code> <s>{t(show(e.from))}</s> → <ins>{t(show(e.to))}</ins>
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
