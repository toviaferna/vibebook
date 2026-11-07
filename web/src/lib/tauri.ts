import { invoke } from "@tauri-apps/api/core";

import { configureApi } from "../api/client";

interface DesktopApiConfig {
  baseUrl: string;
  token: string;
}

export function isTauriRuntime(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

export async function initializeDesktopApi(): Promise<void> {
  if (!isTauriRuntime()) {
    return;
  }
  const config = await invoke<DesktopApiConfig>("api_config");
  configureApi(config);
}
