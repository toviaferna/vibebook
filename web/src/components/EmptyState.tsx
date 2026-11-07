import { BookOpen } from "lucide-react";
import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description: string;
  action?: ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <section className="empty-state">
      <div className="empty-mark" aria-hidden="true">
        <BookOpen size={30} strokeWidth={1.5} />
      </div>
      <h2>{title}</h2>
      <p>{description}</p>
      {action}
    </section>
  );
}
