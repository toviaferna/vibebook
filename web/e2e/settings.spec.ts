import { expect, test } from "@playwright/test";

test("preferencias no desbordan con una ruta de biblioteca larga", async ({ page }) => {
  await page.route("**/api/settings", async (route) => {
    const response = await route.fetch();
    const json = (await response.json()) as Record<string, unknown>;
    json.library_dir =
      "C:\\Users\\tøvia\\AppData\\Local\\vibebook\\vibebook\\library\\biblioteca-personal-de-prueba";
    await route.fulfill({ response, json });
  });

  for (const viewport of [
    { width: 900, height: 1200 },
    { width: 1440, height: 900 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto("/#/settings");
    await expect(page.getByRole("heading", { name: "Preferencias" })).toBeVisible();

    const layout = await page.evaluate(() => {
      const panels = [...document.querySelectorAll<HTMLElement>(".settings-grid > .panel")];
      const bodies = panels.map((panel) => panel.querySelector<HTMLElement>(".panel-body"));
      return {
        overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
        panels: panels.map((panel, index) => {
          const rect = panel.getBoundingClientRect();
          const body = bodies[index];
          return {
            left: rect.left,
            right: rect.right,
            bodyClientWidth: body?.clientWidth ?? 0,
            bodyScrollWidth: body?.scrollWidth ?? 0,
          };
        }),
      };
    });

    expect(layout.overflow).toBe(false);
    for (const panel of layout.panels) {
      expect(panel.bodyScrollWidth, `panel ${panel.left} desborda`).toBeLessThanOrEqual(
        panel.bodyClientWidth,
      );
    }
    for (let index = 1; index < layout.panels.length; index += 1) {
      expect(layout.panels[index - 1].right).toBeLessThanOrEqual(layout.panels[index].left + 1);
    }
  }
});
