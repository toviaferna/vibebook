import { useEffect } from "react";

import { isTauriRuntime } from "../lib/tauri";

const EDITABLE_SELECTOR = "input, textarea, select, [contenteditable='true']";

/**
 * WebView2/WebKitGTK show the browser context menu on right click. In the
 * packaged app that leaks "Reload", "Inspect" and other browser actions, so the
 * shell suppresses the native menu except where the user can paste or copy a
 * real text selection.
 */
export function DesktopContextMenu() {
  useEffect(() => {
    if (!isTauriRuntime()) {
      return;
    }
    const guard = (event: MouseEvent) => {
      const target = event.target;
      if (target instanceof Element && target.closest(EDITABLE_SELECTOR)) {
        return;
      }
      if (window.getSelection()?.toString().trim()) {
        return;
      }
      event.preventDefault();
    };
    window.addEventListener("contextmenu", guard);
    return () => window.removeEventListener("contextmenu", guard);
  }, []);

  return null;
}
