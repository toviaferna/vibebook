import { screen } from "@testing-library/react";
import axe from "axe-core";

import { renderRoute } from "../../test/utils";
import { ReaderPage } from "./ReaderPage";

describe("ReaderPage accesibilidad", () => {
  it("no tiene violaciones serious ni critical", async () => {
    renderRoute("/books/lazarillo-1234/read", "/books/:id/read", <ReaderPage />);

    await screen.findByRole("heading", { name: "Capítulo 1" });
    const results = await axe.run(document.body, {
      rules: {
        "color-contrast": { enabled: false },
      },
    });
    const serious = results.violations.filter(
      (violation) => violation.impact === "serious" || violation.impact === "critical",
    );

    expect(
      serious.map((violation) => ({
        id: violation.id,
        targets: violation.nodes.map((node) => node.target),
      })),
    ).toEqual([]);
  });
});
