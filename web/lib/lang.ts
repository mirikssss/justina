// Общее для сервера и клиента: язык интерфейса (узбекский по умолчанию) и имя cookie.
export type Lang = "uz" | "ru";
export const LANG_COOKIE = "lang";

export function parseLang(value: string | undefined | null): Lang {
  return value === "ru" ? "ru" : "uz";
}
