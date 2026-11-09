import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { type APIRequestContext, expect } from "@playwright/test";

import type { Book } from "../src/api/types";

const here = path.dirname(fileURLToPath(import.meta.url));
const fixturesDir = path.resolve(here, "../../tests/fixtures");

export const API_URL = "http://127.0.0.1:8765";

export function fixturePath(name: string): string {
  return path.join(fixturesDir, name);
}

export async function ensureImportedBook(
  api: APIRequestContext,
  fixtureName: string,
  title: string,
): Promise<Book> {
  const listResponse = await api.get("/api/books?limit=100");
  expect(listResponse.ok()).toBeTruthy();
  const list = (await listResponse.json()) as { items: Book[] };
  const existing = list.items.find((item) => item.title === title);
  if (existing) {
    return existing;
  }

  const buffer = await fs.readFile(fixturePath(fixtureName));
  const importResponse = await api.post("/api/books/import", {
    multipart: {
      file: {
        name: fixtureName,
        mimeType: "application/epub+zip",
        buffer,
      },
    },
  });
  expect(importResponse.ok()).toBeTruthy();
  return (await importResponse.json()) as Book;
}

export async function resetReadingState(api: APIRequestContext, bookId: string): Promise<void> {
  const audio = await api.put(`/api/books/${bookId}/state`, {
    data: { position_ms: 0, chapter_index: 1, playback_rate: 1 },
  });
  expect(audio.ok()).toBeTruthy();
  const reading = await api.put(`/api/books/${bookId}/reading-state`, {
    data: {
      chapter_index: 1,
      char_offset: 0,
      page_index: 0,
      page_count: null,
      percent: 0,
    },
  });
  expect(reading.ok()).toBeTruthy();
}

export async function ensureReadyBook(
  api: APIRequestContext,
  fixtureName: string,
  title: string,
): Promise<Book> {
  const listResponse = await api.get("/api/books?limit=100");
  expect(listResponse.ok()).toBeTruthy();
  const list = (await listResponse.json()) as { items: Book[] };
  let book = list.items.find((item) => item.title === title);

  if (!book) {
    const buffer = await fs.readFile(fixturePath(fixtureName));
    const importResponse = await api.post("/api/books/import", {
      multipart: {
        file: {
          name: fixtureName,
          mimeType: "application/epub+zip",
          buffer,
        },
      },
    });
    expect(importResponse.ok()).toBeTruthy();
    book = (await importResponse.json()) as Book;
  }

  if (book.status === "ready") {
    return book;
  }

  const conversion = await api.post(`/api/books/${book.id}/convert`, {
    data: {
      voice: "es-MX-JorgeNeural",
      engine: "fake",
      style: "neutral",
      rate: "-10%",
      force: false,
    },
  });
  expect(conversion.ok()).toBeTruthy();
  const { job_id: jobId } = (await conversion.json()) as { job_id: string };

  await expect
    .poll(
      async () => {
        const response = await api.get(`/api/jobs/${jobId}`);
        if (!response.ok()) {
          return `http_${response.status()}`;
        }
        const job = (await response.json()) as { status: string };
        return job.status;
      },
      { timeout: 120_000, intervals: [500, 1_000, 2_000] },
    )
    .toBe("completed");

  const refreshed = await api.get(`/api/books/${book.id}`);
  expect(refreshed.ok()).toBeTruthy();
  return (await refreshed.json()) as Book;
}
