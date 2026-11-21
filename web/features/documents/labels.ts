import type { IconName, Tone } from "@/components/mygov";
import type { Schemas } from "@/lib/api/client";
import { useI18n } from "@/lib/i18n";

type Kind = Schemas["DocumentKind"];
type Status = Schemas["DocumentStatus"];

export const KIND: Record<Kind, { icon: IconName }> = {
  notarial_act: { icon: "reg" },
  poa_notarial: { icon: "doc" },
  poa_car: { icon: "car" },
  ban: { icon: "block" },
  real_estate_right: { icon: "home2" },
  vehicle: { icon: "car" },
  loan: { icon: "credit" },
  enforcement_case: { icon: "gavel" },
  labor_contract: { icon: "briefcase" },
  application: { icon: "doc" },
  notification: { icon: "reg" },
  company: { icon: "briefcase" },
  tax_assessment: { icon: "credit" },
};

export const STATUS: Record<Status, { tone: Tone }> = {
  active: { tone: "good" },
  completed: { tone: "info" },
  revoked: { tone: "crit" },
  expired: { tone: "warn" },
  unknown: { tone: "info" },
};

export const SOURCE: Record<string, { icon: IconName }> = {
  "mygov.car_poa": { icon: "car" },
  "mygov.notarial_history": { icon: "reg" },
  "mygov.requests": { icon: "doc" },
  "soliq.property": { icon: "home2" },
  "soliq.vehicles": { icon: "car" },
  "soliq.taxes": { icon: "credit" },
  "birdarcha.company": { icon: "briefcase" },
  "mygov.career": { icon: "briefcase" },
  "mygov.notifications": { icon: "reg" },
  "vakolat.check": { icon: "shield" },
};

export function fmtDate(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("ru-RU");
}

export function fmtDateTime(iso?: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });
}

/** Подписи справочников на языке интерфейса (иконки и цвета — в KIND / STATUS / SOURCE выше). */
export function useLabels() {
  const { t, tOr } = useI18n();
  return {
    kind: (k: string) => tOr(`kind.${k}`, k),
    status: (s: string) => tOr(`status.${s}`, s),
    source: (id: string, fallback?: string) => tOr(`source.${id}`, fallback ?? id),
    role: (r: string, you = false) => `${tOr(`role.${r}`, r)}${you ? ` ${t("role.you")}` : ""}`,
    field: (f: string) => tOr(`field.${f}`, f),
    ago: (iso?: string | null, now = Date.now()) => {
      if (!iso) return t("ago.never");
      const s = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000));
      if (s < 60) return t("ago.s", { n: s });
      if (s < 3600) return t("ago.m", { n: Math.round(s / 60) });
      return t("ago.h", { n: Math.round(s / 3600) });
    },
  };
}
