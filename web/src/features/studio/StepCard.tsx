import clsx from "clsx";
import type { ReactNode } from "react";

interface StepCardProps {
  number: number;
  title: string;
  description?: string;
  active?: boolean;
  locked?: boolean;
  status?: ReactNode;
  children?: ReactNode;
}

export function StepCard({
  number,
  title,
  description,
  active,
  locked,
  status,
  children,
}: StepCardProps) {
  return (
    <section
      className={clsx("step-card", active && "is-active", locked && "is-locked")}
      aria-disabled={locked || undefined}
    >
      <div className="step-number" aria-hidden="true">
        {String(number).padStart(2, "0")}
      </div>
      <div className="step-content">
        <div className="step-head">
          <div>
            <h2>{title}</h2>
            {description ? <p>{description}</p> : null}
          </div>
          {status}
        </div>
        {children ? <div className="step-body">{children}</div> : null}
      </div>
    </section>
  );
}
