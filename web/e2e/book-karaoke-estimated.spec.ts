import { expect, test } from "@playwright/test";

import { API_URL, ensureReadyBook, resetReadingState } from "./helpers";

test("el karaoke también sigue timings estimados de Piper", async ({ page, playwright }) => {
  const api = await playwright.request.newContext({ baseURL: API_URL });
  const book = await ensureReadyBook(api, "e2e-book.epub", "Libro E2E");
  await resetReadingState(api, book.id);
  await api.put("/api/settings", { data: { auto_scroll: true } });
  await api.put(`/api/books/${book.id}/preferences`, {
    data: { reader_mode: "book", reader_size: 24, book_karaoke: true },
  });
  await api.dispose();

  await page.route(`**/api/books/${book.id}/chapters/1`, async (route) => {
    const response = await route.fetch();
    const payload = await response.json();
    if (payload.timing) {
      payload.timing.precision = "estimated";
      for (const segment of payload.timing.segments) {
        segment.precision = "estimated";
      }
    }
    await route.fulfill({ response, json: payload });
  });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/#/books/${book.id}/read`);
  await page.getByRole("button", { name: "Libro", exact: true }).click();
  await expect(page.locator(".book-page:visible").first()).toBeVisible();
  await page.getByRole("button", { name: "Reproducir" }).click();

  const active = page.locator(".book-word.is-active").first();
  await expect(active).toBeVisible({ timeout: 10_000 });
  const first = await active.textContent();
  await expect.poll(() => active.textContent(), { timeout: 8_000 }).not.toBe(first);
});
