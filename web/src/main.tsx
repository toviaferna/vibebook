import "@fontsource-variable/literata";
import "@fontsource-variable/public-sans";
import "@fontsource/spectral/400.css";
import "@fontsource/spectral/500.css";
import "@fontsource/spectral/600.css";
import "@fontsource/atkinson-hyperlegible/400.css";
import "@fontsource/atkinson-hyperlegible/700.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { ThemeProvider } from "./components/ThemeProvider";
import { initializeDesktopApi } from "./lib/tauri";
import { router } from "./router";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/app.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5_000,
    },
  },
});

const root = document.getElementById("root");
if (!root) {
  throw new Error("Missing #root element");
}

const container = createRoot(root);

async function bootstrap() {
  try {
    await initializeDesktopApi();
  } catch (error) {
    renderStartupError(error);
    return;
  }
  container.render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <RouterProvider router={router} />
        </ThemeProvider>
      </QueryClientProvider>
    </StrictMode>,
  );
}

function renderStartupError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error);
  container.render(
    <div className="startup-error" role="alert">
      <p className="eyebrow">Vibebook Desktop</p>
      <h1>No se pudo iniciar el motor local.</h1>
      <p className="muted">
        El sidecar de Python no respondió. Cerrá y volvé a abrir la aplicación; si el problema
        sigue, revisá el log indicado abajo.
      </p>
      <pre>{message}</pre>
    </div>,
  );
}

void bootstrap();
