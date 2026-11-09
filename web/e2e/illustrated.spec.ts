import { expect, test } from "@playwright/test";

import { API_URL, ensureImportedBook } from "./helpers";

test("ilustraciones en Libro, Álbum y Texto", async ({ page, playwright }) => {
  const api = await playwright.request.newContext({ baseURL: API_URL });
  const book = await ensureImportedBook(api, "e2e-illustrated.epub", "Ilustrado E2E");
  const reset = await api.put(`/api/books/${book.id}/reading-state`, {
    data: {
      chapter_index: 1,
      char_offset: 0,
      page_index: 0,
      page_count: null,
      percent: 0,
    },
  });
  expect(reset.ok()).toBeTruthy();
  const resetState = await api.get(`/api/books/${book.id}/reading-state`);
  expect((await resetState.json()) as { page_index: number }).toMatchObject({
    page_index: 0,
    char_offset: 0,
  });
  await api.dispose();

  await page.goto(`/#/books/${book.id}/read`);
  await expect(page.getByRole("button", { name: "Libro", exact: true })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  const next = page
    .getByRole("navigation", { name: "Navegación de páginas" })
    .getByRole("button", { name: /siguiente/i });
  for (let step = 0; step < 6; step += 1) {
    const visible = await page
      .locator(".book-figure img")
      .waitFor({ state: "visible", timeout: 800 })
      .then(() => true)
      .catch(() => false);
    if (visible) {
      break;
    }
    if (!(await next.isEnabled())) {
      break;
    }
    await next.click();
    await page.waitForTimeout(300);
  }
  await expect(page.locator(".book-figure img")).toBeVisible();
  await expect(page.locator(".book-figure figcaption")).toHaveText("La casa del bosque");

  await page.getByRole("button", { name: "Guardar esta página" }).click();
  await page.getByRole("button", { name: "Marcadores de lectura" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByText("Sin nota").first()).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();

  await page.getByRole("button", { name: "Álbum" }).click();
  await expect(page.locator(".book-reader--album")).toBeVisible();
  await expect(page.locator(".book-figure img")).toBeVisible();

  await page.getByRole("button", { name: "Texto" }).click();
  await expect(page.locator(".reader-figure img")).toBeVisible();
  await expect(page.locator(".reader-figure figcaption")).toHaveText("La casa del bosque");
});
