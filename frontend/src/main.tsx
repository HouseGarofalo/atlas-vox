import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles/globals.css";
import { useDesignStore } from "./stores/designStore";
import { useSettingsStore } from "./stores/settingsStore";
import { createLogger } from "./utils/logger";

const logger = createLogger("Main");

// Theme class is set by the inline shim in index.html BEFORE this module
// loads, so first paint uses the correct palette. Here we reconcile: if
// the DOM and the persisted store disagree (e.g. prefers-color-scheme
// fallback applied but the user had explicitly saved a different theme),
// trust the store and sync the class. Then apply the theme palette.
const initialTheme = useSettingsStore.getState().theme;
const domIsDark = document.documentElement.classList.contains("dark");
if (domIsDark !== (initialTheme === "dark")) {
  document.documentElement.classList.toggle("dark", initialTheme === "dark");
  document.documentElement.setAttribute("data-theme", initialTheme);
}
useDesignStore.getState().applyToDOM();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);

logger.info("app_initialized");
