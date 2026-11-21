"use client";

import { useEffect, useRef, type ReactNode } from "react";

import { Icon } from "./Icon";

// Модалка кита (Разработчик 3). Используется для подтверждения действия (FR-G-14).
// NFR-G-05: модалку нельзя встроить в чужую страницу — это обеспечивает CSP frame-ancestors 'none'
// на уровне заголовков (next.config.mjs), здесь — доступность: Esc, фокус, клик по фону.
export function Modal({ title, onClose, children, footer }:
  { title: ReactNode; onClose: () => void; children: ReactNode; footer?: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    ref.current?.focus();
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  return (
    <div className="modal-ov" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={typeof title === "string" ? title : undefined}
        tabIndex={-1} ref={ref}>
        <div className="modal-h">
          <h3>{title}</h3>
          <button type="button" className="modal-x" aria-label="Yopish" onClick={onClose}><Icon name="x" size={20} /></button>
        </div>
        <div className="modal-b">{children}</div>
        {footer ? <div className="modal-f">{footer}</div> : null}
      </div>
    </div>
  );
}
