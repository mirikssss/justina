import type { ReactNode } from "react";

export type Tone = "good" | "warn" | "crit" | "info" | "new";

export function Badge({ tone = "info", children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`badge-s b-${tone}`}>{children}</span>;
}
