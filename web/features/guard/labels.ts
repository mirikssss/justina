import type { Tone } from "@/components/mygov";
import type { Schemas } from "@/lib/api/client";

type Severity = Schemas["Severity"];
type ActionStatus = Schemas["ActionStatus"];
type AlertStatus = Schemas["AlertStatus"];
type ConsentScope = Schemas["ConsentScope"];

// Подписи для контекста «Сторож» (uz). Переключатель uz/ru (next-intl) — отдельная задача FR-G-15;
// пока язык кабинета — узбекский, как и во всём ките.

export const SEVERITY: Record<Severity, { label: string; tone: Tone; icon: "warn" | "bell" | "info" }> = {
  critical: { label: "Muhim", tone: "crit", icon: "warn" },
  high: { label: "Yuqori", tone: "warn", icon: "bell" },
  info: { label: "Ma'lumot", tone: "info", icon: "info" },
};

// Правила G1–G7 (раздел 4 ТЗ): короткое имя для метки над тревогой.
export const RULE: Record<string, string> = {
  G1: "Yangi ishonchnoma",
  G2: "Notarial harakat",
  G3: "Holat o'zgardi",
  G4: "Muddati tugayapti",
  G5: "Hujjat yo'qoldi",
  G6: "Manba uzildi",
  G7: "Oila nusxasi",
};

export const ALERT_STATUS: Record<AlertStatus, string> = {
  new: "Yangi",
  seen: "Ko'rilgan",
  closed: "Yopilgan",
};

// Машина состояний действия (FR-G-07): порядок и подписи шагов.
export const ACTION_FLOW: ActionStatus[] = [
  "proposed",
  "awaiting_confirmation",
  "confirmed",
  "executing",
  "verifying",
  "done",
];

export const ACTION_STATUS: Record<ActionStatus, { label: string; hint: string }> = {
  proposed: { label: "So'ralgan", hint: "Harakat so'raldi" },
  awaiting_confirmation: { label: "Tasdiq kutilmoqda", hint: "Telegramga kod yuborildi" },
  confirmed: { label: "Tasdiqlandi", hint: "Kod qabul qilindi" },
  executing: { label: "Bajarilmoqda", hint: "Manbada amalga oshirilmoqda" },
  verifying: { label: "Tekshirilmoqda", hint: "Natija manbadan tekshirilmoqda" },
  done: { label: "Bajarildi", hint: "Manba tomonidan tasdiqlandi" },
  failed: { label: "Xatolik", hint: "Bajarilmadi — kabinetni tekshiring" },
  expired: { label: "Muddati tugadi", hint: "Tasdiqlash muddati o'tdi" },
};

export const ACTION_TYPE: Record<Schemas["ActionType"], string> = {
  revoke_car_poa: "Avto ishonchnomasini bekor qilish",
};

export const SCOPE: Record<ConsentScope, { label: string; hint: string }> = {
  read_documents: { label: "Hujjatlarni ko'rish", hint: "Mening hujjatlarim ro'yxatini ko'radi" },
  receive_alerts: { label: "Ogohlantirishlarni olish", hint: "Muhim ogohlantirishlar nusxasini oladi" },
};

const SEC = 1000;
export function fmtDateTime(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("uz-UZ", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}
export function fmtAgo(iso?: string | null): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / (60 * SEC));
  if (m < 1) return "hozir";
  if (m < 60) return `${m} daq. oldin`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} soat oldin`;
  return `${Math.floor(h / 24)} kun oldin`;
}
