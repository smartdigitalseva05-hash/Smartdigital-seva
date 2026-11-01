const CACHE_NAME = "smart-digital-seva-v3";
const BASE = new URL("./", self.location.href).pathname;
const APP_FILES = [
  BASE, BASE + "index.html", BASE + "customer_request.html", BASE + "track.html", BASE + "admin.html",
  BASE + "service_guide.html", BASE + "faq.html",
  BASE + "policies.html", BASE + "404.html",
  BASE + "offline.html", BASE + "manifest.webmanifest", BASE + "icon.svg"
];
self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(APP_FILES)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET" || new URL(request.url).origin !== self.location.origin) return;
  if (request.mode === "navigate") {
    event.respondWith(fetch(request).then(response => {
      const copy = response.clone();
      caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
      return response;
    }).catch(async () => (await caches.match(request)) || (await caches.match(BASE + "offline.html")) || caches.match(BASE + "index.html")));
    return;
  }
  event.respondWith(caches.match(request).then(cached => {
    const fresh = fetch(request).then(response => {
      if (response && response.ok) caches.open(CACHE_NAME).then(cache => cache.put(request, response.clone()));
      return response;
    }).catch(() => cached);
    return cached || fresh;
  }));
});