import { Icon, type IconName } from "@/components/mygov";

// Разработчик 3: тревоги по документу (GET /guard/documents/{id}/alerts), «Bu men emasman — bekor qilish»
// (POST /guard/actions -> код в Telegram -> модалка), «Ariza (31-modda)» (POST /guard/drafts).
// Вид перенесён из макета; кнопки пока не подключены.
const ACTS: { cls: string; icon: IconName; title: string; hint: string; forPoa?: boolean }[] = [
  { cls: "danger", icon: "x", title: "Bu men emasman", hint: "Ishonchnomani bekor qilish", forPoa: true },
  { cls: "warnc", icon: "block", title: "Pauza (31-modda)", hint: "Notariusga ariza" },
  { cls: "infoc", icon: "file2", title: "Da'vo arizasi", hint: "Sudga qoralama" },
  { cls: "okc", icon: "check2", title: "Bu men", hint: "Men amalga oshirdim" },
];

export function DocumentGuard({ documentId, status }: { documentId: string; status?: string }) {
  return (
    <section className="card actbar" data-document-id={documentId}>
      <h3>Yuridik himoya</h3>
      <div className="note">Hujjat bo'yicha tezkor choralar. Har bir harakat Telegram kodi bilan tasdiqlanadi.</div>
      <div className="acts">
        {ACTS.map((a) => (
          <button key={a.title} type="button" className={`act ${a.cls}`} disabled={status !== "active" && a.forPoa}>
            <span className="ai2"><Icon name={a.icon} /></span>
            <div>{a.title}<small>{a.hint}</small></div>
          </button>
        ))}
      </div>
    </section>
  );
}
