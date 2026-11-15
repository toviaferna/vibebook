export type ReaderView = "book" | "album" | "text" | "original";

const DESKTOP_QUERY = "(min-width: 981px)";

/** The realistic book is the default where there is room for a spread. */
export function isDesktopReader(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia(DESKTOP_QUERY).matches
  );
}

export function defaultReaderView(): "book" | "text" {
  return isDesktopReader() ? "book" : "text";
}
