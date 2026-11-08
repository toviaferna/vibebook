import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";

import { server } from "./server";

beforeAll(() => server.listen());
afterEach(() => {
  server.resetHandlers();
  cleanup();
  window.localStorage.clear();
  delete document.body.dataset.theme;
  delete document.documentElement.dataset.theme;
  delete document.documentElement.dataset.readerPalette;
});
afterAll(() => server.close());
