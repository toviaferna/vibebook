import type { ReactNode } from "react";

interface FieldProps {
  label: string;
  htmlFor?: string;
  hint?: string;
  error?: string;
  children: ReactNode;
}

export function Field({ label, htmlFor, hint, error, children }: FieldProps) {
  return (
    <div className="field">
      <label className="label" htmlFor={htmlFor}>
        {label}
      </label>
      {children}
      {error ? <p className="error-text">{error}</p> : null}
      {!error && hint ? <p className="hint">{hint}</p> : null}
    </div>
  );
}
