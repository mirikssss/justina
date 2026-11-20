"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { api } from "@/lib/api/client";

import { Icon, type IconName } from "./Icon";

// Каркас как у живого my.gov.uz: синее меню-плашка слева, шапка, контент.
// До 1500px меню сворачивается в иконки, до 992px — выезжает по кнопке (те же брейкпоинты, что у портала).
// Герб и логотип MyGov не копируем (FR-G-15): на их месте — название модуля и плашка «Prototip».
const NAV: { href: string; label: string; icon: IconName }[] = [
  { href: "/documents", label: "Mening hujjatlarim", icon: "folder" },
  { href: "/alerts", label: "Bildirishnomalar", icon: "bell" },
  { href: "/sources", label: "Manbalar", icon: "layers" },
  { href: "/family", label: "Oila", icon: "family" },
];

function initials(name: string) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase() || "?";
}

export function Shell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const me = useQuery({ queryKey: ["me"], queryFn: async () => (await api.GET("/me")).data ?? null, staleTime: 60_000 });
  useEffect(() => setOpen(false), [path]);
  const name = me.data?.display_name ?? "…";

  return (
    <div className={`shell${open ? " nav-open" : ""}`}>
      <aside className="rail" aria-label="Menyu">
        <div className="scroll">
          <Link href="/documents" className="brand">
            <span className="logo"><Icon name="shield2" size={22} /></span>
            <span className="wm">Mening hujjatlarim<small>MyGov moduli</small></span>
          </Link>

          <div className="profile" title={name}>
            <div className="avatar">{initials(name)}</div>
            <div className="who">
              <div className="nm">{name}</div>
              <div className="sub">OneID</div>
            </div>
          </div>

          <div className="navsec">Hujjatlar <Icon name="cdown" size={16} /></div>
          <nav className="nav">
            {NAV.map((n) => (
              <Link key={n.href} href={n.href} className={path?.startsWith(n.href) ? "on" : ""} title={n.label}>
                <span className="ic"><Icon name={n.icon} size={21} /></span>
                <span className="lbl">{n.label}</span>
              </Link>
            ))}
          </nav>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <button className="mob-menu" aria-label="Menyu" onClick={() => setOpen((v) => !v)}>
              <Icon name="menu" size={24} />
            </button>
            <span className="portal-name">Mening hujjatlarim — MyGov moduli</span>
            <span className="proto">Prototip</span>
          </div>
          <div className="topbar-actions">
            {/* TODO(Разработчик 3): переключатель uz/ru (next-intl) */}
            <span className="lang hide-sm">O&apos;z<Icon name="cdown" size={18} /></span>
            <span className="sep" />
            <span className="hide-sm" style={{ color: "var(--blue)" }}><Icon name="access" size={24} /></span>
            <button className="btn-login" onClick={() => api.POST("/auth/logout").then(() => (location.href = "/login"))}>
              <span className="bi">{initials(name)}</span>
              Chiqish
            </button>
          </div>
        </header>
        {children}
        <div className="foot">
          Bu — <b>prototip</b>: MyGov ichidagi «Mening hujjatlarim» moduli. Haqiqiy davlat portali emas.
        </div>
      </main>
      <div className="scrim" onClick={() => setOpen(false)} />
    </div>
  );
}
