"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge, Chips, EmptyState, Icon, Skeleton } from "@/components/mygov";

import { useI18n } from "@/lib/i18n";

import { KIND, SOURCE, STATUS, fmtDate, useLabels } from "./labels";
import { useDocumentsLive, useFeed } from "./queries";

type KindFilter = "all" | keyof typeof KIND;

const TAB_KINDS: KindFilter[] = ["all", "poa_car", "poa_notarial", "notarial_act"];
const STATUS_FILTERS = ["", "active", "revoked", "expired", "completed"];

// FR-D-14: вкладки по типу, фильтр по статусу, поиск, метка «новое», живое обновление.
export function DocumentFeed() {
  const { t } = useI18n();
  const L = useLabels();
  const tabs = TAB_KINDS.map((value) => ({ value, label: t(`feed.tab.${value}` as "feed.tab.all") }));
  const statuses = STATUS_FILTERS.map((value) => ({ value, label: value ? L.status(value) : t("feed.status.any") }));
  const [kind, setKind] = useState<KindFilter>("all");
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  useDocumentsLive();
  const feed = useFeed({ kind: kind === "all" ? undefined : kind, status: status || undefined, q: q || undefined });
  const items = feed.data?.items ?? [];
  const fresh = items.filter((d) => d.is_new);

  return (
    <>
      <div className="hero">
        <h1>{t("app.name")}</h1>
        <p>{t("feed.lead")}</p>
        <label className="search">
          <Icon name="search" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("feed.search")} />
        </label>
        <div className="stats">
          <span className="stat">{t("feed.count", { n: items.length })}</span>
          <span className="stat">{t("feed.sources", { n: new Set(items.map((d) => d.source)).size })}</span>
          {fresh.length ? <span className="stat">{t("feed.new", { n: fresh.length })}</span> : null}
        </div>
      </div>

      {fresh.length > 0 ? (
        <div className="monitor">
          <div className="mi"><Icon name="bell" /></div>
          <div className="mt">
            <b>{t("feed.monitor", { n: fresh.length })}</b>
            <span>{fresh[0].title} — {fmtDate(fresh[0].issued_at)}. {t("feed.check")}</span>
          </div>
          <Link className="btn btn-pri" href={`/documents/${fresh[0].id}`}>{t("feed.review")}</Link>
        </div>
      ) : null}

      <Chips value={kind} options={tabs} onChange={setKind} />
      <Chips value={status} options={statuses} onChange={setStatus} />

      {feed.isLoading ? <Skeleton /> : null}
      {feed.isError ? <EmptyState title={t("api.down")} hint={t("api.down.hint")} /> : null}
      {feed.isSuccess && items.length === 0 ? (
        <EmptyState title={t("feed.empty")} hint={t("feed.empty.hint")} />
      ) : null}

      <div className="doclist">
        {items.map((d) => {
          const k = KIND[d.kind];
          const st = STATUS[d.status];
          const src = SOURCE[d.source];
          return (
            <Link key={d.id} href={`/documents/${d.id}`} className="doc">
              <div className="dic"><Icon name={k.icon} /></div>
              <div className="dmain">
                <div className="dtitle">
                  {d.title}
                  {d.is_new ? <Badge tone="new">{t("feed.badge.new")}</Badge> : null}
                </div>
                <div className="dmeta">
                  <span className="src">{src ? <Icon name={src.icon} /> : null} {L.source(d.source)}</span>
                  {d.number_masked ? <span className="tnum">№ {d.number_masked}</span> : null}
                  {d.counterparty_masked ? <span>{d.counterparty_masked}</span> : null}
                  {d.object_label ? <span>{d.object_label}</span> : null}
                  <span>{fmtDate(d.issued_at)}</span>
                </div>
              </div>
              <div className="dright">
                <Badge tone={st.tone}>{L.status(d.status)}</Badge>
                <span className="chev"><Icon name="chev" /></span>
              </div>
            </Link>
          );
        })}
      </div>
    </>
  );
}
