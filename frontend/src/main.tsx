import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles/globals.css";
import { useDesignStore } from "./stores/designStore";
import { createLogger } from "./utils/logger";

const logger = createLogger("Main");

// Apply design tokens on initial load
useDesignStore.getState().applyToDOM();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);

logger.info("app_initialized");
