import { expect, test } from "@playwright/test";

import { API_URL, ensureReadyBook } from "./helpers";

test("una clave guardada desbloquea el motor y muestra solo sus voces", async ({
  page,
  playwright,
}) => {
  const api = await playwright.request.newContext({ baseURL: API_URL });
  const book = await ensureReadyBook(api, "e2e-reader.epub", "Lector E2E");
  await api.delete("/api/providers/elevenlabs");
  await api.put("/api/providers/elevenlabs", {
    data: { api_key: "sk_e2e_test_key_1234" },
  });
  await api.dispose();

  await page.goto(`/#/books/${book.id}/studio`);
  const switchButton = page.getByRole("button", { name: "Usar ElevenLabs" });
  await expect(switchButton).toBeVisible();
  await switchButton.click();

  await expect(page.getByLabel("Motor")).toHaveValue("elevenlabs");
  await expect(page.locator(".voice-card", { hasText: "Adam" })).toBeVisible();
  await expect(page.locator(".voice-card", { hasText: "Jorge" })).toHaveCount(0);
  await expect(page.getByText("Emociones", { exact: true })).toBeVisible();
});
