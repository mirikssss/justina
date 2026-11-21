"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

// Публичный просмотр: замаскированный документ по временной ссылке, без входа. Ничего, кроме того, что видно в ленте владельца.
type Shared = { document: Record<string, any>; versions_count: number; shared_until: string; note: string };

export default function SharedPage() {
  const { token } = useParams<{ token: string }>();
  const [data, setData] = useState<Shared | null>(null);
  const [state, setState] = useState<"loading" | "ok" | "gone">("loading");
  useEffect(() => {
    fetch(`/api/public/shared/${encodeURIComponent(token)}`)
      .then(async (r) => { if (!r.ok) throw new Error("gone"); setData(await r.json()); setState("ok"); })
      .catch(() => setState("gone"));
  }, [token]);
  const d = data?.document;
  const parties = (d?.parties ?? []) as { role: string; name_masked: string }[];
  return (
    <main style={{ maxWidth: 640, margin: "48px auto", padding: "0 16px", fontFamily: "Montserrat, system-ui, sans-serif" }}>
      <div style={{ background: "#fef3c7", padding: "6px 12px", borderRadius: 8, fontSize: 12, display: "inline-block" }}>Prototip · Justina</div>
      {state === "loading" ? <p>…</p> : null}
      {state === "gone" ? <h1 style={{ fontSize: 22 }}>Ссылка недействительна · Havola yaroqsiz</h1> : null}
      {d ? (
        <>
          <h1 style={{ fontSize: 24, marginBottom: 4 }}>{d.title}</h1>
          <p style={{ color: "#555", marginTop: 0 }}>{d.uri}</p>
          <dl style={{ display: "grid", gridTemplateColumns: "180px 1fr", gap: "8px 16px" }}>
            <dt>Статус / Holat</dt><dd>{d.status}</dd>
            <dt>Вид / Turi</dt><dd>{d.kind}</dd>
            <dt>Выдан / Berilgan</dt><dd>{d.issued_at ?? "—"}</dd>
            <dt>Действует до / Muddati</dt><dd>{d.valid_until ?? "—"}</dd>
            {d.object ? <><dt>Объект / Obyekt</dt><dd>{[d.object.label, d.object.id_masked].filter(Boolean).join(" · ")}</dd></> : null}
            {parties.map((p) => <><dt key={`a${p.role}`}>{p.role}</dt><dd key={`b${p.role}`}>{p.name_masked}</dd></>)}
            <dt>Версий / Versiyalar</dt><dd>{data?.versions_count}</dd>
          </dl>
          <p style={{ color: "#555", fontSize: 13 }}>{data?.note} До / gacha: {data?.shared_until?.slice(0, 16).replace("T", " ")}</p>
        </>
      ) : null}
    </main>
  );
}
