import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import { sampleSettings } from "../test/fixtures";
import { server } from "../test/server";
import { renderWithProviders } from "../test/utils";
import { useThemeMode } from "./ThemeProvider";

function ThemeProbe() {
  const { mode, setMode } = useThemeMode();
  return (
    <div>
      <span>{mode}</span>
      <button type="button" onClick={() => setMode("dark")}>
        Oscuro
      </button>
    </div>
  );
}

describe("ThemeProvider", () => {
  it("persiste el tema elegido en los ajustes", async () => {
    const updates: unknown[] = [];
    server.use(
      http.put("*/api/settings", async ({ request }) => {
        updates.push(await request.json());
        return HttpResponse.json({ ...sampleSettings, theme_mode: "dark" });
      }),
    );
    const user = userEvent.setup();
    renderWithProviders(<ThemeProbe />);

    await user.click(await screen.findByRole("button", { name: "Oscuro" }));

    await waitFor(() => {
      expect(updates).toContainEqual(expect.objectContaining({ theme_mode: "dark" }));
    });
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
});
