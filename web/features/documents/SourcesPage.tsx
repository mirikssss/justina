"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { Badge, Button, EmptyState, Icon, PageHeader, Skeleton, type Tone } from "@/components/mygov";
import { api } from "@/lib/api/client";

import { useI18n } from "@/lib/i18n";

import { SOURCE, fmtDateTime, useLabels } from "./labels";
import { useSources } from "./queries";

const STATE: Record<string, { tone: Tone }> = {
  ok: { tone: "good" },
  error: { tone: "crit" },
  expired: { tone: "warn" },
  disabled: { tone: "info" },
};

// FR-D-16: «последний опрос N с назад», статус, «Обновить». Экран доказывает жюри, что данные живые.
export function SourcesPage() {
  const { t, tOr } = useI18n();
  const L = useLabels();
  const sources = useSources();
  const qc = useQueryClient();
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const refresh = useMutation({
    mutationFn: async (source_id: string) => {
      const { error, response } = await api.POST("/sources/{source_id}/refresh", { params: { path: { source_id } } });
      if (error !== undefined) throw new Error(response.status === 429 ? t("src.rate") : t("src.error"));
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["sources"] }),
  });

  return (
    <>
      <PageHeader title={t("src.title")} subtitle={t("src.subtitle")} />
      {sources.isLoading ? <Skeleton rows={2} /> : null}
      {sources.isError ? <EmptyState title={t("api.down")} /> : null}
      <div className="srcgrid">
        {(sources.data ?? []).map((s) => {
          const stKey = s.status in STATE ? s.status : "disabled";
          const st = STATE[stKey];
          return (
            <div key={s.source_id} className="srccard">
              <div className="st">
                <Icon name={SOURCE[s.source_id]?.icon ?? "layers"} />
                <b>{L.source(s.source_id, s.title)}</b>
                <Badge tone={st.tone}>{tOr(`src.state.${stKey}`, stKey)}</Badge>
              </div>
              <div className="ago tnum">
                {L.ago(s.last_poll_at, now)}
                <small>{t("src.last_poll", { at: fmtDateTime(s.last_ok_at) })}</small>
              </div>
              {s.last_error ? <div className="err">{s.last_error}</div> : null}
              <div style={{ display: "flex", gap: 10, alignItems: "center", justifyContent: "space-between" }}>
                <span className="vcount">{t("src.every", { n: s.poll_interval_s ?? "—" })}</span>
                <Button small variant="ghost" disabled={s.status === "disabled" || refresh.isPending}
                  onClick={() => refresh.mutate(s.source_id)}>{t("src.refresh")}</Button>
              </div>
            </div>
          );
        })}
      </div>
      {refresh.isError ? <p style={{ color: "var(--crit)", fontSize: 13 }}>{refresh.error.message}</p> : null}
    </>
  );
}
