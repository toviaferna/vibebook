import { expect, test } from "@playwright/test";

import { API_URL, ensureImportedBook, resetReadingState } from "./helpers";

const viewports = [
  { label: "desktop", width: 1440, height: 900, pages: 2 },
  { label: "laptop", width: 1024, height: 768, pages: 2 },
  { label: "mobile", width: 390, height: 844, pages: 1 },
];

test("el giro de página no redimensiona el lector", async ({ page, playwright }) => {
  const api = await playwright.request.newContext({ baseURL: API_URL });
  const book = await ensureImportedBook(api, "e2e-book.epub", "Libro E2E");
  await resetReadingState(api, book.id);
  await api.put(`/api/books/${book.id}/preferences`, {
    data: { reader_mode: "book", reader_size: 19 },
  });
  await api.dispose();

  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto(`/#/books/${book.id}/read`);
    await page.getByRole("button", { name: "Libro", exact: true }).click();
    await expect(page.locator(".book-page:visible").first()).toBeVisible();
    await expect(page.locator(".book-nav .mono")).toHaveText(
      viewport.pages === 1 ? /^Página \d+ de \d+$/ : /^Páginas \d+–\d+ de \d+$/,
    );

    const label = page.locator(".book-nav .mono");
    for (let turn = 0; turn < 2; turn += 1) {
      const previousLabel = await label.textContent();
      const samples = await page.evaluate(async () => {
        const rect = (selector: string) => {
          const node = document.querySelector(selector);
          if (!node) return null;
          const value = node.getBoundingClientRect();
          return {
            x: Math.round(value.x * 10) / 10,
            y: Math.round(value.y * 10) / 10,
            w: Math.round(value.width * 10) / 10,
            h: Math.round(value.height * 10) / 10,
          };
        };
        const read = () => {
          const scroller = document.scrollingElement ?? document.documentElement;
          return {
            scrollX: window.scrollX,
            scrollY: window.scrollY,
            scrollWidth: scroller.scrollWidth,
            scrollHeight: scroller.scrollHeight,
            reader: rect(".reader-shell"),
            layout: rect(".reader-layout"),
            article: rect(".reader-article-wrap"),
            table: rect(".book-table"),
            viewport: rect(".book-viewport"),
            book: rect(".opf-book"),
            nav: rect(".book-nav"),
          };
        };

        const samples = [read()];
        const button = document.querySelector(
          '.book-nav button[aria-label="Página siguiente"]',
        ) as HTMLButtonElement | null;
        button?.click();
        for (let frame = 0; frame < 40; frame += 1) {
          await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
          samples.push(read());
        }
        return samples;
      });

      for (const key of [
        "scrollX",
        "scrollY",
        "scrollWidth",
        "scrollHeight",
        "reader",
        "layout",
        "article",
        "table",
        "viewport",
        "book",
        "nav",
      ] as const) {
        const values = new Set(samples.map((sample) => JSON.stringify(sample[key])));
        expect(values.size, `${viewport.label}: ${key} estable durante el giro`).toBe(1);
      }

      const geometry = samples[0];
      expect(geometry.scrollX, `${viewport.label}: sin scroll horizontal`).toBe(0);
      expect(geometry.scrollY, `${viewport.label}: sin scroll vertical`).toBe(0);
      expect(
        geometry.scrollWidth,
        `${viewport.label}: sin desbordamiento horizontal`,
      ).toBeLessThanOrEqual(viewport.width + 1);

      await expect.poll(async () => label.textContent()).not.toBe(previousLabel);
    }
  }
});
