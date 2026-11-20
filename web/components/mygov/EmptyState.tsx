export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="empty">
      <b>{title}</b>
      {hint}
    </div>
  );
}

export function Skeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="doclist">
      {Array.from({ length: rows }, (_, i) => <div key={i} className="skel" />)}
    </div>
  );
}
