import { expect, test } from "@playwright/test";

import { API_URL, ensureImportedSample } from "./helpers";

test("el EPUB de prueba importa portada, metadatos y búsqueda de portada", async ({
  page,
  playwright,
}) => {
  const api = await playwright.request.newContext({ baseURL: API_URL });
  const book = await ensureImportedSample(api, "El mapa de las mareas");
  await api.dispose();

  expect(book.cover_url).not.toBeNull();

  await page.route(`**/api/books/${book.id}/cover/search`, async (route) => {
    await route.fulfill({
      json: {
        book_id: book.id,
        query: book.title,
        items: [
          {
            source: "Open Library",
            title: book.title,
            author: book.author,
            year: 2026,
            cover_url: "https://covers.openlibrary.org/b/id/123-L.jpg",
            preview_url: "https://covers.openlibrary.org/b/id/123-L.jpg",
            edition_url: null,
            score: 0.99,
          },
        ],
      },
    });
  });

  await page.goto(`/#/books/${book.id}`);
  const cover = page.getByRole("img", { name: `Portada de ${book.title}` });
  await expect(cover).toBeVisible();
  await expect
    .poll(() => cover.evaluate((image: HTMLImageElement) => image.naturalWidth))
    .toBeGreaterThan(0);

  await page.getByRole("button", { name: "Buscar portada" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("heading", { name: "Buscar una portada" })).toBeVisible();
  await expect(dialog.getByRole("button", { name: /Portada de El mapa/ })).toBeVisible();
});
