"use client";

import { useSyncExternalStore } from "react";

import { Icon, type IconName } from "./Icon";

// Тост кита (Разработчик 3, FR-G-14). Один <Toaster/> в каркасе; вызов toast(...) из любого места.
export type ToastTone = "good" | "crit" | "info";
type ToastItem = { id: number; text: string; tone: ToastTone };

let items: ToastItem[] = [];
const listeners = new Set<() => void>();
let seq = 0;

function emit() {
  for (const l of listeners) l();
}

export function toast(text: string, tone: ToastTone = "good", ms = 3200) {
  const id = ++seq;
  items = [...items, { id, text, tone }];
  emit();
  setTimeout(() => {
    items = items.filter((t) => t.id !== id);
    emit();
  }, ms);
}

const ICONS: Record<ToastTone, IconName> = { good: "check2", crit: "warn", info: "info" };

export function Toaster() {
  const snapshot = useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => items,
    () => items,
  );
  if (snapshot.length === 0) return null;
  return (
    <div className="toaster" role="status" aria-live="polite">
      {snapshot.map((t) => (
        <div key={t.id} className={`toast t-${t.tone}`}>
          <Icon name={ICONS[t.tone]} size={18} />
          <span>{t.text}</span>
        </div>
      ))}
    </div>
  );
}
