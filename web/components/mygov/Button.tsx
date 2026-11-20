import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "ghost";

export function Button({ variant = "primary", small = false, className = "", ...props }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; small?: boolean }) {
  const v = variant === "primary" ? "btn-pri" : "btn-ghost";
  return <button type="button" className={`btn ${v}${small ? " btn-sm" : ""} ${className}`} {...props} />;
}
