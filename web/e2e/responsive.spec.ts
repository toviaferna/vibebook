import { expect, test } from "@playwright/test";

import { API_URL, ensureReadyBook, resetReadingState } from "./helpers";

const viewports = [
  { width: 1920, height: 1080 },
  { width: 1366, height: 768 },
  { width: 1280, height: 720 },
  { width: 1024, height: 768 },
  { width: 768, height: 1024 },
  { width: 390, height: 844 },
];

test("el lector y la biblioteca caben en 720p, 768p, 1080p y mobile", async ({
  page,
  playwright,
}) => {
  const api = await playwright.request.newContext({ baseURL: API_URL });
  const book = await ensureReadyBook(api, "e2e-reader.epub", "Lector E2E");
  await resetReadingState(api, book.id);
  await api.dispose();

  for (const viewport of viewports) {
    const label = `${viewport.width}x${viewport.height}`;
    await page.setViewportSize(viewport);

    await page.goto("/#/");
    await expect(page.getByRole("heading", { name: "Tu biblioteca" })).toBeVisible();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1),
      `biblioteca sin overflow horizontal en ${label}`,
    ).toBe(true);

    await page.goto(`/#/books/${book.id}/read`);
    await page.getByRole("button", { name: "Libro", exact: true }).click();
    await expect(page.getByRole("region", { name: /Lectura de/ })).toBeVisible();
    await page.waitForTimeout(350);

    const geometry = await page.evaluate(() => {
      const rect = (selector: string) => document.querySelector(selector)?.getBoundingClientRect();
      const pageRect = rect(".book-page");
      const nav = rect(".book-nav");
      const player = rect(".reader-player");
      return {
        overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
        pageBottom: pageRect?.bottom ?? 0,
        navTop: nav?.top ?? 0,
        navBottom: nav?.bottom ?? 0,
        playerTop: player?.top ?? 0,
      };
    });

    expect(geometry.overflow, `lector sin overflow horizontal en ${label}`).toBe(false);
    expect(geometry.pageBottom, `página completa en ${label}`).toBeLessThanOrEqual(
      geometry.navTop + 1,
    );
    expect(geometry.navBottom, `navegación visible en ${label}`).toBeLessThanOrEqual(
      geometry.playerTop + 1,
    );
  }
});
