import type { ReactNode } from "react";

import { Shell } from "@/components/mygov";

// Каркас (Разработчик 3). Все страницы кабинета лежат внутри (shell)/ и получают шапку и меню.
export default function ShellLayout({ children }: { children: ReactNode }) {
  return <Shell>{children}</Shell>;
}
