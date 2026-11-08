/**
 * Detect a new deployment while the app is open.
 *
 * SvelteKit emits hashed chunk names, so a tab left open across a deploy holds
 * references to files that no longer exist and fails on the next lazy import.
 * Poll index.html (which Django serves with no-cache) and compare the build
 * hash; when it changes, reload once.
 */
const CHECK_MS = 5 * 60 * 1000;

export function watchDeploy() {
  if (typeof window === "undefined") return;

  let currentBuild: string | null = null;
  let reloading = false;

  async function readBuild(): Promise<string | null> {
    try {
      const res = await fetch("/", { cache: "no-store" });
      const html = await res.text();
      // SvelteKit inlines the build id in the start script path.
      const m = html.match(/immutable\/entry\/start\.([A-Za-z0-9_-]+)\.js/);
      return m ? m[1] : null;
    } catch {
      return null;
    }
  }

  void (async () => {
    currentBuild = await readBuild();
    setInterval(async () => {
      if (reloading || document.visibilityState !== "visible") return;
      const next = await readBuild();
      if (next && currentBuild && next !== currentBuild) {
        reloading = true;
        window.location.reload();
      }
    }, CHECK_MS);
  })();
}
