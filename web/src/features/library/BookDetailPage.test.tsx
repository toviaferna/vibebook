import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import { sampleBook, sampleResegmentPlan } from "../../test/fixtures";
import { server } from "../../test/server";
import { renderRoute } from "../../test/utils";
import { BookDetailPage } from "./BookDetailPage";

describe("BookDetailPage", () => {
  it("muestra metadata y acciones", async () => {
    renderRoute("/books/lazarillo-1234", "/books/:id", <BookDetailPage />);

    expect(
      await screen.findByRole("heading", { name: "El Lazarillo de Tormes" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Leer y escuchar")).toBeInTheDocument();
    expect(screen.getByText("Abrir estudio")).toBeInTheDocument();
    expect(await screen.findByText("Descargar M4B")).toBeInTheDocument();
    expect(screen.getByText("Segmentación del audio")).toBeInTheDocument();
  });

  it("permite leer un libro importado sin audio", async () => {
    server.use(
      http.get("*/api/books/:id", () =>
        HttpResponse.json({
          ...sampleBook,
          status: "imported",
          duration_ms: null,
          voice: null,
          engine: null,
          rate: null,
          progress: 0,
        }),
      ),
    );
    renderRoute("/books/lazarillo-1234", "/books/:id", <BookDetailPage />);

    expect(await screen.findByRole("link", { name: "Leer" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Convertir a audiolibro" })).toBeInTheDocument();
    expect(screen.queryByText("Descargar M4B")).not.toBeInTheDocument();
  });

  it("repara la segmentación cuando hay texto viejo", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("*/api/books/:id/resegment", () =>
        HttpResponse.json({
          ...sampleResegmentPlan,
          needs_repair: true,
          current_version: 1,
          changed_segments: 2,
          changed_chapters: [1],
          chapters: [
            {
              index: 1,
              title: "Capítulo 1",
              changed: true,
              changed_segments: 2,
              added_segments: 0,
              removed_segments: 0,
            },
          ],
        }),
      ),
    );
    renderRoute("/books/lazarillo-1234", "/books/:id", <BookDetailPage />);

    await user.click(await screen.findByRole("button", { name: "Reparar segmentación" }));

    expect(await screen.findByText(/Reparación lista/)).toBeInTheDocument();
  });

  it("pide confirmación antes de eliminar", async () => {
    const user = userEvent.setup();
    renderRoute("/books/lazarillo-1234", "/books/:id", <BookDetailPage />);

    await user.click(await screen.findByRole("button", { name: "Eliminar libro" }));

    expect(await screen.findByText(/¿Eliminar/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Eliminar definitivamente" })).toBeInTheDocument();
  });
});
