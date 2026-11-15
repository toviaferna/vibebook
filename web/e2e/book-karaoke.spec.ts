import { expect, test } from "@playwright/test";

import { API_URL, ensureReadyBook, resetReadingState } from "./helpers";

test("el karaoke sigue la palabra y pasa la página sin mover la app", async ({
  page,
  playwright,
}) => {
  const api = await playwright.request.newContext({ baseURL: API_URL });
  const book = await ensureReadyBook(api, "e2e-book.epub", "Libro E2E");
  await resetReadingState(api, book.id);
  await api.put("/api/settings", { data: { auto_scroll: true } });
  await api.put(`/api/books/${book.id}/preferences`, {
    data: { reader_size: 28, book_karaoke: true },
  });
  await api.dispose();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/#/books/${book.id}/read`);
  await page.getByRole("button", { name: "Libro", exact: true }).click();
  await expect(page.locator(".book-page:visible").first()).toBeVisible();

  await page.getByRole("button", { name: "Reproducir" }).click();
  await expect(page.locator(".book-highlight-word").first()).toBeVisible({ timeout: 10_000 });

  const pageLabel = page.locator(".book-nav .mono");
  await expect(pageLabel).toHaveText(/^Página \d+ de \d+$/);
  const firstLabel = await pageLabel.textContent();
  const geometry = () =>
    page.evaluate(() => {
      const rect = (selector: string) => {
        const node = document.querySelector(selector);
        if (!node) return null;
        const r = node.getBoundingClientRect();
        return { y: Math.round(r.y), h: Math.round(r.height) };
      };
      return {
        scrollWidth: document.documentElement.scrollWidth,
        scrollHeight: document.documentElement.scrollHeight,
        innerWidth: window.innerWidth,
        innerHeight: window.innerHeight,
        scrollY: window.scrollY,
        nav: rect(".book-nav"),
        table: rect(".book-table"),
        label: document.querySelector(".book-nav .mono")?.textContent,
      };
    });
  const before = await geometry();

  await expect.poll(async () => pageLabel.textContent(), { timeout: 30_000 }).not.toBe(firstLabel);

  const after = await geometry();
  expect(after.table).toEqual(before.table);
  expect(after.nav).toEqual(before.nav);
  expect(after.scrollWidth).toBeLessThanOrEqual(after.innerWidth + 1);
  expect(after.scrollHeight).toBe(before.scrollHeight);
  expect(after.scrollY).toBe(before.scrollY);

  await page.locator(".book-nav").getByRole("button", { name: "Página anterior" }).click();
  await expect(pageLabel).toHaveText(/^Página 1 de \d+$/);
  await page.waitForTimeout(1_500);
  await expect(pageLabel).toHaveText(/^Página 1 de \d+$/);
  await expect
    .poll(async () => pageLabel.textContent(), { timeout: 8_000 })
    .not.toMatch(/^Página 1 de \d+$/);

  const toggle = page.getByRole("button", { name: "Desactivar karaoke en el libro" });
  await expect(toggle).toHaveAttribute("aria-pressed", "true");
  await toggle.click();
  await expect(page.getByRole("button", { name: "Activar karaoke en el libro" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
  await expect(page.locator(".book-highlight-word")).toHaveCount(0);

  await page.getByRole("button", { name: "Activar karaoke en el libro" }).click();
  await expect(page.locator(".book-highlight-word").first()).toBeVisible();
});
