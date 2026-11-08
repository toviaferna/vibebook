import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import { sampleBook } from "../../test/fixtures";
import { server } from "../../test/server";
import { renderWithProviders } from "../../test/utils";
import { LibraryPage } from "./LibraryPage";

describe("LibraryPage", () => {
  it("muestra los libros de la biblioteca", async () => {
    renderWithProviders(<LibraryPage />);

    expect((await screen.findAllByText("El Lazarillo de Tormes")).length).toBeGreaterThan(0);
    expect(screen.getByText("Anónimo")).toBeInTheDocument();
    expect(screen.getByText("Continuar")).toBeInTheDocument();
    expect(screen.getByText("Listo")).toBeInTheDocument();
  });

  it("filtra libros sin audio", async () => {
    const imported = {
      ...sampleBook,
      id: "solo-texto",
      title: "Solo texto",
      status: "imported" as const,
      duration_ms: null,
      progress: 0,
      reading_progress: 0.15,
      last_read_chapter_index: 1,
    };
    server.use(
      http.get("*/api/books", () =>
        HttpResponse.json({
          items: [sampleBook, imported],
          total: 2,
          limit: 100,
          offset: 0,
        }),
      ),
    );
    const user = userEvent.setup();
    renderWithProviders(<LibraryPage />);

    await screen.findByText("Solo texto");
    await user.click(screen.getByRole("button", { name: "Sin audio" }));

    expect(screen.getByText("Solo texto")).toBeInTheDocument();
    expect(screen.queryByText("El Lazarillo de Tormes")).not.toBeInTheDocument();
  });

  it("muestra el estado vacío", async () => {
    server.use(
      http.get("*/api/books", () =>
        HttpResponse.json({ items: [], total: 0, limit: 100, offset: 0 }),
      ),
    );

    renderWithProviders(<LibraryPage />);

    expect(await screen.findByText("Tu biblioteca está vacía")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Elegir EPUB" })).toBeInTheDocument();
  });

  it("muestra un error de API con reintento", async () => {
    server.use(
      http.get("*/api/books", () =>
        HttpResponse.json(
          { error: { code: "internal_error", message: "Falló el índice." } },
          { status: 500 },
        ),
      ),
    );

    renderWithProviders(<LibraryPage />);

    expect(await screen.findByText("No se pudo cargar la biblioteca.")).toBeInTheDocument();
    expect(screen.getByText("Falló el índice.")).toBeInTheDocument();
  });
});
