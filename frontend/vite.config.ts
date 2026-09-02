/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  test: {
    environment: "jsdom",
    // Needed even though tests import describe/it/expect explicitly:
    // @testing-library/react's auto-cleanup between tests only wires
    // itself up when it detects a global afterEach.
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
