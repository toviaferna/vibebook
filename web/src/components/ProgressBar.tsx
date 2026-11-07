import { formatPercent } from "../lib/format";

interface ProgressBarProps {
  value: number;
  label?: string;
  showLabel?: boolean;
}

export function ProgressBar({ value, label, showLabel = false }: ProgressBarProps) {
  const clamped = Math.min(1, Math.max(0, value));
  return (
    <div>
      <div
        className="progress-bar"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(clamped * 100)}
        aria-label={label ?? "Progreso"}
      >
        <span style={{ width: `${clamped * 100}%` }} />
      </div>
      {showLabel ? <span className="mono muted">{formatPercent(clamped)}</span> : null}
    </div>
  );
}
