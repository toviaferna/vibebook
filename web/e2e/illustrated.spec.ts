import { expect, test } from "@playwright/test";

import { API_URL, ensureImportedBook } from "./helpers";

test("ilustraciones en Libro, Álbum y Texto", async ({ page, playwright }) => {
  const api = await playwright.request.newContext({ baseURL: API_URL });
  const book = await ensureImportedBook(api, "e2e-illustrated.epub", "Ilustrado E2E");
  await api.dispose();

  await page.goto(`/#/books/${book.id}/read`);
  await expect(page.getByRole("button", { name: "Libro", exact: true })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(page.locator(".book-figure img")).toBeVisible();
  await expect(page.locator(".book-figure figcaption")).toHaveText("La casa del bosque");

  await page.getByRole("button", { name: "Álbum" }).click();
  await expect(page.locator(".book-reader--album")).toBeVisible();
  await expect(page.locator(".book-figure img")).toBeVisible();

  await page.getByRole("button", { name: "Texto" }).click();
  await expect(page.locator(".reader-figure img")).toBeVisible();
  await expect(page.locator(".reader-figure figcaption")).toHaveText("La casa del bosque");
});
