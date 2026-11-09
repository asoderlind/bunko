import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  // An empty prefix also exposes process environment variables, so Compose can
  // set VITE_API_PROXY without a .env file inside the container.
  const env = loadEnv(mode, ".", "");
  // Compose reaches the API as `web:8000`. When running Vite on the host, set
  // VITE_API_PROXY=http://127.0.0.1:8000 (or your BIND_HOST).
  const apiTarget = env.VITE_API_PROXY ?? "http://web:8000";

  return {
    plugins: [sveltekit()],
    server: {
      host: "0.0.0.0",
      port: 5173,
      // Bind mounts do not reliably emit inotify events in every Docker setup
      // (notably Docker Desktop), so poll for changes in dev.
      watch: {
        usePolling: true,
        // Production build output lives inside the bind mount; watching it
        // makes the dev server reload whenever someone runs `pnpm build`.
        ignored: ["**/build/**"],
      },
      // Dev: same-origin proxy to the API so the session cookie works.
      proxy: {
        "/api": { target: apiTarget, changeOrigin: false },
        "/admin": { target: apiTarget, changeOrigin: false },
        "/static": { target: apiTarget, changeOrigin: false },
      },
    },
  };
});
