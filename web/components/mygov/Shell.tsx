import Link from "next/link";
import type { ReactNode } from "react";

// Герб и логотип MyGov не копируем: на их месте — текстовая подпись прототипа.
const NAV = [
  { href: "/documents", label: "Hujjatlarim" },
  { href: "/alerts", label: "Ogohlantirishlar" },
  { href: "/sources", label: "Manbalar" },
  { href: "/family", label: "Oila" },
];

export function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="flex h-14 items-center justify-between border-b border-border bg-surface px-6">
        <Link href="/documents" className="font-semibold">
          Мои документы <span className="font-normal text-muted">· прототип модуля MyGov</span>
        </Link>
        <div className="flex items-center gap-4 text-sm text-muted">
          <span>uz | ru</span>
        </div>
      </header>
      <div className="mx-auto flex max-w-6xl gap-6 px-6 py-6">
        <nav className="w-52 shrink-0 space-y-1">
          {NAV.map((n) => (
            <Link key={n.href} href={n.href} className="block rounded-ctl px-3 py-2 text-sm hover:bg-surface-2">
              {n.label}
            </Link>
          ))}
        </nav>
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
