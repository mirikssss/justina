"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { api } from "@/lib/api/client";
import { LANGS, useI18n, type MessageKey } from "@/lib/i18n";

import { Icon, type IconName } from "./Icon";

// Каркас как у живого my.gov.uz: синее меню-плашка слева, шапка, контент.
// До 1500px меню сворачивается в иконки, до 992px — выезжает по кнопке (те же брейкпоинты, что у портала).
// Герб и логотип MyGov не копируем (FR-G-15): на их месте — название модуля и плашка «Prototip».
const NAV: { href: string; label: MessageKey; icon: IconName }[] = [
  { href: "/documents", label: "nav.documents", icon: "folder" },
  { href: "/alerts", label: "nav.alerts", icon: "bell" },
  { href: "/sources", label: "nav.sources", icon: "layers" },
  { href: "/family", label: "nav.family", icon: "family" },
];

/** Переключатель языка интерфейса в шапке: O‘z (по умолчанию) / Рус. */
function LangSwitch() {
  const { lang, setLang, t } = useI18n();
  const [open, setOpen] = useState(false);
  const current = LANGS.find((l) => l.value === lang) ?? LANGS[0];
  return (
    <div style={{ position: "relative" }}>
      <button type="button" className="lang" aria-haspopup="listbox" aria-expanded={open} aria-label={t("nav.lang")}
              onClick={() => setOpen((v) => !v)}
              style={{ background: "none", border: 0, cursor: "pointer", font: "inherit" }}>
        {current.label}<Icon name="cdown" size={18} />
      </button>
      {open ? (
        <ul role="listbox" aria-label={t("nav.lang")}
            style={{ position: "absolute", right: 0, top: "calc(100% + 6px)", zIndex: 20, listStyle: "none", margin: 0,
                     padding: 6, background: "var(--card)", border: "1px solid var(--border)", borderRadius: 10,
                     boxShadow: "0 8px 24px rgba(0,0,0,.08)", minWidth: 96 }}>
          {LANGS.map((l) => (
            <li key={l.value} role="option" aria-selected={l.value === lang}>
              <button type="button" onClick={() => { setLang(l.value); setOpen(false); }}
                      style={{ width: "100%", textAlign: "left", padding: "8px 10px", border: 0, borderRadius: 8, cursor: "pointer",
                               font: "inherit", fontWeight: l.value === lang ? 700 : 500,
                               background: l.value === lang ? "var(--light-primary)" : "transparent", color: "var(--blue)" }}>
                {l.label}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function initials(name: string) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase() || "?";
}

export function Shell({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const me = useQuery({ queryKey: ["me"], queryFn: async () => (await api.GET("/me")).data ?? null, staleTime: 60_000 });
  useEffect(() => setOpen(false), [path]);
  const name = me.data?.display_name ?? "…";

  return (
    <div className={`shell${open ? " nav-open" : ""}`}>
      <aside className="rail" aria-label={t("nav.menu")}>
        <div className="scroll">
          <Link href="/documents" className="brand">
            <span className="logo"><Icon name="shield2" size={22} /></span>
            <span className="wm">{t("app.name")}<small>{t("app.module")}</small></span>
          </Link>

          <div className="profile" title={name}>
            <div className="avatar">{initials(name)}</div>
            <div className="who">
              <div className="nm">{name}</div>
              <div className="sub">OneID</div>
            </div>
          </div>

          <div className="navsec">{t("nav.section")} <Icon name="cdown" size={16} /></div>
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
            <button className="mob-menu" aria-label={t("nav.menu")} onClick={() => setOpen((v) => !v)}>
              <Icon name="menu" size={24} />
            </button>
            <span className="portal-name">{t("app.portal")}</span>
            <span className="proto">{t("app.proto")}</span>
          </div>
          <div className="topbar-actions">
            <LangSwitch />
            <span className="sep" />
            <span className="hide-sm" style={{ color: "var(--blue)" }}><Icon name="access" size={24} /></span>
            <button className="btn-login" onClick={() => api.POST("/auth/logout").then(() => (location.href = "/login"))}>
              <span className="bi">{initials(name)}</span>
              {t("nav.logout")}
            </button>
          </div>
        </header>
        {children}
        <div className="foot">
          {t("app.footer")}
        </div>
      </main>
      <div className="scrim" onClick={() => setOpen(false)} />
    </div>
  );
}
