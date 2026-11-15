import { render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { isTauriRuntime } from "../lib/tauri";
import { DesktopContextMenu } from "./DesktopContextMenu";

vi.mock("../lib/tauri", () => ({
  isTauriRuntime: vi.fn(() => true),
}));

function contextMenu(target: EventTarget): MouseEvent {
  const event = new MouseEvent("contextmenu", { bubbles: true, cancelable: true });
  target.dispatchEvent(event);
  return event;
}

describe("DesktopContextMenu", () => {
  afterEach(() => {
    document.body.replaceChildren();
    vi.mocked(isTauriRuntime).mockReturnValue(true);
  });

  it("suprime el menú del navegador en la app empaquetada", () => {
    render(<DesktopContextMenu />);

    expect(contextMenu(document.body).defaultPrevented).toBe(true);
  });

  it("deja el menú nativo en campos editables", () => {
    render(<DesktopContextMenu />);
    const input = document.createElement("input");
    document.body.append(input);

    expect(contextMenu(input).defaultPrevented).toBe(false);
  });

  it("no toca el menú del navegador fuera de Tauri", () => {
    vi.mocked(isTauriRuntime).mockReturnValue(false);
    render(<DesktopContextMenu />);

    expect(contextMenu(document.body).defaultPrevented).toBe(false);
  });
});
