import type { Book, Contents, Rendition } from "epubjs";
import { AlertTriangle } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { mediaUrl } from "../../../api/media";
import type { ManifestChapter } from "../../../api/types";

interface OriginalEpubViewProps {
  bookId: string;
  chapter: ManifestChapter;
  initialCfi?: string | null;
  onCfiChange?: (cfi: string) => void;
}

export function sanitize(contents: Contents) {
  const document = contents.document;
  document
    .querySelectorAll("script, iframe, object, embed, form, base, meta[http-equiv='refresh']")
    .forEach((element) => {
      element.remove();
    });

  for (const element of document.querySelectorAll("*")) {
    for (const attribute of [...element.attributes]) {
      if (attribute.name.startsWith("on")) {
        element.removeAttribute(attribute.name);
      } else if (/^\s*javascript:/i.test(attribute.value)) {
        element.removeAttribute(attribute.name);
      } else if (
        (attribute.name === "src" || attribute.name === "href") &&
        /^(https?:)?\/\//i.test(attribute.value)
      ) {
        element.removeAttribute(attribute.name);
      }
    }
  }

  const policy = document.createElement("meta");
  policy.httpEquiv = "Content-Security-Policy";
  policy.content =
    "default-src 'none'; img-src data: blob:; style-src 'unsafe-inline' data: blob:; font-src data: blob:;";
  document.head.appendChild(policy);

  document.addEventListener(
    "click",
    (event) => {
      const anchor = (event.target as Element | null)?.closest("a");
      if (anchor?.href && /^https?:/i.test(anchor.href)) {
        event.preventDefault();
      }
    },
    { capture: true },
  );
}

async function displayChapter(
  book: Book,
  rendition: Rendition,
  sourceHref: string | null,
  sourceFragment: string | null,
  initialCfi?: string | null,
) {
  let target: string | undefined;
  if (initialCfi) {
    try {
      await rendition.display(initialCfi);
      return;
    } catch {
      // Fall back to the manifest location below.
    }
  }
  if (sourceHref) {
    try {
      const section = book.spine.get(sourceHref);
      target = section?.href ?? sourceHref;
    } catch {
      target = sourceHref;
    }
    if (target && sourceFragment) {
      target = `${target}#${sourceFragment}`;
    }
  }
  try {
    await rendition.display(target);
  } catch {
    await rendition.display();
  }
}

export function OriginalEpubView({
  bookId,
  chapter,
  initialCfi,
  onCfiChange,
}: OriginalEpubViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const bookRef = useRef<Book | null>(null);
  const renditionRef = useRef<Rendition | null>(null);
  const lastHref = useRef<string | null | undefined>(undefined);
  const cfiChangeRef = useRef(onCfiChange);
  const initialCfiRef = useRef(initialCfi);
  cfiChangeRef.current = onCfiChange;
  initialCfiRef.current = initialCfi;
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const sourceHref = chapter.segments[0]?.source_href ?? null;
  const sourceFragment = chapter.segments[0]?.source_fragment ?? null;
  const targetKey = `${sourceHref ?? ""}#${sourceFragment ?? ""}`;

  useEffect(() => {
    let cancelled = false;
    let book: Book | null = null;
    let rendition: Rendition | null = null;
    const onRelocated = (location: { start?: { cfi?: string } }) => {
      const cfi = location.start?.cfi;
      if (cfi) {
        cfiChangeRef.current?.(cfi);
      }
    };

    async function load() {
      if (!containerRef.current) {
        return;
      }
      setStatus("loading");
      setError(null);
      try {
        const ePub = (await import("epubjs")).default;
        if (cancelled || !containerRef.current) {
          return;
        }
        book = ePub(await mediaUrl(bookId, "epub", `/api/books/${bookId}/epub`), {
          openAs: "epub",
        });
        rendition = book.renderTo(containerRef.current, {
          width: "100%",
          height: "100%",
          flow: "scrolled-doc",
          allowScriptedContent: false,
        });
        rendition.hooks.content.register(sanitize);
        rendition.on("relocated", onRelocated);
        bookRef.current = book;
        renditionRef.current = rendition;
        await book.ready;
        if (cancelled) {
          return;
        }
        setStatus("ready");
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "No se pudo abrir el EPUB.");
          setStatus("error");
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
      rendition?.off("relocated", onRelocated);
      rendition?.destroy();
      book?.destroy();
      bookRef.current = null;
      renditionRef.current = null;
      lastHref.current = undefined;
    };
  }, [bookId]);

  useEffect(() => {
    if (status !== "ready" || !bookRef.current || !renditionRef.current) {
      return;
    }
    if (lastHref.current === targetKey) {
      return;
    }
    const firstDisplay = lastHref.current === undefined;
    lastHref.current = targetKey;
    const cfi = firstDisplay ? initialCfiRef.current : null;
    void displayChapter(
      bookRef.current,
      renditionRef.current,
      sourceHref,
      sourceFragment,
      cfi,
    ).catch((displayError) => {
      setError(
        displayError instanceof Error
          ? displayError.message
          : "No se pudo mostrar este capítulo del EPUB.",
      );
      setStatus("error");
    });
  }, [sourceFragment, sourceHref, status, targetKey]);

  return (
    <section
      className="original-epub"
      data-testid="original-epub"
      data-status={status}
      aria-label={`EPUB original de ${chapter.title}`}
    >
      {status === "loading" ? (
        <div className="reader-chapter-loading">
          <span className="sr-only">Cargando EPUB original</span>
          <div className="skeleton skeleton--title" />
          <div className="skeleton" />
          <div className="skeleton" />
        </div>
      ) : null}
      {status === "error" ? (
        <div className="alert" role="alert">
          <AlertTriangle size={18} />
          <span>{error ?? "No se pudo abrir el EPUB original."}</span>
        </div>
      ) : null}
      <div
        ref={containerRef}
        className="original-epub-frame"
        style={{ visibility: status === "ready" ? "visible" : "hidden" }}
      />
    </section>
  );
}
