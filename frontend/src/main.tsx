import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles/globals.css";
import { useDesignStore } from "./stores/designStore";
import { useSettingsStore } from "./stores/settingsStore";
import { createLogger } from "./utils/logger";

const logger = createLogger("Main");

// Apply dark mode class from persisted settings, THEN apply theme
// (order matters: theme.applyToDOM reads the dark class to pick neutrals)
const initialTheme = useSettingsStore.getState().theme;
document.documentElement.classList.toggle("dark", initialTheme === "dark");
useDesignStore.getState().applyToDOM();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);

logger.info("app_initialized");
