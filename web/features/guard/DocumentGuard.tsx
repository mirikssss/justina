"use client";

import { useState } from "react";

import { Badge, Icon, toast, type IconName } from "@/components/mygov";
import { API_BASE, type Schemas } from "@/lib/api/client";
import { useLocale, useT } from "@/lib/i18n";

import { ConfirmModal } from "./ConfirmModal";
import { RULE, SEVERITY, fmtAgo } from "./labels";
import { createAction, createDraft, useDocumentAlerts } from "./queries";

// FR-G-14: тревоги по документу и действия защиты (уровень 3). Вставляется в карточку документа Разработчиком 1.
// «Bu men emasman» → POST /guard/actions → код в Telegram → модалка подтверждения → страница хода действия.
// «Ariza (31-modda)» / «Da'vo» → POST /guard/drafts → PDF.
type ActDef = { key: string; cls: string; icon: IconName; title: string; hint: string };
const ACTS: ActDef[] = [
  { key: "revoke", cls: "danger", icon: "x", title: "Bu men emasman", hint: "Ishonchnomani bekor qilish" },
  { key: "art31", cls: "warnc", icon: "block", title: "Pauza (31-modda)", hint: "Notariusga ariza" },
  { key: "claim", cls: "infoc", icon: "file2", title: "Da'vo arizasi", hint: "Sudga qoralama" },
  { key: "mine", cls: "okc", icon: "check2", title: "Bu men", hint: "Men amalga oshirdim" },
];

// Для прототипа вживую исполняется только отзыв e-доверенности на авто (раздел 6 ТЗ).
const canRevoke = (status?: string) => status === "active";

export function DocumentGuard({ documentId, status }: { documentId: string; status?: string }) {
  const t = useT();
  const { locale } = useLocale();
  const alerts = useDocumentAlerts(documentId);
  const [busy, setBusy] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<Schemas["Action"] | null>(null);
  const docAlerts = alerts.data ?? [];

  async function onRevoke() {
    setBusy("revoke");
    try {
      // Idempotency-Key: повтор того же запроса не создаёт второе действие (FR-G-09, NFR-G-03).
      const key = `revoke_car_poa:${documentId}:${(crypto as Crypto).randomUUID()}`;
      const action = await createAction(documentId, "revoke_car_poa", key);
      toast(t("Tasdiqlash kodi Telegramga yuborildi"), "info");
      setConfirming(action);
    } catch {
      toast(t("Harakatni boshlab bo'lmadi. Telegram ulanganini tekshiring."), "crit");
    } finally {
      setBusy(null);
    }
  }

  async function onDraft(type: Schemas["DraftType"], key: string) {
    setBusy(key);
    try {
      const { url } = await createDraft(documentId, type);
      toast(t("Ariza qoralamasi tayyor"), "good");
      // url относительно API (/assist/drafts/{id}); окно после await режет блокировщик — тогда в этой вкладке
      const href = url.startsWith("/") ? `${API_BASE}${url}` : url;
      const w = window.open(href, "_blank");
      if (w) w.opener = null;
      else window.location.href = href;
    } catch {
      toast(t("Qoralamani yaratib bo'lmadi"), "crit");
    } finally {
      setBusy(null);
    }
  }

  function onClick(a: ActDef) {
    if (a.key === "revoke") return onRevoke();
    if (a.key === "art31") return onDraft("art31_postpone", "art31");
    if (a.key === "claim") return onDraft("court_claim", "claim");
    if (a.key === "mine") {
      toast(t("Belgilandi: bu men amalga oshirdim"), "good");
    }
  }

  return (
    <section className="card actbar" data-document-id={documentId}>
      <h3>{t("Yuridik himoya")}</h3>
      <div className="note">{t("Hujjat bo'yicha tezkor choralar. Har bir harakat Telegram kodi bilan tasdiqlanadi.")}</div>

      {docAlerts.length > 0 ? (
        <div className="guard-alerts">
          {docAlerts.map((al) => (
            <div key={al.id} className={`guard-al sev-${al.severity}`}>
              <span className={`b-${SEVERITY[al.severity].tone}`}><Icon name={SEVERITY[al.severity].icon} size={16} /></span>
              <div>
                <b>{al.title}</b>
                <small>{(RULE[al.rule_id] ? t(RULE[al.rule_id]) : al.rule_id)} · {fmtAgo(al.created_at, locale)}</small>
              </div>
              <Badge tone={SEVERITY[al.severity].tone}>{t(SEVERITY[al.severity].label)}</Badge>
            </div>
          ))}
        </div>
      ) : null}

      <div className="acts">
        {ACTS.map((a) => {
          const disabled = (a.key === "revoke" && !canRevoke(status)) || busy !== null;
          return (
            <button key={a.key} type="button" className={`act ${a.cls}`} disabled={disabled} onClick={() => onClick(a)}>
              <span className="ai2"><Icon name={a.icon} /></span>
              <div>
                {busy === a.key ? "…" : t(a.title)}
                <small>{t(a.hint)}</small>
              </div>
            </button>
          );
        })}
      </div>

      {confirming ? (
        <ConfirmModal
          action={confirming}
          onClose={() => setConfirming(null)}
          onConfirmed={() => setConfirming(null)}
        />
      ) : null}
    </section>
  );
}
