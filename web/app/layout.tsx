import type { Metadata } from "next";
import { cookies } from "next/headers";
import type { ReactNode } from "react";

import "./globals.css";
import { LANG_COOKIE, parseLang } from "@/lib/lang";

import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Mening hujjatlarim · MyGov moduli prototipi",
  description: "Сторож сделок: все документы на ваше имя из госреестров",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  // Язык интерфейса из cookie (по умолчанию узбекский) — страница сразу рендерится на нём, без мигания.
  const lang = parseLang((await cookies()).get(LANG_COOKIE)?.value);
  return (
    <html lang={lang}>
      <head>
        {/* Шрифт портала — Montserrat (500/600/700) */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap" />
      </head>
      <body>
        <Providers lang={lang}>{children}</Providers>
      </body>
    </html>
  );
}
