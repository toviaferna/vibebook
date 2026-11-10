import { expect, test } from "@playwright/test";

import { API_URL, ensureReadyBook, resetReadingState } from "./helpers";

test("reproduce, resalta y persiste la posición", async ({ page, playwright }) => {
  const api = await playwright.request.newContext({ baseURL: API_URL });
  const book = await ensureReadyBook(api, "e2e-reader.epub", "Lector E2E");
  await resetReadingState(api, book.id);
  await api.dispose();

  await page.goto(`/#/books/${book.id}/read`);
  await expect(page.getByRole("heading", { name: "Capítulo 1" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Reproducir" })).toBeVisible();

  await page.getByRole("button", { name: "Abrir índice" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();

  await page.getByRole("button", { name: "Original" }).click();
  const original = page.getByTestId("original-epub");
  await expect(original).toHaveAttribute("data-status", "ready", { timeout: 20_000 });
  await expect(original.locator("iframe")).toBeVisible();
  await page.getByRole("button", { name: "Texto" }).click();
  await expect(original).toBeHidden();

  await page.getByRole("button", { name: "Libro", exact: true }).click();
  await expect(page.getByRole("region", { name: /Lectura de/ })).toBeVisible();
  await expect(page.getByText(/Páginas? \d+(?:[-–]\d+)? de \d+/)).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Navegación de páginas" })).toBeVisible();
  await page.getByRole("button", { name: "Texto" }).click();

  await page.getByRole("button", { name: "Reproducir" }).click();
  const activeWord = page.locator(".reader-word.is-active");
  await expect(activeWord).toBeVisible();
  const firstWord = await activeWord.textContent();

  await expect
    .poll(() => page.evaluate(() => document.querySelector("audio")?.currentTime ?? 0), {
      timeout: 10_000,
    })
    .toBeGreaterThan(0.4);

  await expect.poll(() => activeWord.textContent(), { timeout: 10_000 }).not.toBe(firstWord);

  await page.getByRole("button", { name: "Pausar" }).click();
  const beforeReload = await page.evaluate(
    () => (document.querySelector("audio") as HTMLAudioElement).currentTime,
  );
  expect(beforeReload).toBeGreaterThan(0.4);
  await page.waitForTimeout(2_000);

  await page.reload();
  await expect(page.getByRole("heading", { name: "Capítulo 1" })).toBeVisible();
  await expect
    .poll(
      () =>
        page.evaluate(() => {
          const audio = document.querySelector("audio") as HTMLAudioElement | null;
          return audio ? audio.currentTime : 0;
        }),
      { timeout: 10_000 },
    )
    .toBeGreaterThan(beforeReload - 0.5);

  const paused = await page.evaluate(
    () => (document.querySelector("audio") as HTMLAudioElement | null)?.paused,
  );
  expect(paused).toBe(true);
});

test("guarda la posición del texto y el CFI del original", async ({ page, playwright }) => {
  const api = await playwright.request.newContext({ baseURL: API_URL });
  const book = await ensureReadyBook(api, "e2e-reader.epub", "Lector E2E");
  await resetReadingState(api, book.id);
  await api.dispose();

  await page.goto(`/#/books/${book.id}/read`);
  await expect(page.getByRole("heading", { name: "Capítulo 1" })).toBeVisible();
  await page.getByRole("button", { name: "Buscar en el libro" }).click();
  await page.getByRole("searchbox", { name: "Texto a buscar" }).fill("lector");
  await page.getByRole("button", { name: /Cap\. 1/ }).first().click();
  await page.waitForTimeout(900);

  await expect
    .poll(async () => {
      const response = await page.request.get(`/api/books/${book.id}/reading-state`);
      const state = await response.json();
      return state.char_offset as number;
    })
    .toBeGreaterThan(0);

  await page.getByRole("button", { name: "Original" }).click();
  await expect(page.getByTestId("original-epub")).toHaveAttribute("data-status", "ready", {
    timeout: 20_000,
  });
  await expect
    .poll(async () => {
      const response = await page.request.get(`/api/books/${book.id}/reading-state`);
      const state = await response.json();
      return state.cfi as string | null;
    })
    .not.toBeNull();
});
