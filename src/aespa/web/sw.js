const CACHE = "aespa-v6";

// Versioned assets (cache-busted by ?v=... query param) — cache aggressively
const STATIC_EXTS = [".js", ".css", ".png", ".ico", ".json"];

function isStaticAsset(url) {
  const u = new URL(url);
  return STATIC_EXTS.some((ext) => u.pathname.endsWith(ext));
}

function isApiCall(url) {
  return new URL(url).pathname.startsWith("/api/");
}

// Install: pre-cache the shell assets
self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE).then((cache) =>
      cache.addAll(["/", "/icon.png", "/manifest.json"])
    )
  );
});

// Activate: drop old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))
        )
      )
      .then(() => self.clients.claim())
  );
});

// Fetch strategy:
//   API calls      → network only (always fresh)
//   Static assets  → cache first, then network (they have ?v= cache busters)
//   Navigation     → network first, fall back to cached shell
self.addEventListener("fetch", (event) => {
  const { request } = event;

  // Only handle GET requests
  if (request.method !== "GET") return;

  const url = request.url;

  // API — always go to the network
  if (isApiCall(url)) return;

  // Versioned static assets — serve from cache if present, else fetch & cache
  if (isStaticAsset(url)) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((response) => {
            if (response.ok) {
              const clone = response.clone();
              caches.open(CACHE).then((c) => c.put(request, clone));
            }
            return response;
          })
      )
    );
    return;
  }

  // Navigation / HTML — network first, fall back to cached index
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE).then((c) => c.put(request, clone));
        }
        return response;
      })
      .catch(() => caches.match(request).then((r) => r || caches.match("/")))
  );
});
