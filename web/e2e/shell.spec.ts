import { expect, test } from "@playwright/test";

test("la navegación mobile y el toggle de tema siguen disponibles", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/#/");

  const mobileNav = page.locator(".mobile-nav");
  await expect(mobileNav).toBeVisible();
  await expect(mobileNav.getByRole("link", { name: "Biblioteca" })).toHaveAttribute(
    "aria-current",
    "page",
  );

  await mobileNav.getByRole("link", { name: "Importar" }).click();
  await expect(page.getByRole("heading", { name: "Traé un libro al taller" })).toBeVisible();

  const toggle = page.getByRole("button", { name: /Tema/ });
  await expect(toggle).toBeVisible();
  const beforeLabel = await toggle.getAttribute("aria-label");
  await toggle.click();
  await expect(toggle).not.toHaveAttribute("aria-label", beforeLabel ?? "");
});
