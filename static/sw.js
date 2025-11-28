 final/static/sw.js
const CACHE_NAME = 'puo-app-v1';
const PRECACHE_URLS = [
  '/', // root
  '/static/manifest.json',
  '/static/assets/css/main.css',
  '/static/assets/js/vendors/color-modes.js',
  '/static/assets/imgs/template/favicon-gradient.svg'
];

// Install: pre-cache basic shell
self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE_URLS))
  );
});

// Activate: cleanup old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.map(k => {
        if (k !== CACHE_NAME) return caches.delete(k);
      }))
    ).then(() => self.clients.claim())
  );
});

// Fetch: cache-first for precached, network-fallback for others
self.addEventListener('fetch', event => {
  const request = event.request;
  // Only handle GET
  if (request.method !== 'GET') return;
  event.respondWith(
    caches.match(request).then(cachedResp => {
      if (cachedResp) return cachedResp;
      return fetch(request).then(networkResp => {
        // Optionally cache same-origin responses
        if (networkResp && networkResp.ok && request.url.startsWith(self.location.origin)) {
          const copy = networkResp.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
        }
        return networkResp;
      }).catch(() => {
        // fallback: return cached root or nothing
        return caches.match('/');
      });
    })
  );
});