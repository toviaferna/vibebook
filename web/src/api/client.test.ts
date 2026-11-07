import { HttpResponse, http } from "msw";

import { server } from "../test/server";
import { type ApiError, api, apiUrl, authHeaders, configureApi } from "./client";

describe("api client", () => {
  it("lista libros", async () => {
    const result = await api.listBooks();

    expect(result.total).toBe(1);
    expect(result.items[0].title).toBe("El Lazarillo de Tormes");
  });

  it("convierte errores de API en ApiError", async () => {
    server.use(
      http.get("*/api/books", () =>
        HttpResponse.json(
          { error: { code: "internal_error", message: "Falló el índice." } },
          { status: 500 },
        ),
      ),
    );

    await expect(api.listBooks()).rejects.toMatchObject({
      name: "ApiError",
      code: "internal_error",
      status: 500,
      message: "Falló el índice.",
    } satisfies Partial<ApiError>);
  });

  it("resuelve URLs de assets", () => {
    expect(apiUrl("/api/books/x/cover")).toBe("/api/books/x/cover");
    expect(apiUrl("/books/x/cover")).toBe("/api/books/x/cover");
  });

  it("usa la conexión del escritorio y su token", () => {
    configureApi({ baseUrl: "http://127.0.0.1:9999", token: "abc 123" });

    expect(apiUrl("/api/books/x/cover")).toBe(
      "http://127.0.0.1:9999/api/books/x/cover?token=abc%20123",
    );
    expect(authHeaders()).toEqual({ "X-Vibebook-Token": "abc 123" });

    configureApi({ baseUrl: "/api", token: "" });
    expect(apiUrl("/api/books/x/cover")).toBe("/api/books/x/cover");
  });
});
