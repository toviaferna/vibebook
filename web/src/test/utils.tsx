import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

interface TestProvidersProps {
  client: QueryClient;
  children: ReactNode;
  route: string;
}

function TestProviders({ client, children, route }: TestProvidersProps) {
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

function makeClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

export function renderWithProviders(ui: ReactElement, route = "/") {
  const queryClient = makeClient();
  return {
    queryClient,
    ...render(
      <TestProviders client={queryClient} route={route}>
        {ui}
      </TestProviders>,
    ),
  };
}

export function renderRoute(path: string, pattern: string, element: ReactElement) {
  const queryClient = makeClient();
  return {
    queryClient,
    ...render(
      <TestProviders client={queryClient} route={path}>
        <Routes>
          <Route path={pattern} element={element} />
        </Routes>
      </TestProviders>,
    ),
  };
}
