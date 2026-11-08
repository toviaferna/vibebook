import { expect, test } from "@playwright/test";

import { API_URL, ensureReadyBook } from "./helpers";

test.afterEach(async ({ playwright }) => {
  const api = await playwright.request.newContext({ baseURL: API_URL });
  await api.put("/api/settings", {
    data: { theme_mode: "system", reader_palette: "paper" },
  });
  await api.dispose();
});

test("separa el tema de la app de la paleta del lector", async ({ page, playwright }) => {
  const api = await playwright.request.newContext({ baseURL: API_URL });
  await api.put("/api/settings", {
    data: { theme_mode: "system", reader_palette: "paper" },
  });
  const book = await ensureReadyBook(api, "e2e-reader.epub", "Lector E2E");
  await api.dispose();

  await page.goto("/#/settings");
  await page.getByRole("radio", { name: "Oscuro" }).check();
  await page.getByRole("button", { name: "Guardar" }).click();
  await expect(page.getByRole("button", { name: "Guardado" })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

  await page.goto(`/#/books/${book.id}/read`);
  await page.getByRole("button", { name: "Ajustes de lectura" }).click();
  await page.getByRole("radio", { name: "Noche" }).check();

  await expect(page.locator(".reader-shell")).toHaveAttribute("data-reader-palette", "night");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});
