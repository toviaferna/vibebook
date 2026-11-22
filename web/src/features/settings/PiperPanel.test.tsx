import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import type { PiperStatus } from "../../api/types";
import { samplePiperStatus } from "../../test/fixtures";
import { server } from "../../test/server";
import { renderWithProviders } from "../../test/utils";
import { PiperPanel } from "./PiperPanel";

function _status(overrides: Partial<PiperStatus> = {}): PiperStatus {
  return { ...samplePiperStatus, ...overrides };
}

describe("PiperPanel", () => {
  it("guarda el binario y la carpeta de voces", async () => {
    const user = userEvent.setup();
    let payload: Record<string, unknown> | null = null;
    server.use(
      http.put("*/api/piper", async ({ request }) => {
        payload = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          _status({
            binary: "C:\\piper\\piper.exe",
            voices_dir: "C:\\voces",
            binary_configured: true,
            voices: [
              {
                id: "es_MX-ald-medium",
                name: "Aldo",
                locale: "es-MX",
                gender: "male",
                path: "C:\\voces\\es_MX-ald-medium.onnx",
                available: true,
              },
            ],
          }),
        );
      }),
    );
    renderWithProviders(<PiperPanel />);

    await screen.findByText("Piper neural (local)");
    await user.type(await screen.findByLabelText("Binario de Piper"), "C:\\piper\\piper.exe");
    await user.type(screen.getByLabelText("Carpeta de voces Piper"), "C:\\voces");
    await user.click(screen.getByRole("button", { name: /Guardar y detectar/ }));

    expect(await screen.findByText(/Piper configurado/)).toBeInTheDocument();
    expect(await screen.findByText("Aldo")).toBeInTheDocument();
    expect(payload).toMatchObject({
      binary: "C:\\piper\\piper.exe",
      voices_dir: "C:\\voces",
      espeak_data: null,
    });
  });

  it("usa una carpeta de voces sugerida", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("*/api/piper", () =>
        HttpResponse.json(
          _status({
            suggestions: [
              {
                path: "C:\\Users\\yo\\AppData\\Roaming\\com.vibebook\\vibebook_app\\models\\piper",
                label: "Voces de la app Flutter anterior",
              },
            ],
          }),
        ),
      ),
    );
    renderWithProviders(<PiperPanel />);

    await user.click(
      await screen.findByRole("button", {
        name: /Voces de la app Flutter anterior/,
      }),
    );

    await waitFor(() => {
      expect(screen.getByLabelText("Carpeta de voces Piper")).toHaveValue(
        "C:\\Users\\yo\\AppData\\Roaming\\com.vibebook\\vibebook_app\\models\\piper",
      );
    });
  });

  it("muestra el error de validación del backend", async () => {
    const user = userEvent.setup();
    server.use(
      http.put("*/api/piper", () =>
        HttpResponse.json(
          {
            error: {
              code: "invalid_piper_settings",
              message: "No encontré el binario de Piper: C:\\no-existe",
            },
          },
          { status: 422 },
        ),
      ),
    );
    renderWithProviders(<PiperPanel />);

    await screen.findByText("Piper neural (local)");
    await user.type(await screen.findByLabelText("Binario de Piper"), "C:\\no-existe");
    await user.click(screen.getByRole("button", { name: /Guardar y detectar/ }));

    expect(await screen.findByText(/No encontré el binario de Piper/)).toBeInTheDocument();
  });
});
