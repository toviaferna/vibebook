import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { API_URL, ensureReadyBook } from "./helpers";

test("biblioteca, detalle, estudio y lector sin violaciones graves", async ({
  page,
  playwright,
}) => {
  const api = await playwright.request.newContext({ baseURL: API_URL });
  const book = await ensureReadyBook(api, "e2e-reader.epub", "Lector E2E");
  await api.dispose();

  const pages = [
    { path: "/", heading: "Tu biblioteca" },
    { path: `/#/books/${book.id}`, heading: "Lector E2E" },
    { path: `/#/books/${book.id}/studio`, heading: "Lector E2E" },
    { path: `/#/books/${book.id}/read`, heading: "Capítulo 1" },
  ];

  for (const entry of pages) {
    await page.goto(entry.path);
    await expect(page.getByRole("heading", { name: entry.heading }).first()).toBeVisible();
    await page.waitForTimeout(500);

    const results = await new AxeBuilder({ page }).analyze();
    const serious = results.violations.filter(
      (violation) => violation.impact === "serious" || violation.impact === "critical",
    );

    expect(
      serious.map(
        (violation) =>
          `${violation.id}: ${violation.nodes.map((node) => node.target.join(" ")).join(" | ")}`,
      ),
      entry.path,
    ).toEqual([]);
  }
});
