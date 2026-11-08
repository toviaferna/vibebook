import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { sampleBookmarks, sampleChapter, sampleManifest } from "../../test/fixtures";
import { server } from "../../test/server";
import { renderRoute } from "../../test/utils";
import { ReaderPage } from "./ReaderPage";

vi.mock("./original/OriginalEpubView", () => ({
  OriginalEpubView: () => <div data-testid="original-epub-mock" />,
}));

describe("ReaderPage", () => {
  it("muestra el capítulo, el índice y el reproductor", async () => {
    renderRoute("/books/lazarillo-1234/read", "/books/:id/read", <ReaderPage />);

    expect(await screen.findByRole("heading", { name: "Capítulo 1" })).toBeInTheDocument();
    expect(screen.getByText("Hola,")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Índice del libro" })).toBeInTheDocument();
    expect(screen.getByText("Parte I")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reproducir" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Seguir/ })).toBeInTheDocument();
  });

  it("abre el índice en un diálogo", async () => {
    const user = userEvent.setup();
    renderRoute("/books/lazarillo-1234/read", "/books/:id/read", <ReaderPage />);

    await screen.findByRole("heading", { name: "Capítulo 1" });
    await user.click(screen.getByRole("button", { name: "Abrir índice" }));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getAllByText("Capítulo 1").length).toBeGreaterThan(0);
  });

  it("muestra un libro importado sin reproductor", async () => {
    server.use(
      http.get("*/api/books/:id/manifest", () =>
        HttpResponse.json({ ...sampleManifest, status: "imported" }),
      ),
      http.get("*/api/books/:id/chapters/:index", () =>
        HttpResponse.json({
          ...sampleChapter,
          audio_ready: false,
          duration_ms: null,
          timing: null,
        }),
      ),
    );
    renderRoute("/books/lazarillo-1234/read", "/books/:id/read", <ReaderPage />);

    expect(await screen.findByRole("heading", { name: "Capítulo 1" })).toBeInTheDocument();
    expect(screen.getByText("Hola, mundo. Esta es una prueba.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reproducir" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Convertir a audiolibro" })).toBeInTheDocument();
  });

  it("permite cambiar el tema de lectura", async () => {
    const user = userEvent.setup();
    renderRoute("/books/lazarillo-1234/read", "/books/:id/read", <ReaderPage />);

    await screen.findByRole("heading", { name: "Capítulo 1" });
    await user.click(screen.getByRole("button", { name: "Ajustes de lectura" }));
    await user.click(screen.getByRole("radio", { name: "Noche" }));

    expect(document.body.dataset.theme).toBe("night");
  });

  it("permite alternar entre texto y EPUB original", async () => {
    const user = userEvent.setup();
    renderRoute("/books/lazarillo-1234/read", "/books/:id/read", <ReaderPage />);

    await screen.findByRole("heading", { name: "Capítulo 1" });
    await user.click(screen.getByRole("button", { name: "Original" }));

    expect(screen.getByTestId("original-epub-mock")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Texto" }));
    expect(screen.queryByTestId("original-epub-mock")).not.toBeInTheDocument();
  });

  it("busca dentro del libro y abre el resultado", async () => {
    const user = userEvent.setup();
    renderRoute("/books/lazarillo-1234/read", "/books/:id/read", <ReaderPage />);

    await screen.findByRole("heading", { name: "Capítulo 1" });
    await user.click(screen.getByRole("button", { name: "Buscar en el libro" }));
    await user.type(screen.getByRole("searchbox", { name: "Texto a buscar" }), "Hola");

    expect(await screen.findByText("Hola, mundo. Esta es una prueba.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Cap\. 1/ }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("agrega un marcador desde el lector", async () => {
    let items = [...sampleBookmarks.items];
    server.use(
      http.get("*/api/books/:id/bookmarks", () => HttpResponse.json({ items })),
      http.post("*/api/books/:id/bookmarks", async ({ request }) => {
        const input = (await request.json()) as {
          chapter_index: number;
          position_ms: number;
          note?: string | null;
        };
        const bookmark = {
          id: 2,
          book_id: "lazarillo-1234",
          chapter_index: input.chapter_index,
          position_ms: input.position_ms,
          note: input.note ?? null,
          created_at: "2026-11-07T10:00:00+00:00",
        };
        items = [...items, bookmark];
        return HttpResponse.json(bookmark, { status: 201 });
      }),
    );
    const user = userEvent.setup();
    renderRoute("/books/lazarillo-1234/read", "/books/:id/read", <ReaderPage />);

    await screen.findByRole("heading", { name: "Capítulo 1" });
    await user.click(screen.getByRole("button", { name: "Marcadores" }));
    expect(await screen.findByText("Marcador de prueba")).toBeInTheDocument();

    await user.type(screen.getByRole("textbox", { name: "Nota del marcador" }), "Nuevo");
    await user.click(screen.getByRole("button", { name: "Guardar" }));

    expect(await screen.findByText("Nuevo")).toBeInTheDocument();
  });
});
