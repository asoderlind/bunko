import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: proxy /api and /admin to Django so the SPA is same-origin,
// which keeps session cookies + CSRF working without CORS.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": { target: "http://web:8000", changeOrigin: false },
      "/admin": { target: "http://web:8000", changeOrigin: false },
      "/static": { target: "http://web:8000", changeOrigin: false },
    },
  },
});
