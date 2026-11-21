"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge, Button, Chips, EmptyState, Icon, PageHeader, Skeleton, toast } from "@/components/mygov";
import type { Schemas } from "@/lib/api/client";
import { useLocale, useT } from "@/lib/i18n";

import { ALERT_STATUS, RULE, SEVERITY, fmtAgo, secondsBetween } from "./labels";
import { useAlerts, useAlertsLive, useSetVerdict, useTelegramLink } from "./queries";

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
  const t = useT();
  const [filter, setFilter] = useState<Filter>("all");
  const alerts = useAlerts(filter === "all" ? undefined : filter);
  const rows = alerts.data?.items ?? [];
  const filters = FILTERS.map((f) => ({ ...f, label: t(f.label) }));

  return (
    <>
      <PageHeader
        title={t("Ogohlantirishlar")}
        subtitle={t("Hujjatlaringizdagi o'zgarishlar — eng muhimidan boshlab")}
        actions={<TelegramLinkButton />}
      />
      <Chips value={filter} options={filters} onChange={setFilter} />
      {alerts.isLoading ? (
        <Skeleton rows={3} />
      ) : rows.length === 0 ? (
        <EmptyState title={t("Ogohlantirishlar yo'q")} hint={t("Yangi hodisa paydo bo'lsa, shu yerda ko'rinadi")} />
      ) : (
        <div className="doclist">
          {rows.map((a) => <AlertRow key={a.id} alert={a} />)}
        </div>
      )}
    </>
  );
}

// UC-G5: ссылка t.me/<bot>?start=link_<token> (10 минут) — после неё тревоги и коды приходят в Telegram.
function TelegramLinkButton() {
  const t = useT();
  const link = useTelegramLink();
  const open = () =>
    link.mutate(undefined, {
      onSuccess: (r) => {
        // окно после await часто режет блокировщик всплывающих окон — тогда открываем в этой вкладке
        // ("noopener" в window.open всегда даёт null, поэтому opener обнуляем сами)
        const w = window.open(r.deep_link, "_blank");
        if (w) w.opener = null;
        else window.location.href = r.deep_link;
        toast(t("Botda «Start»ni bosing — havola 10 daqiqa amal qiladi"), "info");
      },
      onError: () => toast(t("Havolani olib bo'lmadi. Qayta urinib ko'ring."), "crit"),
    });
  return (
    <Button variant="ghost" disabled={link.isPending} onClick={open}>
      <Icon name="send" size={16} /> {t("Telegramni ulash")}
    </Button>
  );
}

function AlertRow({ alert }: { alert: Schemas["Alert"] }) {
  const t = useT();
  const { locale } = useLocale();
  const sev = SEVERITY[alert.severity];
  const verdict = useSetVerdict();
  const closed = alert.status === "closed" || alert.verdict !== null;
  const latency = secondsBetween(alert.detected_at, alert.sent_at); // T11: доказательство «≤ 5 с» на экране

  const vote = (v: "me" | "not_me", after?: () => void) =>
    verdict.mutate(
      { alertId: alert.id, verdict: v },
      {
        onSuccess: () => {
          toast(v === "me" ? t("Belgilandi: bu men") : t("Belgilandi: bu men emasman"), v === "me" ? "good" : "info");
          after?.();
        },
        onError: () => toast(t("Saqlanmadi, qaytadan urinib ko'ring"), "crit"),
      },
    );

  return (
    <article className={`alert sev-${alert.severity}`}>
      <div className={`dic b-${sev.tone}`}><Icon name={sev.icon} /></div>
      <div className="dmain">
        <div className="dtitle">
          {alert.title}
          {alert.status === "new" ? <Badge tone="new">{t("Yangi")}</Badge> : null}
        </div>
        <div className="dmeta">
          <Badge tone={sev.tone}>{t(sev.label)}</Badge>
          <span>{RULE[alert.rule_id] ? t(RULE[alert.rule_id]) : alert.rule_id}</span>
          <span>{fmtAgo(alert.created_at, locale)}</span>
          {latency !== null ? <span title={t("Hodisadan Telegramgacha")}>· {t("Telegramga {n} s da", { n: latency })}</span> : null}
          {closed ? <span>· {t(ALERT_STATUS[alert.status])}</span> : null}
        </div>
        {alert.explanation ? <p className="note" style={{ marginTop: 8 }}>{alert.explanation}</p> : null}
        <AlertButtons alert={alert} closed={closed} busy={verdict.isPending} vote={vote} />
      </div>
    </article>
  );
}

function AlertButtons({ alert, closed, busy, vote }:
  { alert: Schemas["Alert"]; closed: boolean; busy: boolean; vote: (v: "me" | "not_me", after?: () => void) => void }) {
  const t = useT();
  const docHref = alert.document_id ? `/documents/${alert.document_id}` : undefined;
  if (closed) {
    return (
      <div className="alert-acts">
        <Badge tone={alert.verdict === "me" ? "good" : "info"}>
          {alert.verdict === "me" ? t("Bu men edi") : alert.verdict === "not_me" ? t("Bu men emas edim") : t("Yopilgan")}
        </Badge>
        {docHref ? <Link className="link" href={docHref}>{t("Hujjatni ochish")} <Icon name="chev" size={16} /></Link> : null}
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
          <Icon name="x" size={16} /> {t("Bu men emasman")}
        </Button>
      ) : null}
      {btns.includes("me") ? (
        <Button variant="ghost" disabled={busy} onClick={() => vote("me")}>
          <Icon name="check2" size={16} /> {t("Bu men")}
        </Button>
      ) : null}
      {btns.includes("reconnect") ? (
        <Link className="link" href="/sources">{t("Manbani qayta ulash")} <Icon name="chev" size={16} /></Link>
      ) : hasOpenOnly && docHref ? (
        <Link className="link" href={docHref}>{t("Ochish")} <Icon name="chev" size={16} /></Link>
      ) : null}
    </div>
  );
}
