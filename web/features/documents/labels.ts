import type { IconName, Tone } from "@/components/mygov";
import type { Schemas } from "@/lib/api/client";

type Kind = Schemas["DocumentKind"];
type Status = Schemas["DocumentStatus"];

export const KIND: Record<Kind, { label: string; icon: IconName }> = {
  notarial_act: { label: "Notarial harakat", icon: "reg" },
  poa_notarial: { label: "Notarial ishonchnoma", icon: "doc" },
  poa_car: { label: "Avtomobilga e-ishonchnoma", icon: "car" },
  ban: { label: "Taqiq", icon: "block" },
  real_estate_right: { label: "Ko'chmas mulk huquqi", icon: "home2" },
  vehicle: { label: "Avtomobil", icon: "car" },
  loan: { label: "Kredit", icon: "credit" },
  enforcement_case: { label: "Ijro ishi", icon: "gavel" },
  labor_contract: { label: "Mehnat shartnomasi", icon: "briefcase" },
  application: { label: "Davlat xizmati arizasi", icon: "doc" },
  notification: { label: "Bildirishnoma", icon: "reg" },
  company: { label: "Yuridik shaxs", icon: "briefcase" },
  tax_assessment: { label: "Soliq hisob-kitobi", icon: "credit" },
};

export const STATUS: Record<Status, { label: string; tone: Tone }> = {
  active: { label: "Amalda", tone: "good" },
  completed: { label: "Bajarilgan", tone: "info" },
  revoked: { label: "Bekor qilingan", tone: "crit" },
  expired: { label: "Muddati o'tgan", tone: "warn" },
  unknown: { label: "Noma'lum", tone: "info" },
};

export const SOURCE: Record<string, { label: string; icon: IconName }> = {
  "mygov.car_poa": { label: "my.gov.uz · avtomobilga e-ishonchnomalar", icon: "car" },
  "mygov.notarial_history": { label: "Notarial harakatlar tarixi", icon: "reg" },
  "mygov.requests": { label: "my.gov.uz · mening arizalarim", icon: "doc" },
  "birdarcha.company": { label: "Birdarcha.uz · yuridik shaxslarim", icon: "briefcase" },
  "mygov.career": { label: "my.gov.uz · mehnat faoliyati", icon: "briefcase" },
  "mygov.notifications": { label: "my.gov.uz · bildirishnomalar", icon: "reg" },
  "vakolat.check": { label: "Vakolat.uz · ishonchnomani tekshirish", icon: "shield" },
};

export const ROLE: Record<string, string> = {
  principal: "Ishonch bildiruvchi (siz)",
  agent: "Vakil (siz)",
  party: "Tomon",
  debtor: "Qarzdor",
  employee: "Xodim",
};

export const FIELD: Record<string, string> = {
  status: "Holat",
  valid_until: "Amal qilish muddati",
  issued_at: "Berilgan sana",
  title: "Nomi",
  owner_role: "Sizning rolingiz",
  "object.label": "Obyekt",
  "object.id_masked": "Obyekt raqami",
  parties: "Tomonlar",
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

export function ago(iso?: string | null, now = Date.now()): string {
  if (!iso) return "hali so'ralmagan";
  const s = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000));
  if (s < 60) return `${s} s oldin`;
  if (s < 3600) return `${Math.round(s / 60)} daq oldin`;
  return `${Math.round(s / 3600)} soat oldin`;
}
