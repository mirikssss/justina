"use client";

import { Icon, type IconName } from "@/components/mygov";
import { useI18n, type MessageKey } from "@/lib/i18n";

// Разработчик 3: тревоги по документу (GET /guard/documents/{id}/alerts), «Bu men emasman — bekor qilish»
// (POST /guard/actions -> код в Telegram -> модалка), «Ariza (31-modda)» (POST /guard/drafts).
// Вид перенесён из макета; кнопки пока не подключены.
const ACTS: { cls: string; icon: IconName; title: MessageKey; hint: MessageKey; forPoa?: boolean }[] = [
  { cls: "danger", icon: "x", title: "guard.not_me", hint: "guard.not_me.hint", forPoa: true },
  { cls: "warnc", icon: "block", title: "guard.pause", hint: "guard.pause.hint" },
  { cls: "infoc", icon: "file2", title: "guard.claim", hint: "guard.claim.hint" },
  { cls: "okc", icon: "check2", title: "guard.me", hint: "guard.me.hint" },
];

export function DocumentGuard({ documentId, status }: { documentId: string; status?: string }) {
  const { t } = useI18n();
  return (
    <section className="card actbar" data-document-id={documentId}>
      <h3>{t("guard.title")}</h3>
      <div className="note">{t("guard.note")}</div>
      <div className="acts">
        {ACTS.map((a) => (
          <button key={a.title} type="button" className={`act ${a.cls}`} disabled={status !== "active" && a.forPoa}>
            <span className="ai2"><Icon name={a.icon} /></span>
            <div>{t(a.title)}<small>{t(a.hint)}</small></div>
          </button>
        ))}
      </div>
    </section>
  );
}
