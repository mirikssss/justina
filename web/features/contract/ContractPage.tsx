"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { Badge, Button, Card, EmptyState, PageHeader, type Tone } from "@/components/mygov";
import { api, type Schemas } from "@/lib/api/client";
import { useLocale, useT } from "@/lib/i18n";

type Review = Schemas["ContractReview"];

const LEVEL: Record<string, { label: string; tone: Tone }> = {
  high: { label: "Yuqori xavf", tone: "crit" },
  medium: { label: "O'rtacha xavf", tone: "warn" },
  low: { label: "Past xavf", tone: "good" },
};

function toBase64(buf: ArrayBuffer): string {
  let s = "";
  const bytes = new Uint8Array(buf);
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(s);
}

// Проверка договора перед подписанием: текст или файл PDF/DOCX/TXT -> пояснение ИИ, риски, вопросы, нормы lex.uz.
export function ContractPage() {
  const t = useT();
  const { locale } = useLocale();
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const run = useMutation({
    mutationFn: async (): Promise<Review> => {
      const body: Schemas["ContractIn"] = { lang: locale };
      if (file) { body.filename = file.name; body.content_base64 = toBase64(await file.arrayBuffer()); } else { body.text = text; }
      const { data, error, response } = await api.POST("/assist/contract", { body });
      if (error !== undefined || !data) throw new Error(response.status === 429 ? "429" : response.status === 422 ? "422" : "err");
      return data;
    },
  });
  const r = run.data;
  const can = (file !== null || text.trim().length >= 80) && !run.isPending;
  const err = run.error?.message;

  return (
    <>
      <PageHeader title={t("Shartnomani imzolashdan oldin tekshirish")}
        subtitle={t("Shartnoma matnini kiriting yoki faylni yuklang: sun'iy intellekt shartlarni sodda tushuntiradi va xavflarni ko'rsatadi")} />
      <div style={{ display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", alignItems: "start" }}>
        <Card title={t("Shartnoma")} icon="doc">
          <textarea value={text} onChange={(e) => { setText(e.target.value); setFile(null); }} rows={12}
            placeholder={t("Shartnoma matnini shu yerga qo'ying…")}
            style={{ width: "100%", background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 10, padding: 12, color: "var(--fg)", font: "inherit", fontSize: 14, resize: "vertical" }} />
          <div style={{ margin: "12px 0", display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <label className="btn btn-ghost btn-sm" style={{ cursor: "pointer" }}>
              {t("Fayl yuklash (PDF, DOCX, TXT)")}
              <input type="file" accept=".pdf,.docx,.txt" style={{ display: "none" }}
                onChange={(e) => { setFile(e.target.files?.[0] ?? null); if (e.target.files?.[0]) setText(""); }} />
            </label>
            {file ? <small>{file.name}</small> : null}
          </div>
          <Button onClick={() => run.mutate()} disabled={!can}>{run.isPending ? t("Tahlil qilinmoqda…") : t("Tekshirish")}</Button>
          <p style={{ marginTop: 10, fontSize: 12, color: "var(--muted)" }}>
            {t("Shaxsiy ma'lumotlar (JShShIR, telefon) modelga yuborilishidan oldin yashiriladi.")}
          </p>
        </Card>

        <div style={{ display: "grid", gap: 16 }}>
          {err ? <EmptyState title={err === "429" ? t("Juda ko'p so'rov") : err === "422" ? t("Matn juda qisqa yoki fayl o'qilmadi") : t("Tahlil bajarilmadi")}
            hint={err === "429" ? t("Bir soatdan keyin urinib ko'ring") : t("Qayta urinib ko'ring")} /> : null}
          {!r && !err ? <EmptyState title={t("Natija bu yerda chiqadi")} hint={t("Shartnomani kiriting va «Tekshirish» tugmasini bosing")} /> : null}
          {r ? (
            <>
              <Card title={t("Qisqacha")} icon="info"><p style={{ margin: 0 }}>{r.summary}</p></Card>
              <Card title={t("Majburiyatlar")} icon="list">
                <ul style={{ paddingLeft: 18, margin: 0, display: "grid", gap: 6 }}>{r.obligations.map((x, i) => <li key={i}>{x}</li>)}</ul>
              </Card>
              <Card title={t("Xavflar")} icon="warn">
                <div style={{ display: "grid", gap: 10 }}>
                  {r.risks.map((x, i) => (
                    <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                      <Badge tone={LEVEL[x.level]?.tone ?? "info"}>{LEVEL[x.level] ? t(LEVEL[x.level].label) : x.level}</Badge><span>{x.text}</span>
                    </div>
                  ))}
                </div>
              </Card>
              {r.missing.length ? (
                <Card title={t("Nima yetishmaydi")} icon="block">
                  <ul style={{ paddingLeft: 18, margin: 0, display: "grid", gap: 6 }}>{r.missing.map((x, i) => <li key={i}>{x}</li>)}</ul>
                </Card>
              ) : null}
              <Card title={t("Imzolashdan oldin so'rang")} icon="help">
                <ul style={{ paddingLeft: 18, margin: 0, display: "grid", gap: 6 }}>{r.questions.map((x, i) => <li key={i}>{x}</li>)}</ul>
              </Card>
              {r.citations.length ? (
                <Card title={t("Qonunchilik")} icon="scale">
                  <div style={{ display: "grid", gap: 6, fontSize: 13 }}>
                    {r.citations.map((c) => <a key={c.url} href={c.url} target="_blank" rel="noreferrer">{c.act_title}, {c.article}</a>)}
                  </div>
                </Card>
              ) : null}
              <p style={{ fontSize: 12, color: "var(--muted)" }}>
                {r.disclaimer}{r.truncated ? ` ${t("Matn uzun bo'lgani uchun boshi tahlil qilindi.")}` : ""}
              </p>
            </>
          ) : null}
        </div>
      </div>
    </>
  );
}
