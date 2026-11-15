import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "../../test/utils";
import { ProvidersPanel } from "./ProvidersPanel";

describe("ProvidersPanel", () => {
  it("muestra los proveedores y guarda una clave", async () => {
    renderWithProviders(<ProvidersPanel />, "/settings");

    const gemini = await screen.findByRole("article", { name: "Google Gemini TTS" });
    expect(within(gemini).getByText("Sin configurar")).toBeInTheDocument();

    fireEvent.change(within(gemini).getByLabelText("Clave de API"), {
      target: { value: "AQ.test-key-1234" },
    });
    fireEvent.click(within(gemini).getByRole("button", { name: "Guardar clave" }));

    await waitFor(() => expect(within(gemini).getByText("Clave guardada.")).toBeInTheDocument());
  });

  it("no muestra la clave completa", async () => {
    renderWithProviders(<ProvidersPanel />, "/settings");

    const eleven = await screen.findByRole("article", { name: "ElevenLabs" });
    fireEvent.change(within(eleven).getByLabelText("Clave de API"), {
      target: { value: "sk_secret_key_9876" },
    });
    fireEvent.click(within(eleven).getByRole("button", { name: "Guardar clave" }));

    await waitFor(() => expect(within(eleven).getByText("Clave guardada.")).toBeInTheDocument());
    expect(screen.queryByDisplayValue("sk_secret_key_9876")).not.toBeInTheDocument();
  });
});
