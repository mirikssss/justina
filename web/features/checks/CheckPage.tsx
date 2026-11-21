"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { Badge, Button, Card, EmptyState, PageHeader, type Tone } from "@/components/mygov";
import { api, type Schemas } from "@/lib/api/client";
import { useLocale, useT } from "@/lib/i18n";

type Check = Schemas["Check"];

const RISK: Record<Check["risk_level"], { label: string; tone: Tone }> = {
  low: { label: "Past xavf", tone: "good" },
  medium: { label: "O'rtacha xavf", tone: "warn" },
  high: { label: "Yuqori xavf", tone: "crit" },
  block: { label: "Bitim taqiqlanadi", tone: "crit" },
};

const field: React.CSSProperties = {
  width: "100%", background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 10,
  padding: "11px 14px", color: "var(--fg)", font: "inherit", fontSize: 14, outline: 0,
};
const label: React.CSSProperties = { display: "block", fontSize: 12, color: "var(--muted)", margin: "12px 0 4px" };

// Проверка перед сделкой (покупатель) и кабинет нотариуса — один движок POST /v1/checks.
// Решение принимают правила R1–R8; то, что мы проверить не можем, показываем прямо («Tekshirilmadi»).
export function CheckPage({ mode }: { mode: "buyer" | "notary" }) {
  const t = useT();
  const { locale } = useLocale();
  const notary = mode === "notary";
  const [poa, setPoa] = useState("");
  const [actsByPoa, setActsByPoa] = useState(true);
  const [issued, setIssued] = useState("");
  const [age, setAge] = useState("");
  const [cadastre, setCadastre] = useState("");

  const run = useMutation({
    mutationFn: async (): Promise<Check> => {
      const { data, error } = await api.POST("/v1/checks", {
        body: {
          poa_number: poa.trim(), acts_by_poa: actsByPoa,
          poa_issued_at: issued || null, seller_age: age ? Number(age) : null, cadastre_number: cadastre.trim() || null,
        },
      });
      if (error !== undefined || !data) throw new Error("xato");
      return data;
    },
  });
  const res = run.data;
  const text = (r: { text: string; text_uz: string }) => (locale === "ru" ? r.text : r.text_uz);

  return (
    <>
      <PageHeader
        title={notary ? t("Notarius kabineti") : t("Bitimdan oldin tekshirish")}
        subtitle={notary
          ? t("Ishonchnoma bo'yicha bitimni tasdiqlashdan oldin xavf qoidalari (R1–R8) bo'yicha tekshiruv")
          : t("Ishonchnoma bo'yicha mulk yoki avtomobil sotib olishdan oldin uni tekshiring")}
      />
      <div style={{ display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", alignItems: "start" }}>
        <Card title={t("So'rov")} icon="shield">
          <form onSubmit={(e) => { e.preventDefault(); if (poa.trim().length >= 3) run.mutate(); }}>
            <label style={label} htmlFor="poa">{t("Ishonchnoma raqami")}</label>
            <input id="poa" style={field} value={poa} onChange={(e) => setPoa(e.target.value)} placeholder="2026-0001234" autoComplete="off" />
            <label className="scope" style={{ display: "flex", gap: 10, margin: "14px 0 0", alignItems: "flex-start" }}>
              <input type="checkbox" checked={actsByPoa} onChange={(e) => setActsByPoa(e.target.checked)} />
              <span>{notary ? t("Sotuvchi vakil sifatida harakat qilmoqda") : t("Sotuvchi ishonchnoma bo'yicha harakat qilmoqda")}</span>
            </label>
            {notary ? (
              <>
                <label style={label} htmlFor="issued">{t("Ishonchnoma berilgan sana")}</label>
                <input id="issued" type="date" style={field} value={issued} onChange={(e) => setIssued(e.target.value)} />
                <label style={label} htmlFor="age">{t("Mulk egasining yoshi")}</label>
                <input id="age" type="number" min={0} max={130} style={field} value={age} onChange={(e) => setAge(e.target.value)} />
                <label style={label} htmlFor="cad">{t("Kadastr raqami")}</label>
                <input id="cad" style={field} value={cadastre} onChange={(e) => setCadastre(e.target.value)} placeholder="10:05:01:02:03:0017" />
              </>
            ) : null}
            <div style={{ marginTop: 16 }}>
              <Button type="submit" onClick={() => { if (poa.trim().length >= 3) run.mutate(); }} disabled={run.isPending || poa.trim().length < 3}>
                {run.isPending ? t("Tekshirilmoqda…") : t("Tekshirish")}
              </Button>
            </div>
          </form>
        </Card>

        <div style={{ display: "grid", gap: 16 }}>
          {run.isError ? <EmptyState title={t("Tekshiruv bajarilmadi")} hint={t("Keyinroq qayta urinib ko'ring")} /> : null}
          {!res && !run.isError ? <EmptyState title={t("Natija bu yerda chiqadi")} hint={t("Ishonchnoma raqamini kiriting")} /> : null}
          {res ? (
            <>
              <Card title={t("Natija")} icon="shield2" tag={<Badge tone={RISK[res.risk_level].tone}>{t(RISK[res.risk_level].label)}</Badge>}>
                {res.reasons.length === 0 ? <p>{t("Xavf belgilari topilmadi")}</p> : (
                  <ul style={{ paddingLeft: 18, margin: 0, display: "grid", gap: 8 }}>
                    {res.reasons.map((r) => (
                      <li key={r.rule}><b>{r.rule}</b> · {text(r)}</li>
                    ))}
                  </ul>
                )}
                {res.consent_required ? <p style={{ marginTop: 12 }}><Badge tone="warn">{t("MyID tasdig'i kerak")}</Badge></p> : null}
                {res.known_in_justina ? <p style={{ marginTop: 8, fontSize: 13, color: "var(--muted)" }}>{t("Ishonchnoma Justina ma'lumotlarida ham bor")}</p> : null}
              </Card>
              <Card title={t("Vakolat reyestri")} icon="layers">
                {res.registry.unavailable ? <p>{t("Reyestr hozir mavjud emas")}</p>
                  : !res.registry.found ? <p>{t("Reyestrda topilmadi")}</p> : (
                    <dl style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "4px 12px", margin: 0, fontSize: 13 }}>
                      {Object.entries(res.registry.fields).map(([k, v]) => (<><dt key={`k${k}`} style={{ color: "var(--muted)" }}>{k}</dt><dd key={`v${k}`} style={{ margin: 0 }}>{v}</dd></>))}
                    </dl>
                  )}
              </Card>
              <Card title={t("Tekshirilmadi")} icon="info">
                <ul style={{ paddingLeft: 18, margin: 0, display: "grid", gap: 6, fontSize: 13, color: "var(--muted)" }}>
                  {res.not_checked.map((n) => (<li key={n.rule}><b>{n.rule}</b> · {text(n)}</li>))}
                </ul>
              </Card>
            </>
          ) : null}
        </div>
      </div>
    </>
  );
}
