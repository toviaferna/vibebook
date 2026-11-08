import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderRoute } from "../../test/utils";
import { StudioPage } from "./StudioPage";

describe("StudioPage", () => {
  it("muestra los pasos y el resumen de conversión", async () => {
    renderRoute("/books/lazarillo-1234/studio", "/books/:id/studio", <StudioPage />);

    expect(await screen.findByRole("heading", { name: "Voz" })).toBeInTheDocument();
    expect(screen.getAllByText("Jorge").length).toBeGreaterThan(0);
    expect(screen.getByText("Salida")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Reconvertir/ })).toBeInTheDocument();
  });

  it("inicia una conversión y muestra el resultado", async () => {
    const user = userEvent.setup();
    renderRoute("/books/lazarillo-1234/studio", "/books/:id/studio", <StudioPage />);

    await user.click(await screen.findByRole("button", { name: /Reconvertir/ }));

    expect(await screen.findByText("Conversión completa.")).toBeInTheDocument();
  });

  it("permite elegir otra voz", async () => {
    const user = userEvent.setup();
    renderRoute("/books/lazarillo-1234/studio", "/books/:id/studio", <StudioPage />);

    const dalia = await screen.findByRole("button", { name: /^Dalia/ });
    await user.click(dalia);

    expect(dalia).toHaveAttribute("aria-pressed", "true");
  });

  it("permite elegir Piper y su voz local", async () => {
    const user = userEvent.setup();
    renderRoute("/books/lazarillo-1234/studio", "/books/:id/studio", <StudioPage />);

    const engine = await screen.findByLabelText("Motor");
    await user.selectOptions(engine, "piper");

    const aldo = await screen.findByRole("button", { name: /^Aldo/ });
    expect(aldo).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("option", { name: /Piper/ })).toBeInTheDocument();
  });
});
