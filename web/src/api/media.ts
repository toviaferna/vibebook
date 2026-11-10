import { apiFetch, apiUrl } from "./client";
import type { MediaTicket } from "./types";

const EXPIRY_MARGIN_MS = 30_000;
const cache = new Map<string, { url: string; expiresAt: number }>();
const pending = new Map<string, Promise<string>>();

export async function mediaUrl(bookId: string, kind: string, path: string): Promise<string> {
  const key = `${bookId}:${kind}:${path}`;
  const cached = cache.get(key);
  if (cached && cached.expiresAt > Date.now() + EXPIRY_MARGIN_MS) {
    return cached.url;
  }
  const inFlight = pending.get(key);
  if (inFlight) {
    return inFlight;
  }
  const request = apiFetch<MediaTicket>("/media/ticket", {
    method: "POST",
    body: JSON.stringify({ book_id: bookId, kind, path }),
  })
    .then((ticket) => {
      const url = apiUrl(ticket.url);
      const expiresAt = Date.parse(ticket.expires_at);
      cache.set(key, {
        url,
        expiresAt: Number.isFinite(expiresAt) ? expiresAt : Date.now(),
      });
      return url;
    })
    .finally(() => {
      pending.delete(key);
    });
  pending.set(key, request);
  return request;
}

export function clearMediaTickets(): void {
  cache.clear();
  pending.clear();
}
