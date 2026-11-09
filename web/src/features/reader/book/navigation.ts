export type PageDirection = "next" | "prev";

export type PageMove =
  | { kind: "page"; index: number }
  | { kind: "chapter"; direction: PageDirection }
  | { kind: "none" };

interface ResolvePageMoveInput {
  pageIndex: number;
  pageCount: number;
  spread: boolean;
  direction: PageDirection;
  hasNextChapter?: boolean;
  hasPreviousChapter?: boolean;
}

export function resolvePageMove({
  pageIndex,
  pageCount,
  spread,
  direction,
  hasNextChapter = false,
  hasPreviousChapter = false,
}: ResolvePageMoveInput): PageMove {
  if (pageCount <= 0) {
    return { kind: "none" };
  }
  const step = spread ? 2 : 1;
  const lastPage = Math.max(0, pageCount - step);
  const target =
    direction === "next" ? Math.min(lastPage, pageIndex + step) : Math.max(0, pageIndex - step);

  if (target !== pageIndex) {
    return { kind: "page", index: target };
  }
  if (direction === "next" && hasNextChapter) {
    return { kind: "chapter", direction: "next" };
  }
  if (direction === "prev" && hasPreviousChapter) {
    return { kind: "chapter", direction: "prev" };
  }
  return { kind: "none" };
}

export function formatPageLabel(pageIndex: number, pageCount: number, spread: boolean): string {
  if (pageCount <= 0) {
    return "—";
  }
  const visible = spread ? Math.min(2, pageCount - pageIndex) : 1;
  if (visible > 1) {
    return `Páginas ${pageIndex + 1}–${pageIndex + visible} de ${pageCount}`;
  }
  return `Página ${pageIndex + 1} de ${pageCount}`;
}
