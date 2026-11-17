import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { sampleBookDetail } from "../../test/fixtures";
import { renderWithProviders } from "../../test/utils";
import { AmbiencePanel } from "./AmbiencePanel";

describe("AmbiencePanel", () => {
  it("asigna una cama a un capítulo y guarda el plan", async () => {
    renderWithProviders(<AmbiencePanel book={sampleBookDetail} />, "/");

    expect(await screen.findByText("Sonido del libro")).toBeInTheDocument();
    const select = await screen.findByLabelText("Cama del capítulo 1");
    fireEvent.change(select, { target: { value: "procedural-rain-1234" } });

    expect(await screen.findByText("-24 dB")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Volumen del plan · -18 dB"), {
      target: { value: "-24" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Guardar plan" }));

    await waitFor(() => expect(screen.getByText("Plan de ambiente guardado.")).toBeInTheDocument());
  });

  it("analiza el texto y reemplaza el plan", async () => {
    renderWithProviders(<AmbiencePanel book={sampleBookDetail} />, "/");

    fireEvent.click(await screen.findByRole("button", { name: "Analizar capítulos" }));

    await waitFor(() =>
      expect(screen.getByText("Plan analizado a partir del texto.")).toBeInTheDocument(),
    );
  });
});
