import type { ReactNode } from "react";

export function Chips<T extends string>({ value, options, onChange }:
  { value: T; options: { value: T; label: ReactNode }[]; onChange: (v: T) => void }) {
  return (
    <div className="filters">
      {options.map((o) => (
        <button key={o.value} type="button" className={`chip${o.value === value ? " on" : ""}`} onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}
