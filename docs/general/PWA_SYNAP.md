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

**`start_url` del manifest:** `/login/`, alineado con la restricción móvil «solo Nivel A» (`MobileLevelAOnlyMiddleware`): en móvil no se debe abrir la app en rutas no adaptadas (p. ej. el dashboard general).

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
| `theme/static/img/pwa/` | Iconos PNG | Generados con `generate_pwa_icons` (ver Fase 0 abajo) |
| `login/templates/login/includes/pwa_head.html` | Nuevo | Manifest + meta PWA en login móvil |
| `login/templates/login/includes/pwa_sw_register.html` | Nuevo | Registro SW en login móvil |
| `login/templates/login/mobile/login_administranet.html` | Modificado | Includes PWA solo si `request.is_mobile` |
| `login/management/commands/generate_pwa_icons.py` | Nuevo | Comando para generar iconos desde logo |
| `core/tests/test_pwa.py` | Nuevo | Tests automatizados PWA (+ login móvil) |
| `core/middleware/mobile_level_a_middleware.py` | Nuevo | En móvil, solo rutas Nivel A + APIs TPV |
| `core/templates/core/mobile_desktop_only.html` | Nuevo | Mensaje 403 móvil (solo escritorio) |
| `docs/general/MOBILE_SOLO_NIVEL_A.md` | Nuevo | Política y lista de rutas permitidas |

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

## Fase 0 — Iconos e instalabilidad en login móvil

Prerequisito para PWA instalable desde `/login/` (start_url del manifest) y para desbloqueo WebAuthn en standalone.

### Comando `generate_pwa_icons`

Genera PNG en `theme/static/img/pwa/` a partir del logo del producto:

1. Logo más reciente `Logo_Signo_administraNET*` en `MEDIA/empresas/logos`
2. Fallback `theme/static/img/brand/logo_signo_administranet.png`
3. Opcional: `--source /ruta/logo.png`

```bash
docker exec Synap_app python manage.py generate_pwa_icons
```

Tamaños: 72, 96, 128, 144, 152, 180, 192, 384, 512 px. Los iconos 192 y 512 incluyen padding maskable (80 % área segura).

Tras generar o cambiar iconos:

```bash
docker exec Synap_app python manage.py collectstatic --noinput
```

### Partials PWA en login

`login/templates/login/mobile/login_administranet.html` incluye (solo móvil):

- `login/includes/pwa_head.html` — `<link rel="manifest">`, meta theme-color, apple-touch-icon (`icon-180.png`)
- `login/includes/pwa_sw_register.html` — `navigator.serviceWorker.register('/sw.js')`

Paridad con el bloque PWA de `base_app.html`; el login no extiende ese layout pero debe ser instalable al abrir `/login/`.

---

## Iconos PWA (referencia)

Generar iconos con el comando de gestión (recomendado) o manualmente desde un PNG fuente ≥512×512:

```bash
docker exec Synap_app python manage.py generate_pwa_icons
```

Salida en `theme/static/img/pwa/`:
icon-72.png   icon-96.png   icon-128.png  icon-144.png
icon-152.png  icon-180.png  icon-192.png  icon-384.png  icon-512.png
```

Alternativa manual con **pwa-asset-generator (npm):**
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

## Manuales de usuario (FAB volver a la app)

Los HTML de manual (`scripts/generar_manuales_html.py` → `*/static/*/manuales/manual_usuario_*.html`) incluyen un botón flotante **«Volver a la app»**:

- **Visible solo en PWA** (`display-mode` standalone / iOS `navigator.standalone` / `SynapPwa.isPwaStandalone()`).
- En navegador normal permanece oculto.
- Al pulsar: `history.back()` si hay historial; si no navega, fallback al hub del módulo (`/mpr/`, `/stock/inventario/`, `/ecom/mayoristapp/pedidos/`, `/contabilidad/auditoria/`).

Regenerar tras cambiar el generador:

```bash
python3 scripts/generar_manuales_html.py
```

---

## Tests

```bash
docker exec Synap_app python manage.py test core.tests.test_pwa login.tests.test_webauthn --verbosity=2
```

Tests PWA organizados en grupos (URLs, SW, manifest, offline, templates, feature flag, estáticos, integración, HTTPS, **login móvil**).

---

## Limitaciones iOS Safari

- El caché del SW en iOS es más agresivo; puede requerir cerrar y reabrir la app para actualizar.
- Las notificaciones push no son soportadas en iOS < 16.4 (fuera del alcance).
- El splash screen en iOS requiere `apple-touch-startup-image` con media queries por tamaño de dispositivo (implementación futura).
- El almacenamiento del SW en iOS tiene límites más bajos que Android.

---

## Referencia

- Especificación completa: `docs/general/ESPEC_PWA_SYNAP.md`
- Desbloqueo WebAuthn: `docs/login/WEBAUTHN_UNLOCK.md`
- Tests: `core/tests/test_pwa.py`, `login/tests/test_webauthn.py`
- Middleware de dispositivos: `core/middleware/base_middleware.py` (clase `DeviceDetectionMiddleware`)
