"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { Badge, Card, EmptyState, Icon, PageHeader, Skeleton, type Tone } from "@/components/mygov";
import { api } from "@/lib/api/client";
import { useLocale, useT } from "@/lib/i18n";

import { KIND, STATUS, fmtDate, fmtDateTime } from "./labels";

const LEVEL: Record<string, { label: string; tone: Tone }> = {
  high: { label: "Muhim", tone: "crit" },
  medium: { label: "Diqqat", tone: "warn" },
  info: { label: "Ma'lumot", tone: "info" },
};

// Сводка: что у человека есть, что истекает, что требует внимания, что изменилось, насколько свежие данные.
export function OverviewPage() {
  const t = useT();
  const { locale } = useLocale();
  const q = useQuery({
    queryKey: ["overview"],
    queryFn: async () => {
      const { data, error } = await api.GET("/documents/overview");
      if (error !== undefined || !data) throw new Error("overview");
      return data;
    },
    refetchInterval: 15_000,
  });
  const o = q.data;
  const stat = { fontSize: 28, fontWeight: 700, lineHeight: 1.1 } as const;

  return (
    <>
      <PageHeader title={t("Umumiy ko'rinish")} subtitle={t("Sizning barcha hujjatlaringiz, muddatlar va e'tibor talab qiladigan narsalar")} />
      {q.isLoading ? <Skeleton rows={3} /> : null}
      {q.isError ? <EmptyState title={t("API bilan aloqa yo'q")} /> : null}
      {o ? (
        <div style={{ display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", alignItems: "start" }}>
          <Card title={t("Raqamlarda")} icon="layers">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
              <div><div className="tnum" style={stat}>{o.total}</div><small>{t("hujjat")}</small></div>
              <div><div className="tnum" style={stat}>{o.new_7d}</div><small>{t("7 kunda yangi")}</small></div>
              <div><div className="tnum" style={stat}>{o.sources.ok ?? 0}</div><small>{t("manba ishlayapti")}</small></div>
            </div>
            <div style={{ marginTop: 14, display: "flex", gap: 6, flexWrap: "wrap" }}>
              {o.by_kind.map((k) => (
                <Link key={k.kind} href={`/documents?kind=${k.kind}`} className="chip" style={{ fontSize: 12 }}>
                  {KIND[k.kind as keyof typeof KIND] ? t(KIND[k.kind as keyof typeof KIND].label) : k.kind} · {k.count}
                </Link>
              ))}
            </div>
          </Card>

          <Card title={t("E'tibor talab qiladi")} icon="warn">
            {o.attention.length === 0 ? <p>{t("Hozircha hammasi joyida")}</p> : (
              <div style={{ display: "grid", gap: 10 }}>
                {o.attention.map((a, i) => (
                  <div key={`${a.type}${i}`} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                    <Badge tone={LEVEL[a.level].tone}>{t(LEVEL[a.level].label)}</Badge>
                    <div style={{ minWidth: 0 }}>
                      {a.document_id ? <Link href={`/documents/${a.document_id}`}><b>{a.title}</b></Link> : <b>{a.title}</b>}
                      <div style={{ fontSize: 13, color: "var(--muted)" }}>{locale === "ru" ? a.text : a.text_uz}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card title={t("Tez orada tugaydi")} icon="bell">
            {o.expiring.length === 0 ? <p>{t("90 kun ichida tugaydigan hujjat yo'q")}</p> : (
              <div style={{ display: "grid", gap: 8 }}>
                {o.expiring.map((e) => (
                  <Link key={e.id} href={`/documents/${e.id}`} style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                    <span>{e.title}</span>
                    <span className="tnum" style={{ color: e.days_left <= 30 ? "var(--crit)" : "var(--muted)" }}>
                      {fmtDate(e.valid_until)} · {e.days_left} {t("kun")}
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </Card>

          <Card title={t("So'nggi o'zgarishlar")} icon="list">
            {o.recent_changes.length === 0 ? <p>{t("Hali o'zgarishlar yo'q")}</p> : (
              <div style={{ display: "grid", gap: 8 }}>
                {o.recent_changes.map((r) => (
                  <Link key={r.id} href={`/documents/${r.id}`} style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
                    <span style={{ minWidth: 0 }}><Icon name={KIND[r.kind as keyof typeof KIND]?.icon ?? "doc"} size={15} /> {r.title}</span>
                    <span style={{ display: "flex", gap: 8, alignItems: "center", whiteSpace: "nowrap" }}>
                      <Badge tone={STATUS[r.status as keyof typeof STATUS]?.tone ?? "info"}>{STATUS[r.status as keyof typeof STATUS] ? t(STATUS[r.status as keyof typeof STATUS].label) : r.status}</Badge>
                      <small>{fmtDateTime(r.updated_at)}</small>
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </Card>
        </div>
      ) : null}
    </>
  );
}
