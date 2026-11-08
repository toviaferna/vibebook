import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";

import {
  sampleBook,
  sampleBookDetail,
  sampleBookmarks,
  sampleChapter,
  sampleEngines,
  sampleJob,
  sampleManifest,
  samplePlugin,
  samplePlugins,
  sampleReadingBookmarks,
  sampleReadingState,
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
  http.get("*/api/books/:id/reading-state", () => HttpResponse.json(sampleReadingState)),
  http.put("*/api/books/:id/reading-state", async ({ request }) => {
    const patch = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ ...sampleReadingState, ...patch });
  }),
  http.get("*/api/books/:id/reading-bookmarks", () => HttpResponse.json(sampleReadingBookmarks)),
  http.post("*/api/books/:id/reading-bookmarks", async ({ request }) => {
    const input = (await request.json()) as {
      chapter_index: number;
      char_offset: number;
      page_index: number;
      note?: string | null;
    };
    return HttpResponse.json(
      {
        id: 2,
        book_id: sampleBook.id,
        chapter_index: input.chapter_index,
        char_offset: input.char_offset,
        page_index: input.page_index,
        note: input.note ?? null,
        created_at: "2026-11-07T10:00:00+00:00",
      },
      { status: 201 },
    );
  }),
  http.delete(
    "*/api/books/:id/reading-bookmarks/:bookmarkId",
    () => new HttpResponse(null, { status: 204 }),
  ),
  http.get("*/api/books/:id/preferences", () =>
    HttpResponse.json({
      book_id: sampleBook.id,
      reader_mode: null,
      reader_palette: null,
      reader_font: null,
      reader_size: null,
      page_turn: null,
      ambience_enabled: null,
      updated_at: null,
    }),
  ),
  http.put("*/api/books/:id/preferences", async ({ request }) => {
    const patch = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ book_id: sampleBook.id, ...patch, updated_at: null });
  }),
  http.get("*/api/settings", () => HttpResponse.json(sampleSettings)),
  http.put("*/api/settings", async ({ request }) => {
    const patch = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ ...sampleSettings, ...patch });
  }),
  http.get("*/api/engines", () => HttpResponse.json(sampleEngines)),
  http.get("*/api/engines/plugins", () => HttpResponse.json(samplePlugins)),
  http.post("*/api/engines/plugins", () => HttpResponse.json(samplePlugin, { status: 201 })),
  http.delete("*/api/engines/plugins/:pluginId", () => new HttpResponse(null, { status: 204 })),
  http.post("*/api/engines/:pluginId/test", () =>
    HttpResponse.json({
      ok: true,
      latency_ms: 120,
      voice_count: 1,
      message: "Plugin disponible y síntesis correcta.",
    }),
  ),
  http.put("*/api/engines/:pluginId/config", async ({ request }) => {
    const patch = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ ...samplePlugin, ...patch });
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
