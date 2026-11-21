"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { LOCALES, RU, type Locale } from "./messages";

export { LOCALES, LOCALE_NAME, LOCALE_SHORT } from "./messages";
export type { Locale } from "./messages";

const STORAGE_KEY = "storozh.locale";

export type TVars = Record<string, string | number>;
// t(uz) — исходная строка кабинета и есть ключ. vars заполняет {name}. ctx разводит одинаковые
// узбекские строки с разным переводом (ключ "<ctx>::<uz>").
export type TFn = (uz: string, vars?: TVars, ctx?: string) => string;

type Ctx = { locale: Locale; setLocale: (l: Locale) => void; t: TFn };
const LocaleContext = createContext<Ctx | null>(null);

function fill(s: string, vars?: TVars): string {
  if (!vars) return s;
  return s.replace(/\{(\w+)\}/g, (_, k: string) => (k in vars ? String(vars[k]) : `{${k}}`));
}

function isLocale(v: unknown): v is Locale {
  return typeof v === "string" && (LOCALES as string[]).includes(v);
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  // Сервер и первый клиентский рендер — "uz" (как <html lang="uz">), чтобы не было рассинхрона
  // гидрации; сохранённый выбор поднимаем из localStorage уже в эффекте.
  const [locale, setLocaleState] = useState<Locale>("uz");

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (isLocale(saved) && saved !== "uz") setLocaleState(saved);
    } catch {
      /* приватный режим / заблокированное хранилище — остаёмся на uz */
    }
  }, []);

  useEffect(() => {
    try {
      document.documentElement.lang = locale;
    } catch {
      /* no-op */
    }
  }, [locale]);

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    try {
      localStorage.setItem(STORAGE_KEY, l);
    } catch {
      /* no-op */
    }
  }, []);

  const t = useCallback<TFn>(
    (uz, vars, ctx) => {
      if (locale === "uz") return fill(uz, vars);
      const hit = (ctx ? RU[`${ctx}::${uz}`] : undefined) ?? RU[uz] ?? uz;
      return fill(hit, vars);
    },
    [locale],
  );

  const value = useMemo<Ctx>(() => ({ locale, setLocale, t }), [locale, setLocale, t]);
  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

function useLocaleContext(): Ctx {
  const ctx = useContext(LocaleContext);
  if (!ctx) throw new Error("useLocale must be used within <LocaleProvider>");
  return ctx;
}

export function useLocale(): { locale: Locale; setLocale: (l: Locale) => void } {
  const { locale, setLocale } = useLocaleContext();
  return { locale, setLocale };
}

export function useT(): TFn {
  return useLocaleContext().t;
}
