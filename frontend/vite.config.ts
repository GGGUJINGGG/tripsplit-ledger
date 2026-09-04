/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon-32x32.png", "apple-touch-icon.png"],
      manifest: {
        name: "TripSplit Ledger",
        short_name: "TripSplit",
        description: "Split trip expenses and settle up with your travel companions",
        theme_color: "#2563a8",
        background_color: "#f4f6f8",
        display: "standalone",
        start_url: "/",
        icons: [
          {
            src: "pwa-192x192.png",
            sizes: "192x192",
            type: "image/png",
          },
          {
            src: "pwa-512x512.png",
            sizes: "512x512",
            type: "image/png",
          },
          {
            src: "maskable-icon-512x512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        // Precache only the built app shell (JS/CSS/HTML/icons) — API
        // requests are never intercepted or cached here, so trip data,
        // balances, and settlements always come straight from the
        // network and can't go stale behind a service worker.
        globPatterns: ["**/*.{js,css,html,png,svg,ico}"],
        navigateFallbackDenylist: [/^\/api\//],
      },
    }),
  ],
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
