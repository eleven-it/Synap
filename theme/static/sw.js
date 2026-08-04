/**
 * Service Worker — Synap PWA
 *
 * Estrategias:
 *   Cache-First  → assets estáticos (/static/, CDNs de Tailwind/Alpine/Fonts)
 *   Network-First → navegación HTML (con fallback a /offline/)
 *
 * Para forzar actualización de caché en producción:
 *   1. Cambiar CACHE_VERSION abajo (ej. 'v2')
 *   2. Ejecutar collectstatic
 *   3. El navegador detecta el cambio y activa el nuevo SW
 */

const CACHE_VERSION = 'v3';
const STATIC_CACHE  = `synap-static-${CACHE_VERSION}`;
const PAGES_CACHE   = `synap-pages-${CACHE_VERSION}`;
const OFFLINE_URL   = '/offline/';

/** Shell HTML conteo inventario físico (Nivel A). APIs /stock/api/ no se cachean aquí. */
const CONTEO_SHELL_URLS = [
  '/stock/conteo/',
  '/offline/',
];

const EXCLUDED_PATHS = ['/admin/', '/api/', '/logout/'];

function isStaticAsset(url) {
  const path = new URL(url).pathname;
  return (
    path.startsWith('/static/css/') ||
    path.startsWith('/static/js/') ||
    path.startsWith('/static/fonts/') ||
    path.startsWith('/static/img/')
  );
}

function isCDNAsset(url) {
  const hostname = new URL(url).hostname;
  return (
    hostname === 'cdn.tailwindcss.com' ||
    hostname === 'unpkg.com' ||
    hostname === 'cdn.jsdelivr.net' ||
    hostname === 'fonts.googleapis.com' ||
    hostname === 'fonts.gstatic.com'
  );
}

function isExcluded(url) {
  const path = new URL(url).pathname;
  return EXCLUDED_PATHS.some(function(excluded) {
    return path.indexOf(excluded) !== -1;
  });
}

// ── install ──────────────────────────────────────────────────────────────
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(PAGES_CACHE).then(function(cache) {
      return cache.addAll(CONTEO_SHELL_URLS);
    }).then(function() {
      return self.skipWaiting();
    })
  );
});

// ── activate ─────────────────────────────────────────────────────────────
self.addEventListener('activate', function(event) {
  var keepCaches = [STATIC_CACHE, PAGES_CACHE];
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(name) {
          if (keepCaches.indexOf(name) === -1) {
            return caches.delete(name);
          }
        })
      );
    }).then(function() {
      return self.clients.claim();
    })
  );
});

// ── fetch ────────────────────────────────────────────────────────────────
self.addEventListener('fetch', function(event) {
  var request = event.request;

  if (request.method !== 'GET') {
    return;
  }

  if (isExcluded(request.url)) {
    return;
  }

  // Cache-First: assets estáticos y CDN
  if (isStaticAsset(request.url) || isCDNAsset(request.url)) {
    event.respondWith(
      caches.open(STATIC_CACHE).then(function(cache) {
        return cache.match(request).then(function(cached) {
          if (cached) {
            return cached;
          }
          return fetch(request).then(function(networkResponse) {
            if (networkResponse && networkResponse.status === 200) {
              cache.put(request, networkResponse.clone());
            }
            return networkResponse;
          });
        });
      })
    );
    return;
  }

  // Network-First: navegación HTML
  if (request.mode === 'navigate' || request.headers.get('accept').indexOf('text/html') !== -1) {
    event.respondWith(
      fetch(request).then(function(networkResponse) {
        if (networkResponse && networkResponse.status === 200) {
          var responseClone = networkResponse.clone();
          caches.open(PAGES_CACHE).then(function(cache) {
            cache.put(request, responseClone);
          });
        }
        return networkResponse;
      }).catch(function() {
        return caches.match(request).then(function(cached) {
          return cached || caches.match(OFFLINE_URL);
        });
      })
    );
    return;
  }
});
