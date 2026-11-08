import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";

import {
  sampleBook,
  sampleBookDetail,
  sampleBookmarks,
  sampleChapter,
  sampleJob,
  sampleManifest,
  sampleSearch,
  sampleSettings,
  sampleVoices,
} from "./fixtures";

export const server = setupServer(
  http.get("*/api/books", () =>
    HttpResponse.json({
      items: [sampleBook],
      total: 1,
      limit: 100,
      offset: 0,
    }),
  ),
  http.get("*/api/books/:id", () => HttpResponse.json(sampleBookDetail)),
  http.get("*/api/books/:id/manifest", () => HttpResponse.json(sampleManifest)),
  http.get("*/api/books/:id/chapters/:index", () => HttpResponse.json(sampleChapter)),
  http.get("*/api/books/:id/search", ({ request }) => {
    const query = new URL(request.url).searchParams.get("q") ?? "";
    return HttpResponse.json(query.trim().length >= 2 ? sampleSearch : { items: [] });
  }),
  http.get("*/api/books/:id/bookmarks", () => HttpResponse.json(sampleBookmarks)),
  http.post("*/api/books/:id/bookmarks", async ({ request }) => {
    const input = (await request.json()) as {
      chapter_index: number;
      position_ms: number;
      note?: string | null;
    };
    return HttpResponse.json(
      {
        id: 2,
        book_id: sampleBook.id,
        chapter_index: input.chapter_index,
        position_ms: input.position_ms,
        note: input.note ?? null,
        created_at: "2026-11-07T10:00:00+00:00",
      },
      { status: 201 },
    );
  }),
  http.delete(
    "*/api/books/:id/bookmarks/:bookmarkId",
    () => new HttpResponse(null, { status: 204 }),
  ),
  http.get("*/api/books/:id/state", () => HttpResponse.json(sampleBookDetail.state)),
  http.put("*/api/books/:id/state", async ({ request }) => {
    const patch = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ ...sampleBookDetail.state, ...patch });
  }),
  http.get("*/api/settings", () => HttpResponse.json(sampleSettings)),
  http.put("*/api/settings", async ({ request }) => {
    const patch = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ ...sampleSettings, ...patch });
  }),
  http.get("*/api/voices", () => HttpResponse.json(sampleVoices)),
  http.post("*/api/books/import", () =>
    HttpResponse.json({ ...sampleBook, status: "imported", duration_ms: null }, { status: 201 }),
  ),
  http.post("*/api/books/:id/convert", () =>
    HttpResponse.json({ job_id: "job_1" }, { status: 202 }),
  ),
  http.get("*/api/jobs/job_1", () => HttpResponse.json(sampleJob)),
  http.delete("*/api/books/:id", () => new HttpResponse(null, { status: 204 })),
  http.post("*/api/books/rescan", () => HttpResponse.json({ count: 1 })),
);
