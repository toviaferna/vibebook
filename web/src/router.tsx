import { createHashRouter } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { ImportPage } from "./features/import/ImportPage";
import { BookDetailPage } from "./features/library/BookDetailPage";
import { LibraryPage } from "./features/library/LibraryPage";
import { SettingsPage } from "./features/settings/SettingsPage";
import { StudioPage } from "./features/studio/StudioPage";

export const router = createHashRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <LibraryPage /> },
      { path: "import", element: <ImportPage /> },
      { path: "books/:id", element: <BookDetailPage /> },
      { path: "books/:id/studio", element: <StudioPage /> },
      { path: "settings", element: <SettingsPage /> },
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
