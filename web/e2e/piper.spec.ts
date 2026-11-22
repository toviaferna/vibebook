import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "@playwright/test";

import { API_URL } from "./helpers";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../..");
const fixtures = path.join(root, ".tmp", "e2e-piper");

function createVoiceFolder(): { binary: string; voices: string } {
  fs.rmSync(fixtures, { recursive: true, force: true });
  const voiceDir = path.join(fixtures, "vits-piper-es_MX-ald-medium");
  fs.mkdirSync(voiceDir, { recursive: true });
  fs.writeFileSync(path.join(voiceDir, "es_MX-ald-medium.onnx"), "onnx");
  fs.writeFileSync(path.join(voiceDir, "es_MX-ald-medium.onnx.json"), "{}");
  const binary = path.join(fixtures, "piper");
  fs.writeFileSync(binary, "binary");
  return { binary, voices: fixtures };
}

test("Ajustes detecta el binario y las voces de Piper", async ({ page, playwright }) => {
  const { binary, voices } = createVoiceFolder();
  const api = await playwright.request.newContext({ baseURL: API_URL });
  await api.put("/api/piper", {
    data: { binary: null, voices_dir: null, espeak_data: null },
  });

  try {
    await page.goto("/#/settings");

    const panel = page.locator("section.panel", { hasText: "Piper neural (local)" });
    await expect(panel).toBeVisible();
    await expect(panel.getByText(/Falta el binario de Piper/)).toBeVisible();

    await page.getByLabel("Binario de Piper").fill(binary);
    await page.getByLabel("Carpeta de voces Piper").fill(voices);
    await page.getByRole("button", { name: /Guardar y detectar/ }).click();

    await expect(panel.getByText(/Piper configurado/)).toBeVisible();
    await expect(panel.getByText(/Binario detectado/)).toBeVisible();
    await expect(panel.getByText("Aldo")).toBeVisible();
    await expect(panel.getByText("es_MX-ald-medium", { exact: true })).toBeVisible();

    const saved = await (await api.get("/api/piper")).json();
    expect(saved.voices).toHaveLength(1);
    expect(saved.voices[0].id).toBe("es_MX-ald-medium");

    await page.goto("/#/books");
    await page.goto("/#/settings");
    await expect(panel.getByText("Aldo")).toBeVisible();
  } finally {
    await api.put("/api/piper", {
      data: { binary: null, voices_dir: null, espeak_data: null },
    });
    await api.dispose();
    fs.rmSync(fixtures, { recursive: true, force: true });
  }
});

test("Ajustes explica cuando la ruta del binario no existe", async ({ page }) => {
  await page.goto("/#/settings");

  const panel = page.locator("section.panel", { hasText: "Piper neural (local)" });
  await expect(panel).toBeVisible();
  await page.getByLabel("Binario de Piper").fill("C:\\no-existe\\piper.exe");
  await page.getByRole("button", { name: /Guardar y detectar/ }).click();

  await expect(panel.getByText(/No encontré el binario de Piper/)).toBeVisible();
});
