import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderRoute } from "../../test/utils";
import { BookDetailPage } from "./BookDetailPage";

describe("BookDetailPage", () => {
  it("muestra metadata y acciones", async () => {
    renderRoute("/books/lazarillo-1234", "/books/:id", <BookDetailPage />);

    expect(await screen.findByText("El Lazarillo de Tormes")).toBeInTheDocument();
    expect(screen.getByText("Abrir estudio")).toBeInTheDocument();
    expect(screen.getByText("Descargar M4B")).toBeInTheDocument();
  });

  it("pide confirmación antes de eliminar", async () => {
    const user = userEvent.setup();
    renderRoute("/books/lazarillo-1234", "/books/:id", <BookDetailPage />);

    await user.click(await screen.findByRole("button", { name: "Eliminar libro" }));

    expect(await screen.findByText(/¿Eliminar/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Eliminar definitivamente" })).toBeInTheDocument();
  });
});
