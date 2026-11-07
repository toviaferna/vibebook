import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderWithProviders } from "../../test/utils";
import { ImportPage } from "./ImportPage";

describe("ImportPage", () => {
  it("importa un EPUB y muestra el resumen", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ImportPage />);
    const input = screen.getByLabelText("Seleccionar EPUB");
    const file = new File(["fake"], "libro.epub", { type: "application/epub+zip" });

    await user.upload(input, file);

    expect(await screen.findByText("Preparar audiolibro")).toBeInTheDocument();
    expect(screen.getByText("El Lazarillo de Tormes")).toBeInTheDocument();
  });

  it("rechaza archivos que no son EPUB", () => {
    renderWithProviders(<ImportPage />);
    const input = screen.getByLabelText("Seleccionar EPUB");
    const file = new File(["fake"], "libro.txt", { type: "text/plain" });

    fireEvent.change(input, { target: { files: [file] } });

    expect(screen.getByText("El archivo debe tener extensión .epub.")).toBeInTheDocument();
  });
});
