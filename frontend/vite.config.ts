import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    // Dev: same-origin proxy to the API so the session cookie works.
    proxy: {
      "/api": { target: "http://web:8000", changeOrigin: false },
      "/admin": { target: "http://web:8000", changeOrigin: false },
      "/static": { target: "http://web:8000", changeOrigin: false },
    },
  },
});
