"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { Button, Modal } from "@/components/mygov";
import type { Schemas } from "@/lib/api/client";

import { ACTION_TYPE } from "./labels";
import { confirmAction } from "./queries";

// Шаг 2 действия (UC-G3, FR-G-08): 6-значный код из Telegram, 2 минуты, 3 попытки, потом 429.
// Модалка нарочно отдельный компонент: её же нельзя встроить в iframe (NFR-G-05).
function secondsLeft(iso?: string | null): number {
  if (!iso) return 0;
  return Math.max(0, Math.round((new Date(iso).getTime() - Date.now()) / 1000));
}

export function ConfirmModal({ action, onClose, onConfirmed }:
  { action: Schemas["Action"]; onClose: () => void; onConfirmed: (a: Schemas["Action"]) => void }) {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [left, setLeft] = useState(() => secondsLeft(action.confirm_expires_at));
  const [attempts, setAttempts] = useState(action.attempts_left ?? 3);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => inputRef.current?.focus(), []);
  useEffect(() => {
    const t = setInterval(() => setLeft(secondsLeft(action.confirm_expires_at)), 1000);
    return () => clearInterval(t);
  }, [action.confirm_expires_at]);

  const expired = left <= 0;
  const blocked = attempts <= 0 || expired || busy;
  const mmss = useMemo(() => {
    const m = Math.floor(left / 60), s = left % 60;
    return `${m}:${String(s).padStart(2, "0")}`;
  }, [left]);

  async function submit() {
    if (code.length !== 6 || blocked) return;
    setBusy(true);
    setErr(null);
    try {
      const { action: updated, status } = await confirmAction(action.id, code);
      if (updated) {
        onConfirmed(updated);
        router.push(`/actions/${updated.id}`);
        onClose();
        return;
      }
      if (status === 429) {
        setAttempts(0);
        setErr("Urinishlar tugadi. Yangi harakat so'rang.");
      } else {
        setAttempts((a) => Math.max(0, a - 1));
        setErr("Kod noto'g'ri. Qaytadan kiriting.");
      }
      setCode("");
      inputRef.current?.focus();
    } catch {
      setErr("Tarmoq xatosi. Qaytadan urinib ko'ring.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      title="Tasdiqlash kodi"
      onClose={onClose}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Bekor qilish</Button>
          <Button onClick={submit} disabled={code.length !== 6 || blocked}>
            {busy ? "Tekshirilmoqda…" : "Tasdiqlash"}
          </Button>
        </>
      }
    >
      <p className="note" style={{ marginBottom: 14 }}>
        <b>{ACTION_TYPE[action.type]}</b>. Telegramga yuborilgan 6 xonali kodni kiriting.
      </p>
      <input
        ref={inputRef}
        className="code-in"
        inputMode="numeric"
        autoComplete="one-time-code"
        aria-label="Tasdiqlash kodi"
        maxLength={6}
        value={code}
        disabled={attempts <= 0 || expired}
        onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
        onKeyDown={(e) => e.key === "Enter" && submit()}
        placeholder="______"
      />
      <div className="code-meta">
        <span className={expired ? "count err" : "count"}>
          {expired ? "Muddati tugadi" : `Kod amal qiladi: ${mmss}`}
        </span>
        <span className="count">Urinishlar: {Math.max(0, attempts)}/3</span>
      </div>
      {err ? <div className="err" style={{ marginTop: 12 }}>{err}</div> : null}
    </Modal>
  );
}
