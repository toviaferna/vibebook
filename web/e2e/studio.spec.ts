import { expect, test } from "@playwright/test";

import { fixturePath } from "./helpers";

test("importa y convierte un EPUB con el motor fake", async ({ page }) => {
  await page.goto("/#/import");

  await page.getByLabel("Seleccionar EPUB").setInputFiles(fixturePath("e2e-studio.epub"));
  await expect(page.getByRole("heading", { name: "Studio E2E" })).toBeVisible();

  await page.getByRole("link", { name: "Preparar audiolibro" }).click();
  await expect(page.getByRole("heading", { name: "Studio E2E" })).toBeVisible();
  await expect(page.getByLabel("Motor")).toBeVisible();

  await page.getByLabel("Motor").selectOption("fake");
  await page.getByRole("button", { name: "Convertir audiolibro" }).click();

  await expect(page.getByText("Conversión completa.")).toBeVisible({ timeout: 120_000 });
  await expect(page.getByRole("link", { name: "Leer ahora" })).toBeVisible();
});
