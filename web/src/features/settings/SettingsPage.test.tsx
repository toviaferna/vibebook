import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import type { PluginList } from "../../api/types";
import { samplePlugin, sampleSettings } from "../../test/fixtures";
import { server } from "../../test/server";
import { renderWithProviders } from "../../test/utils";
import { SettingsPage } from "./SettingsPage";

describe("SettingsPage", () => {
  it("muestra las preferencias y cambia el tema de la app", async () => {
    const user = userEvent.setup();
    renderWithProviders(<SettingsPage />);

    expect(await screen.findByText("Preferencias del taller")).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: "Oscuro" }));

    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("mantiene independiente la paleta del lector", async () => {
    const user = userEvent.setup();
    renderWithProviders(<SettingsPage />);

    await screen.findByText("Preferencias del taller");
    await user.click(screen.getByRole("radio", { name: "Noche" }));

    expect(screen.getByRole("radio", { name: "Noche" })).toBeChecked();
    expect(document.documentElement.dataset.theme).not.toBe("night");
  });

  it("permite elegir Piper como motor por defecto", async () => {
    const user = userEvent.setup();
    renderWithProviders(<SettingsPage />);

    const engine = await screen.findByLabelText("Motor");
    await user.selectOptions(engine, "piper");

    expect(engine).toHaveValue("piper");
    expect(screen.getByLabelText("Voz")).toHaveValue("es_MX-ald-medium");
  });

  it("guarda solo los campos editables", async () => {
    const user = userEvent.setup();
    let payload: Record<string, unknown> | null = null;
    server.use(
      http.put("*/api/settings", async ({ request }) => {
        payload = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ ...sampleSettings, ...payload });
      }),
    );
    renderWithProviders(<SettingsPage />);

    await user.click(await screen.findByRole("button", { name: "Guardar" }));

    expect(await screen.findByRole("button", { name: "Guardado" })).toBeInTheDocument();
    expect(payload).toMatchObject({
      default_engine: "edge",
      default_voice: "es-MX-JorgeNeural",
    });
    expect(payload).not.toHaveProperty("library_dir");
    expect(payload).not.toHaveProperty("azure_configured");
  });

  it("agrega un plugin VEP", async () => {
    const user = userEvent.setup();
    let plugins: PluginList = { items: [] };
    server.use(
      http.get("*/api/engines/plugins", () => HttpResponse.json(plugins)),
      http.post("*/api/engines/plugins", async ({ request }) => {
        const body = (await request.json()) as { url: string };
        const plugin = { ...samplePlugin, url: body.url };
        plugins = { items: [plugin] };
        return HttpResponse.json(plugin, { status: 201 });
      }),
    );
    renderWithProviders(<SettingsPage />);

    await user.type(await screen.findByLabelText("URL del plugin"), "http://127.0.0.1:9001");
    await user.click(screen.getByRole("button", { name: "Agregar plugin" }));

    expect(await screen.findByText("Demo VEP")).toBeInTheDocument();
    expect(screen.getByText("Plugin agregado.")).toBeInTheDocument();
  });
});
