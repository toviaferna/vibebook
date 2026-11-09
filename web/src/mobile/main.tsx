import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "../styles/tokens.css";
import "../styles/base.css";
import "./mobile.css";
import { MobileReaderApp } from "./MobileReaderApp";

const root = document.getElementById("root");
if (!root) {
  throw new Error("Missing #root element");
}

createRoot(root).render(
  <StrictMode>
    <MobileReaderApp />
  </StrictMode>,
);
