import type { ManifestChapter } from "../../api/types";

export function chapterDisplayTitle(
  chapter: Pick<ManifestChapter, "title" | "number" | "generated_title">,
): string {
  const title = chapter.title.trim();
  if (!title) {
    return chapter.number ? `Capítulo ${chapter.number}` : "Capítulo";
  }
  if (chapter.number !== null && chapter.number !== undefined && /^\d+$/.test(title)) {
    return `Capítulo ${chapter.number}`;
  }
  return title;
}
