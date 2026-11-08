import { mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { chromium } from "@playwright/test";

const appUrl = process.env.APP_URL ?? "http://127.0.0.1:5173";
const apiUrl = process.env.API_URL ?? "http://127.0.0.1:8765";
const bookId = process.env.BOOK_ID;
if (!bookId) {
  throw new Error("BOOK_ID is required (a converted book in the running studio)");
}

const output = fileURLToPath(new URL("../../docs/assets/identity/", import.meta.url));
await mkdir(output, { recursive: true });

async function setSettings(themeMode, readerPalette) {
  const response = await fetch(`${apiUrl}/api/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ theme_mode: themeMode, reader_palette: readerPalette }),
  });
  if (!response.ok) {
    throw new Error(`settings ${response.status}: ${await response.text()}`);
  }
}

async function preparePage(page, hash, themeMode, readerPalette) {
  await setSettings(themeMode, readerPalette);
  await page.goto(`${appUrl}/#${hash}`);
  await page.evaluate(
    ([mode, palette]) => {
      localStorage.setItem("vibebook.theme-mode", mode);
      localStorage.setItem("vibebook.reader-palette", palette);
    },
    [themeMode, readerPalette],
  );
  await page.reload();
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(500);
}

async function capture(page, name, fullPage = true) {
  await page.screenshot({
    path: `${output}/${name}.jpg`,
    type: "jpeg",
    quality: 82,
    fullPage,
  });
  console.log(`captured ${name}.jpg`);
}

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1440, height: 960 },
  colorScheme: "light",
});

try {
  await preparePage(page, "/", "light", "paper");
  await page.getByRole("heading", { name: "Tu taller de escucha" }).waitFor();
  await capture(page, "library-light");

  await preparePage(page, "/", "dark", "night");
  await page.getByRole("heading", { name: "Tu taller de escucha" }).waitFor();
  await capture(page, "library-dark");

  await preparePage(page, `/books/${bookId}`, "light", "paper");
  await page.getByRole("heading", { name: "Lector E2E" }).waitFor();
  await capture(page, "detail-light");

  await preparePage(page, `/books/${bookId}`, "dark", "night");
  await page.getByRole("heading", { name: "Lector E2E" }).waitFor();
  await capture(page, "detail-dark");

  await preparePage(page, `/books/${bookId}/read`, "light", "paper");
  await page.getByRole("button", { name: "Libro", exact: true }).click();
  await page.locator(".book-page").first().waitFor();
  await capture(page, "reader-light", false);

  await preparePage(page, `/books/${bookId}/read`, "light", "sepia");
  await page.getByRole("button", { name: "Libro", exact: true }).click();
  await page.locator(".book-page").first().waitFor();
  await capture(page, "reader-sepia", false);

  await preparePage(page, `/books/${bookId}/read`, "dark", "night");
  await page.getByRole("button", { name: "Libro", exact: true }).click();
  await page.locator(".book-page").first().waitFor();
  await capture(page, "reader-dark", false);

  await preparePage(page, "/settings", "light", "paper");
  await page.getByRole("heading", { name: "Preferencias del taller" }).waitFor();
  await capture(page, "settings-light");

  await preparePage(page, "/settings", "dark", "night");
  await page.getByRole("heading", { name: "Preferencias del taller" }).waitFor();
  await capture(page, "settings-dark");
} finally {
  await setSettings("system", "paper").catch(() => {});
  await browser.close();
}
