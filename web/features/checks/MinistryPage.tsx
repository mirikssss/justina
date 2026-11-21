"use client";

import { useQuery } from "@tanstack/react-query";

import { Badge, Card, EmptyState, PageHeader, Skeleton } from "@/components/mygov";
import { api } from "@/lib/api/client";
import { useT } from "@/lib/i18n";

const SEVERITY_TONE = { critical: "crit", high: "warn", info: "info" } as const;

function Bar({ value, max }: { value: number; max: number }) {
  return (
    <span style={{ display: "inline-block", height: 8, width: `${Math.max(4, (value / Math.max(max, 1)) * 100)}%`, minWidth: 4,
      background: "var(--blue)", borderRadius: 4 }} />
  );
}

// Панель рисков Минюста: обезличенные агрегаты, без личных данных и номеров документов.
export function MinistryPage() {
  const t = useT();
  const risks = useQuery({
    queryKey: ["analytics", "risks"],
    queryFn: async () => { const { data, error } = await api.GET("/analytics/risks"); if (error !== undefined || !data) throw new Error("x"); return data; },
    refetchInterval: 15_000,
  });
  const docs = useQuery({
    queryKey: ["analytics", "documents"],
    queryFn: async () => { const { data, error } = await api.GET("/analytics/documents"); if (error !== undefined || !data) throw new Error("x"); return data; },
    refetchInterval: 15_000,
  });
  const r = risks.data;
  const maxRule = Math.max(0, ...(r?.by_rule.map((x) => x.count) ?? []));

  return (
    <>
      <PageHeader title={t("Adliya vazirligi xavf paneli")}
        subtitle={t("Shaxsiy ma'lumotlarsiz umumlashtirilgan ko'rsatkichlar: ogohlantirishlar, «Bu men emasman» ulushi, yetkazish tezligi")} />
      {risks.isLoading ? <Skeleton rows={2} /> : null}
      {risks.isError ? <EmptyState title={t("API bilan aloqa yo'q")} /> : null}
      {r ? (
        <div style={{ display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", alignItems: "start" }}>
          <Card title={t("Asosiy ko'rsatkichlar")} icon="shield">
            <dl style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: "8px 16px", margin: 0 }}>
              <dt>{t("Ogohlantirishlar")} ({r.days} {t("kun")})</dt><dd className="tnum" style={{ margin: 0 }}><b>{r.alerts}</b></dd>
              <dt>{t("Javob berilgan")}</dt><dd className="tnum" style={{ margin: 0 }}>{r.answered}</dd>
              <dt>{t("«Bu men emasman»")}</dt><dd className="tnum" style={{ margin: 0 }}>{r.not_me}{r.not_me_share !== null ? ` (${Math.round(r.not_me_share * 100)}%)` : ""}</dd>
              <dt>{t("Yetkazish, median")}</dt><dd className="tnum" style={{ margin: 0 }}>{r.delivery_seconds.p50 !== null ? `${r.delivery_seconds.p50} s` : "—"}</dd>
              <dt>{t("Yetkazish, p95")}</dt><dd className="tnum" style={{ margin: 0 }}>{r.delivery_seconds.p95 !== null ? `${r.delivery_seconds.p95} s` : "—"}</dd>
            </dl>
          </Card>
          <Card title={t("Qoidalar bo'yicha")} icon="layers">
            {r.by_rule.length === 0 ? <p>{t("Hozircha ogohlantirishlar yo'q")}</p> : (
              <div style={{ display: "grid", gap: 10 }}>
                {r.by_rule.map((x) => (
                  <div key={`${x.rule_id}${x.severity}`}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                      <span><b>{x.rule_id}</b> <Badge tone={SEVERITY_TONE[x.severity as keyof typeof SEVERITY_TONE] ?? "info"}>{x.severity}</Badge></span>
                      <span className="tnum">{x.count}</span>
                    </div>
                    <Bar value={x.count} max={maxRule} />
                  </div>
                ))}
              </div>
            )}
          </Card>
          <Card title={t("Kunlar bo'yicha")} icon="bell">
            {r.per_day.length === 0 ? <p>{t("Hozircha ogohlantirishlar yo'q")}</p> : (
              <div style={{ display: "grid", gap: 6, fontSize: 13 }}>
                {r.per_day.map((d) => (
                  <div key={d.day} style={{ display: "flex", justifyContent: "space-between" }}>
                    <span className="tnum">{d.day}</span><span className="tnum">{d.count}{d.critical ? ` · ${d.critical} critical` : ""}</span>
                  </div>
                ))}
              </div>
            )}
          </Card>
          <Card title={t("Hujjatlar")} icon="folder">
            {docs.data ? (
              <>
                <p style={{ margin: "0 0 8px" }}>{docs.data.citizens} {t("fuqaro")} · {docs.data.documents} {t("hujjat")}</p>
                <div style={{ display: "grid", gap: 4, fontSize: 13 }}>
                  {docs.data.by_kind_status.map((x) => (
                    <div key={`${x.kind}${x.status}`} style={{ display: "flex", justifyContent: "space-between" }}>
                      <span>{x.kind} · {x.status}</span><span className="tnum">{x.count}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : <Skeleton rows={1} />}
          </Card>
        </div>
      ) : null}
      <p style={{ marginTop: 16, fontSize: 12, color: "var(--muted)" }}>
        {t("Prototip: hudud va notarius kesimi hamda kichik guruhlarni yashirish (k-anonimlik) hali yo'q.")}
      </p>
    </>
  );
}
