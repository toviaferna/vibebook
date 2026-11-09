import { expect, test } from "@playwright/test";

import { API_URL, ensureReadyBook, resetReadingState } from "./helpers";

test("cruza capítulos al llegar al final de la página", async ({ page, playwright }) => {
  const api = await playwright.request.newContext({ baseURL: API_URL });
  const book = await ensureReadyBook(api, "e2e-reader.epub", "Lector E2E");
  await resetReadingState(api, book.id);
  await api.dispose();

  await page.goto(`/#/books/${book.id}/read`);
  await expect(page.getByRole("heading", { name: "Capítulo 1" })).toBeVisible();
  await page.getByRole("button", { name: "Libro", exact: true }).click();
  await expect(page.getByRole("region", { name: /Lectura de/ })).toBeVisible();

  const navigation = page.getByRole("navigation", { name: "Navegación de páginas" });
  const next = navigation.getByRole("button", { name: /Siguiente/ });
  for (let step = 0; step < 12; step += 1) {
    if (await page.getByRole("heading", { name: "Capítulo 2" }).isVisible()) {
      break;
    }
    await expect(next).toBeEnabled();
    await next.click();
    await page.waitForTimeout(280);
  }
  await expect(page.getByRole("heading", { name: "Capítulo 2" })).toBeVisible();

  const previous = navigation.getByRole("button", { name: /anterior/i });
  await previous.click();
  await expect(page.getByRole("heading", { name: "Capítulo 1" })).toBeVisible();
});
