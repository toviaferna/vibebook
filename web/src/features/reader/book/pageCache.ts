import type { ManifestChapter, ManifestImage } from "../../../api/types";
import type { BookPage } from "./paginator";

const MAX_CACHE = 8;
const cache = new Map<string, BookPage[]>();

export function hashString(value: string): string {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(36);
}

export function chapterSignature(chapter: ManifestChapter, images: ManifestImage[] = []): string {
  const segments = chapter.segments
    .map((segment) => `${segment.id}\u0000${segment.text}`)
    .join("\u0001");
  const figures = images
    .filter((image) => image.chapter_index === chapter.index)
    .map(
      (image) =>
        `${image.id}\u0000${image.position}\u0000${image.caption ?? ""}\u0000${image.width ?? ""}\u0000${image.height ?? ""}`,
    )
    .join("\u0001");
  return hashString(`${chapter.index}\u0002${segments}\u0002${figures}`);
}

export function pageCacheKey(input: {
  bookId: string;
  chapter: ManifestChapter;
  images?: ManifestImage[];
  width: number;
  height: number;
  font: string;
  size: number;
  album: boolean;
}): string {
  const signature = chapterSignature(input.chapter, input.images ?? []);
  return `${input.bookId}:${signature}:${Math.round(input.width)}:${Math.round(input.height)}:${input.font}:${input.size}:${input.album ? "album" : "book"}`;
}

export function getCachedPages(key: string): BookPage[] | undefined {
  const pages = cache.get(key);
  if (pages) {
    cache.delete(key);
    cache.set(key, pages);
  }
  return pages;
}

export function setCachedPages(key: string, pages: BookPage[]): void {
  cache.set(key, pages);
  while (cache.size > MAX_CACHE) {
    const first = cache.keys().next().value;
    if (first === undefined) break;
    cache.delete(first);
  }
}

export function clearPageCache(bookId?: string): void {
  if (!bookId) {
    cache.clear();
    return;
  }
  const prefix = `${bookId}:`;
  for (const key of cache.keys()) {
    if (key.startsWith(prefix)) {
      cache.delete(key);
    }
  }
}
