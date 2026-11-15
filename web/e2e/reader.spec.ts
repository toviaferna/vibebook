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

test("en mobile hoja una página, sigue el audio y no desborda", async ({ page, playwright }) => {
  const api = await playwright.request.newContext({ baseURL: API_URL });
  const book = await ensureReadyBook(api, "e2e-reader.epub", "Lector E2E");
  await resetReadingState(api, book.id);
  await api.put(`/api/books/${book.id}/preferences`, {
    data: { reader_mode: "book", reader_size: 28 },
  });

  try {
    await page.setViewportSize({ width: 390, height: 640 });
    await page.goto(`/#/books/${book.id}/read`);
    await expect(page.getByRole("region", { name: /Lectura de/ })).toBeVisible();

    const nav = page.getByRole("navigation", { name: "Navegación de páginas" });
    const label = nav.locator(".mono.muted");
    await expect(label).toHaveText(/^Página 1 de \d+$/);
    await expect(page.locator(".book-word").first()).toBeVisible();

    const karaoke = nav.getByRole("button", { name: "Karaoke" });
    await expect(karaoke).toHaveAttribute("aria-pressed", "true");

    const follow = page.locator("button.reader-follow");
    if ((await follow.getAttribute("aria-pressed")) === "false") {
      await follow.click();
    }
    await page.waitForTimeout(700);
    await page.getByRole("button", { name: "Reproducir" }).click();
    await expect(label).toHaveText(/^Página 2 de \d+$/, { timeout: 12_000 });
    await expect(page.locator(".book-word.is-active")).toBeVisible();
    await page.getByRole("button", { name: "Pausar" }).click();

    const overflow = page.evaluate(
      () =>
        new Promise<number>((resolve) => {
          let maximum = 0;
          const start = performance.now();
          const tick = () => {
            maximum = Math.max(maximum, document.documentElement.scrollWidth);
            if (performance.now() - start < 1_200) {
              requestAnimationFrame(tick);
            } else {
              resolve(maximum);
            }
          };
          tick();
        }),
    );
    await nav.getByRole("button", { name: /siguiente/i }).click();
    const viewportWidth = await page.evaluate(() => window.innerWidth);
    expect(await overflow).toBeLessThanOrEqual(viewportWidth + 1);

    await karaoke.click();
    await expect(karaoke).toHaveAttribute("aria-pressed", "false");
    await expect(page.locator(".book-word")).toHaveCount(0);
  } finally {
    await api.put(`/api/books/${book.id}/preferences`, {
      data: { reader_mode: "text", reader_size: 19, book_karaoke: true },
    });
    await api.dispose();
  }
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
  await page
    .getByRole("button", { name: /Cap\. 1/ })
    .first()
    .click();
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
