import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { sampleBook } from "../../test/fixtures";
import { renderWithProviders } from "../../test/utils";
import { CoverSearchDialog } from "./CoverSearchDialog";

describe("CoverSearchDialog", () => {
  it("busca y aplica una portada", async () => {
    const onOpenChange = vi.fn();
    renderWithProviders(
      <CoverSearchDialog book={sampleBook} open onOpenChange={onOpenChange} />,
      `/books/${sampleBook.id}`,
    );

    expect(await screen.findByText(/Open Library/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Portada de/ }));

    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
  });
});
