const PRELOAD_RELOAD_KEY = "aespa_preload_reload";

export function recoverFromPreloadError(
  event: Event,
  {
    storage = window.sessionStorage,
    reload = () => window.location.reload(),
  }: { storage?: Storage; reload?: () => void } = {},
) {
  event.preventDefault();
  if (storage.getItem(PRELOAD_RELOAD_KEY)) return;
  storage.setItem(PRELOAD_RELOAD_KEY, "1");
  reload();
}

/** Development uses Vite directly; a cached production shell must not intercept HMR. */
export function registerServiceWorker() {
  if (!import.meta.env.PROD || !("serviceWorker" in navigator)) return;

  window.addEventListener("vite:preloadError", recoverFromPreloadError);

  const register = () => {
    window.sessionStorage.removeItem(PRELOAD_RELOAD_KEY);
    navigator.serviceWorker.register("/sw.js").catch((error) => {
      console.warn("Offline support could not be registered", error);
    });
  };
  if (document.readyState === "complete") register();
  else window.addEventListener("load", register, { once: true });
}
