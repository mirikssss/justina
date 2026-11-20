import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Mening hujjatlarim · MyGov moduli prototipi",
  description: "Сторож сделок: все документы на ваше имя из госреестров",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="uz">
      <head>
        {/* Шрифт портала — Montserrat (500/600/700) */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap" />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
