import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderWithProviders } from "../../test/utils";
import { SettingsPage } from "./SettingsPage";

describe("SettingsPage", () => {
  it("muestra las preferencias y guarda un tema", async () => {
    const user = userEvent.setup();
    renderWithProviders(<SettingsPage />);

    expect(await screen.findByText("Preferencias del taller")).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: /Noche/ }));

    expect(document.body.dataset.theme).toBe("night");
  });
});
