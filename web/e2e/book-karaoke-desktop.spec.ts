import { expect, test } from "@playwright/test";

import { API_URL, ensureReadyBook, resetReadingState } from "./helpers";

test("en 2K el karaoke sigue en ambas páginas y el audio pasa el pliego", async ({
  page,
  playwright,
}) => {
  const api = await playwright.request.newContext({ baseURL: API_URL });
  const book = await ensureReadyBook(api, "e2e-book.epub", "Libro E2E");
  await resetReadingState(api, book.id);
  await api.put("/api/settings", { data: { auto_scroll: true } });
  await api.put(`/api/books/${book.id}/preferences`, {
    data: { reader_mode: "book", reader_size: 19, book_karaoke: true },
  });
  await api.dispose();

  await page.setViewportSize({ width: 2560, height: 1440 });
  await page.goto(`/#/books/${book.id}/read`);
  await page.getByRole("button", { name: "Libro", exact: true }).click();
  await expect(page.locator(".book-page:visible").first()).toBeVisible();
  await page.waitForTimeout(600);

  const viewport = await page.locator(".book-viewport").boundingBox();
  expect(viewport?.width ?? 0).toBeGreaterThan(1_300);

  await page.getByRole("button", { name: "Reproducir" }).click();
  await expect(page.locator(".book-word.is-active").first()).toBeVisible({ timeout: 10_000 });

  const seek = async (seconds: number) => {
    await page.evaluate((value) => {
      const audio = document.querySelector("audio") as HTMLAudioElement;
      audio.currentTime = value;
      audio.dispatchEvent(new Event("seeked"));
      audio.dispatchEvent(new Event("timeupdate"));
    }, seconds);
  };

  await seek(32.5);
  const rightPageWord = page.locator(".book-word.is-active").first();
  await expect(rightPageWord).toBeVisible({ timeout: 5_000 });
  await expect
    .poll(() =>
      rightPageWord.evaluate((node) => node.closest("article")?.getAttribute("aria-label")),
    )
    .toBe("Página 2");

  await seek(85);
  const label = page.locator(".book-nav .mono");
  const firstLabel = await label.textContent();
  await expect.poll(() => label.textContent(), { timeout: 12_000 }).not.toBe(firstLabel);
  const nextWord = page.locator(".book-word.is-active").first();
  await expect(nextWord).toBeVisible({ timeout: 5_000 });
  await expect
    .poll(() => nextWord.evaluate((node) => node.closest("article")?.getAttribute("aria-label")))
    .toBe("Página 3");
});
