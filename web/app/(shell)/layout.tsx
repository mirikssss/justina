import type { ReactNode } from "react";

import { Shell, Toaster } from "@/components/mygov";
import { ConsentGate, DeleteMyData } from "@/features/platform";

// Каркас (Разработчик 3). Все страницы кабинета лежат внутри (shell)/ и получают шапку и меню.
export default function ShellLayout({ children }: { children: ReactNode }) {
  return (
    <Shell>
      {children}
      <DeleteMyData />
      <ConsentGate />
      <Toaster />
    </Shell>
  );
}
