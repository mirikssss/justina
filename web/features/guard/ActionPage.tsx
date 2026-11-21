"use client";

import Link from "next/link";

import { API_BASE } from "@/lib/api/client";
import { Badge, Card, EmptyState, Icon, PageHeader, Skeleton } from "@/components/mygov";
import type { Schemas } from "@/lib/api/client";
import { useT } from "@/lib/i18n";

import { ACTION_FLOW, ACTION_STATUS, ACTION_TYPE, fmtDateTime, secondsBetween } from "./labels";
import { useAction, useActionLive } from "./queries";

// FR-G-14: ход действия живыми шагами по action.updated (SSE). В конце — «Подтверждено источником»
// и скриншот результата (GET /guard/actions/{id}/evidence). failed/expired показываем отдельно.
const FINAL: Schemas["ActionStatus"][] = ["done", "failed", "expired"];

export function ActionPage({ id }: { id: string }) {
  useActionLive(id);
  const t = useT();
  const q = useAction(id);
  if (q.isLoading) return <Skeleton rows={4} />;
  if (q.isError || !q.data) return <EmptyState title={t("Harakat topilmadi")} hint={t("Ro'yxatga qayting")} />;
  const a = q.data;

  const reached = new Map(a.steps.map((s) => [s.status, s.at]));
  const doneIn = secondsBetween(reached.get("confirmed"), reached.get("done")); // T11
  const failed = a.status === "failed";
  const expired = a.status === "expired";
  // Индекс текущего шага в нормальном потоке (для подсветки «идёт сейчас»).
  const flowIdx = ACTION_FLOW.indexOf(a.status);

  return (
    <>
      <Link href="/alerts" className="back"><Icon name="back" /> {t("Ogohlantirishlar")}</Link>
      <PageHeader
        title={t("Harakat jarayoni")}
        subtitle={t(ACTION_TYPE[a.type])}
        actions={<Badge tone={failed || expired ? "crit" : a.status === "done" ? "good" : "info"}>{t(ACTION_STATUS[a.status].label)}</Badge>}
      />

      <div className="detail">
        <div className="dcol">
          <Card title={t("Bosqichlar")} icon="layers">
            <div className="tl">
              {ACTION_FLOW.map((step, i) => {
                const at = reached.get(step);
                const done = at !== undefined || (flowIdx >= 0 && i < flowIdx);
                const current = flowIdx === i && !FINAL.includes(a.status);
                const stopped = (failed || expired) && !done && i > flowIdx;
                return (
                  <div key={step} className={`ev${current ? " cur" : ""}`} style={stopped ? { opacity: 0.4 } : undefined}>
                    <span className="dot" style={done && !current ? { background: "var(--good)", boxShadow: "0 0 0 1px var(--good)" } : undefined} />
                    <div className="ec">
                      <b>{t(ACTION_STATUS[step].label)}</b>
                      {at ? <span className="dt">{fmtDateTime(at)}</span> : current ? <span className="dt">{t("hozir…")}</span> : null}
                      <p>{t(ACTION_STATUS[step].hint)}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          {a.status === "done" ? (
            <Card title={t("Natija")} icon="shield2" tag={t("Manba tomonidan tasdiqlandi")}>
              <p className="ai-sum" style={{ color: "var(--good)", fontWeight: 600 }}>
                <Icon name="check2" size={16} /> {t("Bekor qilindi. Natija manbada tasdiqlandi")}
                {a.result?.verified_status ? ` (${a.result.verified_status})` : ""}.
              </p>
              {doneIn !== null ? <p className="note">{t("Tasdiqlashdan natijagacha: {n} s", { n: doneIn })}</p> : null}
              <Evidence id={id} />
            </Card>
          ) : null}

          {failed ? (
            <Card title={t("Bajarilmadi")} icon="warn">
              <div className="err">{a.result?.error ?? t("Manbadan tasdiq olinmadi. Kabinetni tekshiring.")}</div>
              <Evidence id={id} />
            </Card>
          ) : null}

          {expired ? (
            <Card title={t("Muddati tugadi")} icon="warn">
              <div className="err">{t("Tasdiqlash muddati o'tdi. Hujjat kartasidan harakatni qaytadan boshlang.")}</div>
            </Card>
          ) : null}
        </div>

        <Card title={t("Qadam-baqadam")} className="guard-aside">
          <p className="note">
            {t("Harakat ikki bosqichda tasdiqlanadi: sayt — so'rov, Telegram — kod. Kod faqat sizning ulangan Telegramingizga keladi va 2 daqiqa amal qiladi.")}
          </p>
          {!FINAL.includes(a.status) ? (
            <p className="note" style={{ marginTop: 10 }}>
              <Icon name="bolt" size={14} /> {t("Jarayon jonli yangilanadi — sahifani yopishingiz mumkin.")}
            </p>
          ) : null}
        </Card>
      </div>
    </>
  );
}

function Evidence({ id }: { id: string }) {
  const t = useT();
  // Скриншот результата отдаётся как image/png с cookie-сессией; same-origin через /api.
  return (
    <a className="evidence" href={`${API_BASE}/guard/actions/${id}/evidence`} target="_blank" rel="noopener">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={`${API_BASE}/guard/actions/${id}/evidence`} alt={t("Natija skrinshoti")} loading="lazy" />
      <span className="link">{t("To'liq ko'rish")} <Icon name="chev" size={16} /></span>
    </a>
  );
}
