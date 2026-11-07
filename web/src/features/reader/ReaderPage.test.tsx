import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderRoute } from "../../test/utils";
import { ReaderPage } from "./ReaderPage";

describe("ReaderPage", () => {
  it("muestra el capítulo, el índice y el reproductor", async () => {
    renderRoute("/books/lazarillo-1234/read", "/books/:id/read", <ReaderPage />);

    expect(await screen.findByRole("heading", { name: "Capítulo 1" })).toBeInTheDocument();
    expect(screen.getByText("Hola,")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Índice del libro" })).toBeInTheDocument();
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

  it("permite cambiar el tema de lectura", async () => {
    const user = userEvent.setup();
    renderRoute("/books/lazarillo-1234/read", "/books/:id/read", <ReaderPage />);

    await screen.findByRole("heading", { name: "Capítulo 1" });
    await user.click(screen.getByRole("button", { name: "Ajustes de lectura" }));
    await user.click(screen.getByRole("radio", { name: "Noche" }));

    expect(document.body.dataset.theme).toBe("night");
  });
});
