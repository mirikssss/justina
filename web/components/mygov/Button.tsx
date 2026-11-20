import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-accent text-white hover:opacity-90",
  secondary: "border border-border bg-surface hover:bg-surface-2",
  danger: "bg-crit text-white hover:opacity-90",
};

export function Button({ variant = "primary", className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return <button type="button" className={`rounded-ctl px-4 py-2 text-sm font-medium disabled:opacity-50 ${VARIANTS[variant]} ${className}`} {...props} />;
}
