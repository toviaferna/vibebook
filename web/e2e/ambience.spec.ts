import { expect, test } from "@playwright/test";

import { API_URL, ensureImportedBook } from "./helpers";

function wavBuffer(seconds = 0.5, frequency = 440): Buffer {
  const rate = 24_000;
  const samples = Math.floor(seconds * rate);
  const buffer = Buffer.alloc(44 + samples * 2);
  buffer.write("RIFF", 0);
  buffer.writeUInt32LE(36 + samples * 2, 4);
  buffer.write("WAVE", 8);
  buffer.write("fmt ", 12);
  buffer.writeUInt32LE(16, 16);
  buffer.writeUInt16LE(1, 20);
  buffer.writeUInt16LE(1, 22);
  buffer.writeUInt32LE(rate, 24);
  buffer.writeUInt32LE(rate * 2, 28);
  buffer.writeUInt16LE(2, 32);
  buffer.writeUInt16LE(16, 34);
  buffer.write("data", 36);
  buffer.writeUInt32LE(samples * 2, 40);
  for (let index = 0; index < samples; index += 1) {
    const value = Math.round(8_000 * Math.sin((2 * Math.PI * frequency * index) / rate));
    buffer.writeInt16LE(value, 44 + index * 2);
  }
  return buffer;
}

test("analiza un plan y activa el ambiente del lector", async ({ page, playwright }) => {
  const api = await playwright.request.newContext({ baseURL: API_URL });
  const book = await ensureImportedBook(api, "e2e-reader.epub", "Ambiente E2E");

  const assetResponse = await api.post("/api/ambience/assets/import", {
    multipart: {
      file: {
        name: "rain-bed.wav",
        mimeType: "audio/wav",
        buffer: wavBuffer(),
      },
      prompt: "rain bed e2e",
      kind: "ambience",
      tags: "rain,loop",
      license: "CC0-1.0",
      loopable: "true",
    },
  });
  expect(assetResponse.ok()).toBeTruthy();
  const asset = (await assetResponse.json()) as { id: string };

  const planResponse = await api.put(`/api/books/${book.id}/ambience`, {
    data: {
      settings: { enabled: false, master_gain_db: -18, ducking_db: -12 },
      plan: {
        version: 1,
        chapters: [
          {
            chapter_index: 1,
            bed: {
              asset_id: asset.id,
              kind: "ambience",
              start_ms: 0,
              end_ms: null,
              loop: true,
              gain_db: -24,
              fade_in_ms: 1500,
              fade_out_ms: 2000,
              confidence: 0.8,
              reason: "lluvia de prueba",
            },
            effects: [],
          },
        ],
      },
    },
  });
  expect(planResponse.ok()).toBeTruthy();
  await api.dispose();

  await page.goto(`/#/books/${book.id}`);
  await expect(page.getByText("1 capítulo con plan")).toBeVisible();

  await page.goto(`/#/books/${book.id}/read`);
  await expect(page.getByRole("heading", { name: "Capítulo 1" })).toBeVisible();
  const toggle = page.getByRole("button", { name: "Activar ambiente" });
  await expect(toggle).toBeVisible();
  await toggle.click();

  await expect(page.getByRole("button", { name: "Apagar ambiente" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(page.locator(".reader-ambience")).toContainText("lluvia de prueba");
});
