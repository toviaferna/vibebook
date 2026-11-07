import clsx from "clsx";

import { formatStatus } from "../lib/format";

export function StatusChip({ status }: { status: string }) {
  return (
    <span className={clsx("status-chip", `status-chip--${status}`)}>{formatStatus(status)}</span>
  );
}
