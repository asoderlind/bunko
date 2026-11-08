import adapter from "@sveltejs/adapter-static";
import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    // Pure client-side app: Django serves the built files, so there is no Node
    // server. SPA fallback keeps deep links like /notes/<id> working.
    adapter: adapter({
      pages: "build",
      assets: "build",
      fallback: "index.html",
      strict: false,
    }),
    alias: {
      $lib: "./src/lib",
    },
  },
};

export default config;
