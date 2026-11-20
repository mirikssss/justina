import type { ReactNode } from "react";

import { Icon, type IconName } from "./Icon";

export function Card({ title, icon, tag, className = "", children }:
  { title?: ReactNode; icon?: IconName; tag?: ReactNode; className?: string; children: ReactNode }) {
  return (
    <section className={`card ${className}`}>
      {title ? (
        <div className="ch">
          {icon ? <Icon name={icon} /> : null}
          <h3>{title}</h3>
          {tag ? <span className="tagai">{tag}</span> : null}
        </div>
      ) : null}
      {children}
    </section>
  );
}
