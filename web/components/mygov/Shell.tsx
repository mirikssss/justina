"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { api } from "@/lib/api/client";
import { LOCALES, LOCALE_NAME, LOCALE_SHORT, useLocale, useT } from "@/lib/i18n";

import { Icon, type IconName } from "./Icon";

// Каркас как у живого my.gov.uz: синее меню-плашка слева, шапка, контент.
// До 1500px меню сворачивается в иконки, до 992px — выезжает по кнопке (те же брейкпоинты, что у портала).
// Герб и логотип MyGov не копируем (FR-G-15): на их месте — название модуля и плашка «Prototip».
const NAV: { href: string; label: string; icon: IconName }[] = [
  { href: "/documents", label: "Mening hujjatlarim", icon: "folder" },
  { href: "/alerts", label: "Bildirishnomalar", icon: "bell" },
  { href: "/sources", label: "Manbalar", icon: "layers" },
  { href: "/family", label: "Oila", icon: "family" },
  { href: "/precheck", label: "Bitimdan oldin tekshirish", icon: "scale" },
  { href: "/notary", label: "Notarius kabineti", icon: "gavel" },
  { href: "/ministry", label: "Xavf paneli", icon: "shield2" },
];

function initials(name: string) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase() || "?";
}

// Переключатель uz/ru (FR-G-15). Простой дропдаун в шапке; выбор хранится в localStorage.
function LangSwitch() {
  const { locale, setLocale } = useLocale();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onEsc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onEsc);
    };
  }, [open]);

  return (
    <div className="lang-wrap" ref={ref}>
      <button type="button" className="lang" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        {LOCALE_SHORT[locale]}
        <Icon name="cdown" size={18} />
      </button>
      {open ? (
        <div className="lang-menu" role="menu">
          {LOCALES.map((l) => (
            <button
              key={l}
              type="button"
              role="menuitemradio"
              aria-checked={l === locale}
              className={l === locale ? "on" : ""}
              onClick={() => { setLocale(l); setOpen(false); }}
            >
              {LOCALE_NAME[l]}
              {l === locale ? <Icon name="check2" size={16} /> : null}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const t = useT();
  const [open, setOpen] = useState(false);
  const me = useQuery({ queryKey: ["me"], queryFn: async () => (await api.GET("/me")).data ?? null, staleTime: 60_000 });
  useEffect(() => setOpen(false), [path]);
  const name = me.data?.display_name ?? "…";

  return (
    <div className={`shell${open ? " nav-open" : ""}`}>
      <aside className="rail" aria-label={t("Menyu")}>
        <div className="scroll">
          <Link href="/documents" className="brand">
            <span className="logo"><Icon name="shield2" size={22} /></span>
            <span className="wm">{t("Mening hujjatlarim")}<small>{t("MyGov moduli")}</small></span>
          </Link>

          <div className="profile" title={name}>
            <div className="avatar">{initials(name)}</div>
            <div className="who">
              <div className="nm">{name}</div>
              <div className="sub">OneID</div>
            </div>
          </div>

          <div className="navsec">{t("Hujjatlar")} <Icon name="cdown" size={16} /></div>
          <nav className="nav">
            {NAV.map((n) => (
              <Link key={n.href} href={n.href} className={path?.startsWith(n.href) ? "on" : ""} title={t(n.label)}>
                <span className="ic"><Icon name={n.icon} size={21} /></span>
                <span className="lbl">{t(n.label)}</span>
              </Link>
            ))}
          </nav>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <button className="mob-menu" aria-label={t("Menyu")} onClick={() => setOpen((v) => !v)}>
              <Icon name="menu" size={24} />
            </button>
            <span className="portal-name">{t("Mening hujjatlarim — MyGov moduli")}</span>
            <span className="proto">{t("Prototip")}</span>
          </div>
          <div className="topbar-actions">
            <LangSwitch />
            <span className="sep" />
            <span className="hide-sm" style={{ color: "var(--blue)" }}><Icon name="access" size={24} /></span>
            <button className="btn-login" onClick={() => api.POST("/auth/logout").then(() => (location.href = "/login"))}>
              <span className="bi">{initials(name)}</span>
              {t("Chiqish")}
            </button>
          </div>
        </header>
        {children}
        <div className="foot">
          {t("Bu —")} <b>{t("prototip")}</b>: {t("MyGov ichidagi «Mening hujjatlarim» moduli. Haqiqiy davlat portali emas.")}
        </div>
      </main>
      <div className="scrim" onClick={() => setOpen(false)} />
    </div>
  );
}
