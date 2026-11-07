import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";

import { sampleBook, sampleBookDetail, sampleJob, sampleSettings, sampleVoices } from "./fixtures";

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
