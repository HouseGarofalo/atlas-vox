/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// Atlas Vox backend runs on port 8100 (configured in .env PORT=8100)
const backendUrl = "http://localhost:8100";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3100,
    strictPort: false,
    proxy: {
      "/api/": {
        target: backendUrl,
        changeOrigin: true,
      },
      "/v1/": {
        target: backendUrl,
        changeOrigin: true,
      },
      "/mcp/": {
        target: backendUrl,
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    css: true,
    exclude: ["e2e/**", "node_modules/**"],
  },
});
