# PWA Synap — Documentación Operativa

## Arquitectura

Synap implementa PWA a nivel intermedio, **solo para dispositivos móviles** (feature flag via `DeviceDetectionMiddleware`).

```
Navegador (móvil)
  ├── /manifest.json  ← Vista Django (core.views.pwa_views.serve_manifest)
  ├── /sw.js          ← Vista Django (core.views.pwa_views.serve_sw)
  ├── /offline/       ← TemplateView (theme/templates/offline.html)
  └── /static/*       ← WhiteNoise (assets cacheados por el SW)
```

En desktop, el navegador no recibe meta tags PWA ni registra el Service Worker.

---

## Archivos creados/modificados

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `theme/static/manifest.json` | Nuevo | Web App Manifest completo |
| `theme/static/sw.js` | Nuevo | Service Worker (cache-first + network-first) |
| `theme/templates/offline.html` | Nuevo | Página offline autocontenida |
| `core/views/pwa_views.py` | Nuevo | Vistas `serve_sw` y `serve_manifest` |
| `django_project/urls.py` | Modificado | Rutas `/sw.js`, `/manifest.json`, `/offline/` |
| `theme/templates/base_app.html` | Modificado | Bloque PWA condicional `{% if request.is_mobile %}` |
| `theme/static/img/pwa/` | Nuevo dir | Directorio para iconos (pendiente generarlos) |
| `core/tests/test_pwa.py` | Nuevo | 62 tests automatizados |

---

## Estrategias de caché del Service Worker

### Cache-First (assets estáticos)

Aplica a requests GET que coincidan con:
- `/static/css/`, `/static/js/`, `/static/fonts/`, `/static/img/`
- CDNs: `cdn.tailwindcss.com`, `unpkg.com`, `cdn.jsdelivr.net`, `fonts.googleapis.com`, `fonts.gstatic.com`

Primero busca en caché; si no existe, va a red y guarda en caché.

### Network-First (navegación HTML)

Aplica a requests de navegación (`request.mode === 'navigate'`).

Primero intenta red; si falla, busca en caché; si no hay caché, sirve `/offline/`.

### Exclusiones (nunca se interceptan)

- URLs con `/admin/`, `/api/`, `/logout/`
- Requests que no sean GET (POST, PUT, DELETE, etc.)

---

## Versión del caché

La constante `CACHE_VERSION` en `theme/static/sw.js` controla el versionado:

```javascript
const CACHE_VERSION = 'v1';
```

### Forzar actualización en producción

1. Editar `theme/static/sw.js`, cambiar `CACHE_VERSION` (ej. `'v2'`).
2. Ejecutar collectstatic:
   ```bash
   docker exec Synap_app python manage.py collectstatic --noinput
   ```
3. El navegador detecta el cambio byte-a-byte en `/sw.js`.
4. El evento `activate` del nuevo SW borra cachés antiguos automáticamente.

---

## Verificación post-deploy

```bash
# Service Worker
curl -I https://synap.administranet.com.ar/sw.js
# Esperar: 200, Content-Type: application/javascript, Cache-Control: no-cache

# Manifest
curl -I https://synap.administranet.com.ar/manifest.json
# Esperar: 200, Content-Type: application/manifest+json

# Página offline
curl -I https://synap.administranet.com.ar/offline/
# Esperar: 200, Content-Type: text/html
```

---

## Feature flag por dispositivo

El bloque PWA en `base_app.html` está envuelto en:

```html
{% if request.is_mobile %}
  <!-- meta tags PWA, manifest, apple-touch-icon -->
{% endif %}

{% if request.is_mobile %}
  <script>navigator.serviceWorker.register('/sw.js', { scope: '/' })...</script>
{% endif %}
```

`request.is_mobile` es inyectado por `DeviceDetectionMiddleware` con detección en dos capas: (1) cookie `device_hint` (valores `mobile` | `desktop`) seteada por el script en cliente; (2) User-Agent (PHONE_PATTERNS y TABLET_PATTERNS). Se acepta también la cookie legacy `synap_prefer_mobile` (`1`/`0`). Ver **docs/general/DETECCION_TABLET_IPAD_ANDROID.md**.

| Dispositivo | PWA activa |
|-------------|-----------|
| Android phone/tablet (UA detectable) | Sí |
| iPhone (UA con "iPhone") | Sí |
| iPad con UA tipo Macintosh | Sí, tras cookie device_hint=mobile (script detecta MacIntel + maxTouchPoints) |
| Desktop | No |

### Tablet / iPad (detección en dos capas)

En iPadOS 13+, el UA en servidor es tipo Macintosh; el script en `base_app.html` detecta iPad con `navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1`, setea `device_hint=mobile` y recarga. El siguiente request ya llega con la cookie y el middleware marca `request.is_mobile = True`. La cookie tiene validez de 1 día. Opcionalmente el cliente puede llamar a POST `/set-device-hint/` para actualizar la cookie sin recarga.

---

## Iconos pendientes

Generar iconos desde un PNG fuente de al menos 512x512 y colocarlos en `theme/static/img/pwa/`:

```
icon-72.png   icon-96.png   icon-128.png  icon-144.png
icon-152.png  icon-180.png  icon-192.png  icon-384.png  icon-512.png
```

### Herramientas recomendadas

- **pwa-asset-generator (npm):**
  ```bash
  npx pwa-asset-generator logo-512.png theme/static/img/pwa/ --icon-only --type png
  ```
- **RealFaviconGenerator:** https://realfavicongenerator.net/

---

## Headers del servidor

| URL | Cache-Control | Nota |
|-----|--------------|------|
| `/sw.js` | `no-cache` | La vista Django lo envía; si hay nginx/proxy, no sobrescribir |
| `/manifest.json` | `public, max-age=86400` | Cache de 24h |
| `/offline/` | Sin restricción especial | |

Si se usa nginx como proxy reverso, agregar:

```nginx
location = /sw.js {
    proxy_pass http://gunicorn;
    proxy_set_header Cache-Control "no-cache";
}
```

---

## Tests

```bash
docker exec Synap_app python manage.py test core.tests.test_pwa --verbosity=2
```

62 tests organizados en 8 grupos:

| Grupo | Tests | Qué verifica |
|-------|-------|-------------|
| URLs | 6 | Resolución de `/sw.js`, `/manifest.json`, `/offline/` |
| Service Worker | 11 | Vista, content-type, cache-control, contenido del SW |
| Manifest | 14 | Vista, JSON válido, campos obligatorios, iconos |
| Offline | 6 | Página offline autocontenida |
| Template source | 7 | `base_app.html` tiene condicional y meta tags |
| Feature flag | 7 | Mobile SI vs Desktop NO (renderizado condicional) |
| Static files | 4 | Archivos fuente existen en `theme/static/` |
| Integración | 4 | CSRF, admin, redirect raíz siguen OK |
| HTTPS | 3 | SSL redirect, HSTS, proxy header |

---

## Limitaciones iOS Safari

- El caché del SW en iOS es más agresivo; puede requerir cerrar y reabrir la app para actualizar.
- Las notificaciones push no son soportadas en iOS < 16.4 (fuera del alcance).
- El splash screen en iOS requiere `apple-touch-startup-image` con media queries por tamaño de dispositivo (implementación futura).
- El almacenamiento del SW en iOS tiene límites más bajos que Android.

---

## Referencia

- Especificación completa: `docs/general/ESPEC_PWA_SYNAP.md`
- Tests: `core/tests/test_pwa.py`
- Middleware de dispositivos: `core/middleware/base_middleware.py` (clase `DeviceDetectionMiddleware`)
