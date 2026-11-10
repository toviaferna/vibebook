import { clearMediaTickets, mediaUrl } from "./media";

describe("media tickets", () => {
  beforeEach(() => clearMediaTickets());

  it("pide un ticket y lo reutiliza mientras no expira", async () => {
    const first = await mediaUrl("libro-1", "epub", "/api/books/libro-1/epub");
    const second = await mediaUrl("libro-1", "epub", "/api/books/libro-1/epub");

    expect(first).toBe("/api/books/libro-1/epub?ticket=test-ticket");
    expect(second).toBe(first);
  });

  it("separa la caché por libro, tipo y ruta", async () => {
    const epub = await mediaUrl("libro-1", "epub", "/api/books/libro-1/epub");
    const cover = await mediaUrl("libro-1", "cover", "/api/books/libro-1/cover");

    expect(epub).not.toBe(cover);
  });
});
