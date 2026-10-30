const CACHE_NAME = 'wick-mirror-v1';

// Optional: Add core files you want to guarantee are cached immediately on load
const PRECACHE_ASSETS = [
  './',
  './github/workflows/deploy.yml',
  './index.html',
  './.gitignore',
  './README.md',
  './patch.py',
  './robots.txt',
];

// 1. Install Event: Pre-cache critical assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// 2. Activate Event: Clean up old caches if the cache name changes
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            return caches.delete(cache);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// 3. Fetch Event: Serve from cache, fallback to network, and automatically cache new files
self.addEventListener('fetch', (event) => {
  // Only handle GET requests (GitHub Pages/Static sites use GET)
  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        // Return the cached file immediately
        return cachedResponse;
      }

      // If not in cache, fetch from the network
      return fetch(event.request).then((networkResponse) => {
        // Check if we received a valid response
        if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
          return networkResponse;
        }

        // Clone the response (streams can only be read once)
        const responseToCache = networkResponse.clone();

        // Automatically save the newly fetched file into the offline cache
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, responseToCache);
        });

        return networkResponse;
      }).catch(() => {
        // Optional: Return a fallback offline page if network fails and asset isn't cached
      });
    })
  );
});
