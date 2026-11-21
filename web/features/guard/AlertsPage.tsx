"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge, Button, Chips, EmptyState, Icon, PageHeader, Skeleton, toast } from "@/components/mygov";
import type { Schemas } from "@/lib/api/client";

import { ALERT_STATUS, RULE, SEVERITY, fmtAgo } from "./labels";
import { useAlerts, useAlertsLive, useSetVerdict } from "./queries";

// FR-G-14: список тревог по важности, кнопки «Это я» / «Это не я». Живёт на alert.created (NFR-G-01).
type Filter = "all" | Schemas["AlertStatus"];
const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "Barchasi" },
  { value: "new", label: "Yangi" },
  { value: "seen", label: "Ko'rilgan" },
  { value: "closed", label: "Yopilgan" },
];

export function AlertsPage() {
  useAlertsLive();
  const [filter, setFilter] = useState<Filter>("all");
  const alerts = useAlerts(filter === "all" ? undefined : filter);
  const rows = alerts.data?.items ?? [];

  return (
    <>
      <PageHeader title="Ogohlantirishlar" subtitle="Hujjatlaringizdagi o'zgarishlar — eng muhimidan boshlab" />
      <Chips value={filter} options={FILTERS} onChange={setFilter} />
      {alerts.isLoading ? (
        <Skeleton rows={3} />
      ) : rows.length === 0 ? (
        <EmptyState title="Ogohlantirishlar yo'q" hint="Yangi hodisa paydo bo'lsa, shu yerda ko'rinadi" />
      ) : (
        <div className="doclist">
          {rows.map((a) => <AlertRow key={a.id} alert={a} />)}
        </div>
      )}
    </>
  );
}

function AlertRow({ alert }: { alert: Schemas["Alert"] }) {
  const sev = SEVERITY[alert.severity];
  const verdict = useSetVerdict();
  const closed = alert.status === "closed" || alert.verdict !== null;

  const vote = (v: "me" | "not_me", after?: () => void) =>
    verdict.mutate(
      { alertId: alert.id, verdict: v },
      {
        onSuccess: () => {
          toast(v === "me" ? "Belgilandi: bu men" : "Belgilandi: bu men emasman", v === "me" ? "good" : "info");
          after?.();
        },
        onError: () => toast("Saqlanmadi, qaytadan urinib ko'ring", "crit"),
      },
    );

  return (
    <article className={`alert sev-${alert.severity}`}>
      <div className={`dic b-${sev.tone}`}><Icon name={sev.icon} /></div>
      <div className="dmain">
        <div className="dtitle">
          {alert.title}
          {alert.status === "new" ? <Badge tone="new">Yangi</Badge> : null}
        </div>
        <div className="dmeta">
          <Badge tone={sev.tone}>{sev.label}</Badge>
          <span>{RULE[alert.rule_id] ?? alert.rule_id}</span>
          <span>{fmtAgo(alert.created_at)}</span>
          {closed ? <span>· {ALERT_STATUS[alert.status]}</span> : null}
        </div>
        {alert.explanation ? <p className="note" style={{ marginTop: 8 }}>{alert.explanation}</p> : null}
        <AlertButtons alert={alert} closed={closed} busy={verdict.isPending} vote={vote} />
      </div>
    </article>
  );
}

function AlertButtons({ alert, closed, busy, vote }:
  { alert: Schemas["Alert"]; closed: boolean; busy: boolean; vote: (v: "me" | "not_me", after?: () => void) => void }) {
  const docHref = alert.document_id ? `/documents/${alert.document_id}` : undefined;
  if (closed) {
    return (
      <div className="alert-acts">
        <Badge tone={alert.verdict === "me" ? "good" : "info"}>
          {alert.verdict === "me" ? "Bu men edi" : alert.verdict === "not_me" ? "Bu men emas edim" : "Yopilgan"}
        </Badge>
        {docHref ? <Link className="link" href={docHref}>Hujjatni ochish <Icon name="chev" size={16} /></Link> : null}
      </div>
    );
  }
  const btns = alert.buttons ?? [];
  const hasNotMe = btns.some((b) => b.startsWith("not_me"));
  const hasOpenOnly = !hasNotMe && !btns.includes("me");
  return (
    <div className="alert-acts">
      {hasNotMe ? (
        // «Это не я» → фиксируем вердикт и ведём на карточку документа, где <DocumentGuard/> даёт отзыв/заявление (UC-G3).
        <Button
          variant="primary"
          disabled={busy}
          onClick={() => vote("not_me", () => docHref && (location.href = docHref))}
        >
          <Icon name="x" size={16} /> Bu men emasman
        </Button>
      ) : null}
      {btns.includes("me") ? (
        <Button variant="ghost" disabled={busy} onClick={() => vote("me")}>
          <Icon name="check2" size={16} /> Bu men
        </Button>
      ) : null}
      {btns.includes("reconnect") ? (
        <Link className="link" href="/sources">Manbani qayta ulash <Icon name="chev" size={16} /></Link>
      ) : hasOpenOnly && docHref ? (
        <Link className="link" href={docHref}>Ochish <Icon name="chev" size={16} /></Link>
      ) : null}
    </div>
  );
}
