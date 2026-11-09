import { lazy, type ReactNode, Suspense } from "react";
import { createHashRouter } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { LibraryPage } from "./features/library/LibraryPage";

const ImportPage = lazy(async () => ({
  default: (await import("./features/import/ImportPage")).ImportPage,
}));
const BookDetailPage = lazy(async () => ({
  default: (await import("./features/library/BookDetailPage")).BookDetailPage,
}));
const StudioPage = lazy(async () => ({
  default: (await import("./features/studio/StudioPage")).StudioPage,
}));
const SettingsPage = lazy(async () => ({
  default: (await import("./features/settings/SettingsPage")).SettingsPage,
}));
const ReaderPage = lazy(async () => ({
  default: (await import("./features/reader/ReaderPage")).ReaderPage,
}));

function RouteLoading() {
  return (
    <div className="page page--narrow">
      <div className="page-loading">
        <div className="skeleton skeleton--title" />
        <div className="skeleton skeleton--card" />
      </div>
    </div>
  );
}

function route(element: ReactNode) {
  return <Suspense fallback={<RouteLoading />}>{element}</Suspense>;
}

export const router = createHashRouter([
  { path: "/books/:id/read", element: route(<ReaderPage />) },
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <LibraryPage /> },
      { path: "import", element: route(<ImportPage />) },
      { path: "books/:id", element: route(<BookDetailPage />) },
      { path: "books/:id/studio", element: route(<StudioPage />) },
      { path: "settings", element: route(<SettingsPage />) },
      {
        path: "*",
        element: (
          <div className="page page--narrow">
            <p className="eyebrow">404</p>
            <h1 className="page-title">Esta página no existe.</h1>
          </div>
        ),
      },
    ],
  },
]);
