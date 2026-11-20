type Tone = "good" | "warn" | "crit" | "info" | "muted";

const TONES: Record<Tone, string> = {
  good: "bg-good-bg text-good",
  warn: "bg-warn-bg text-warn",
  crit: "bg-crit-bg text-crit",
  info: "bg-info-bg text-accent",
  muted: "bg-surface-2 text-muted",
};

export function Badge({ tone = "muted", children }: { tone?: Tone; children: React.ReactNode }) {
  return <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${TONES[tone]}`}>{children}</span>;
}
