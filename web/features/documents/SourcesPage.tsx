"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { Badge, Button, EmptyState, Icon, PageHeader, Skeleton, type Tone } from "@/components/mygov";
import { api } from "@/lib/api/client";
import { useLocale, useT } from "@/lib/i18n";

import { SOURCE, ago, fmtDateTime } from "./labels";
import { useSources } from "./queries";

const STATE: Record<string, { label: string; tone: Tone }> = {
  ok: { label: "Ishlayapti", tone: "good" },
  error: { label: "Xatolik", tone: "crit" },
  expired: { label: "Sessiya tugagan", tone: "warn" },
  disabled: { label: "Ulanmagan", tone: "info" },
};

// FR-D-16: «последний опрос N с назад», статус, «Обновить». Экран доказывает жюри, что данные живые.
export function SourcesPage() {
  const t = useT();
  const { locale } = useLocale();
  const sources = useSources();
  const qc = useQueryClient();
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const refresh = useMutation({
    mutationFn: async (source_id: string) => {
      const { error, response } = await api.POST("/sources/{source_id}/refresh", { params: { path: { source_id } } });
      if (error !== undefined) throw new Error(response.status === 429 ? "20 soniyada bir martadan ko'p emas" : "xato");
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["sources"] }),
  });

  return (
    <>
      <PageHeader title={t("Manbalar")} subtitle={t("Ma'lumotlar qayerdan va qanchalik yangi kelayotgani")} />
      {sources.isLoading ? <Skeleton rows={2} /> : null}
      {sources.isError ? <EmptyState title={t("API bilan aloqa yo'q")} /> : null}
      <div className="srcgrid">
        {(sources.data ?? []).map((s) => {
          const st = STATE[s.status] ?? STATE.disabled;
          return (
            <div key={s.source_id} className="srccard">
              <div className="st">
                <Icon name={SOURCE[s.source_id]?.icon ?? "layers"} />
                <b>{SOURCE[s.source_id] ? t(SOURCE[s.source_id].label) : s.title}</b>
                <Badge tone={st.tone}>{t(st.label)}</Badge>
              </div>
              <div className="ago tnum">
                {ago(s.last_poll_at, now, locale)}
                <small>{t("oxirgi so'rov · muvaffaqiyatli:")} {fmtDateTime(s.last_ok_at)}</small>
              </div>
              {s.last_error ? <div className="err">{s.last_error}</div> : null}
              <div style={{ display: "flex", gap: 10, alignItems: "center", justifyContent: "space-between" }}>
                <span className="vcount">{t("har {n} s", { n: s.poll_interval_s ?? "—" })}</span>
                <Button small variant="ghost" disabled={s.status === "disabled" || refresh.isPending}
                  onClick={() => refresh.mutate(s.source_id)}>{t("Yangilash")}</Button>
              </div>
            </div>
          );
        })}
      </div>
      {refresh.isError ? <p style={{ color: "var(--crit)", fontSize: 13 }}>{t(refresh.error.message)}</p> : null}
    </>
  );
}
