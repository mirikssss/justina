"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge, Chips, EmptyState, Icon, Skeleton } from "@/components/mygov";

import { KIND, SOURCE, STATUS, fmtDate } from "./labels";
import { useDocumentsLive, useFeed } from "./queries";

type KindFilter = "all" | keyof typeof KIND;

const TABS: { value: KindFilter; label: string }[] = [
  { value: "all", label: "Barchasi" },
  { value: "poa_car", label: "E-ishonchnomalar" },
  { value: "poa_notarial", label: "Notarial ishonchnomalar" },
  { value: "notarial_act", label: "Notarial harakatlar" },
];

const STATUSES = [
  { value: "", label: "Har qanday holat" },
  { value: "active", label: "Amalda" },
  { value: "revoked", label: "Bekor qilingan" },
  { value: "expired", label: "Muddati o'tgan" },
  { value: "completed", label: "Bajarilgan" },
];

// FR-D-14: вкладки по типу, фильтр по статусу, поиск, метка «новое», живое обновление.
export function DocumentFeed() {
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
        <h1>Mening hujjatlarim</h1>
        <p>Turli davlat reyestrlaridan to&apos;plangan hujjatlaringiz — versiyalar tarixi bilan birga.
          Yangi hujjat paydo bo&apos;lsa, darhol xabar beramiz.</p>
        <label className="search">
          <Icon name="search" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Nomi yoki raqami bo'yicha qidirish" />
        </label>
        <div className="stats">
          <span className="stat">{items.length} ta hujjat</span>
          <span className="stat">{new Set(items.map((d) => d.source)).size} ta manba</span>
          {fresh.length ? <span className="stat">{fresh.length} ta yangi</span> : null}
        </div>
      </div>

      {fresh.length > 0 ? (
        <div className="monitor">
          <div className="mi"><Icon name="bell" /></div>
          <div className="mt">
            <b>Monitoring: {fresh.length} ta yangi hujjat</b>
            <span>{fresh[0].title} — {fmtDate(fresh[0].issued_at)}. Siz bilan bog'liqligini tekshiring.</span>
          </div>
          <Link className="btn btn-pri" href={`/documents/${fresh[0].id}`}>Ko'rib chiqish</Link>
        </div>
      ) : null}

      <Chips value={kind} options={TABS} onChange={setKind} />
      <Chips value={status} options={STATUSES} onChange={setStatus} />

      {feed.isLoading ? <Skeleton /> : null}
      {feed.isError ? <EmptyState title="API bilan aloqa yo'q" hint="Backend ishga tushirilganini tekshiring: make db, storozh api" /> : null}
      {feed.isSuccess && items.length === 0 ? (
        <EmptyState title="Hujjatlar topilmadi" hint="Manbani ulang (storozh documents connect) yoki demo: storozh documents seed" />
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
                  {d.is_new ? <Badge tone="new">YANGI</Badge> : null}
                </div>
                <div className="dmeta">
                  <span className="src">{src ? <Icon name={src.icon} /> : null} {src?.label ?? d.source}</span>
                  {d.number_masked ? <span className="tnum">№ {d.number_masked}</span> : null}
                  {d.counterparty_masked ? <span>{d.counterparty_masked}</span> : null}
                  {d.object_label ? <span>{d.object_label}</span> : null}
                  <span>{fmtDate(d.issued_at)}</span>
                </div>
              </div>
              <div className="dright">
                <Badge tone={st.tone}>{st.label}</Badge>
                <span className="chev"><Icon name="chev" /></span>
              </div>
            </Link>
          );
        })}
      </div>
    </>
  );
}
