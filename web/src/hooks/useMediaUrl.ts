import { useEffect, useState } from "react";

import { mediaUrl } from "../api/media";

export function useMediaUrl(
  bookId: string | null | undefined,
  kind: string,
  path: string | null | undefined,
): string | undefined {
  const [url, setUrl] = useState<string>();

  useEffect(() => {
    let cancelled = false;
    if (!bookId || !path) {
      setUrl(undefined);
      return;
    }
    void mediaUrl(bookId, kind, path)
      .then((next) => {
        if (!cancelled) {
          setUrl(next);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setUrl(undefined);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [bookId, kind, path]);

  return url;
}
