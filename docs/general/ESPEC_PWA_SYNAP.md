# Especificación: PWA (Progressive Web App) — Synap

**Estado: PENDIENTE**  
**Prioridad: Media**  
**Módulos afectados:** core, theme (templates/static), django_project (urls/settings)

---

## 1. Resumen

Implementar PWA a nivel intermedio en Synap para permitir:
- Instalación como app nativa en Android e iOS.
- Caché inteligente de assets estáticos (cache-first) para carga rápida.
- Fallback offline con página dedicada cuando no hay red (network-first para HTML).
- Experiencia standalone (sin barra del navegador) en dispositivos móviles.

**Feature flagging por dispositivo:** La PWA se activa **solo en dispositivos móviles**. Los meta tags PWA, el `<link rel="manifest">` y el registro del Service Worker se inyectan condicionalmente en `base_app.html` usando `{% if request.is_mobile %}`, aprovechando el middleware `DeviceDetectionMiddleware` existente (`core.middleware.DeviceDetectionMiddleware`). En desktop, el navegador no ve manifest ni registra SW.

**No incluye:** notificaciones push, sincronización en background, IndexedDB para datos offline.

---

## 2. Requisitos del navegador y del estándar

| Requisito | Detalle |
|-----------|---------|
| HTTPS obligatorio | Ya configurado: `SECURE_SSL_REDIRECT = not DEBUG` en `django_project/settings.py` |
| `sw.js` en raíz del dominio | Debe servirse desde `/sw.js`, no desde `/static/sw.js` |
| `manifest.json` en raíz | Debe servirse desde `/manifest.json`, no desde `/static/manifest.json` |
| Scope del SW | `scope: '/'` — controla toda la aplicación |

---

## 3. Componentes y archivos

### 3.1. Web App Manifest (`manifest.json`)

**Ubicación fuente:** `theme/static/manifest.json`  
**URL pública:** `/manifest.json` (servida por vista Django, no por WhiteNoise)

**Campos obligatorios:**

| Campo | Valor |
|-------|-------|
| `name` | `"Synap - Gestión Empresarial"` |
| `short_name` | `"Synap"` |
| `description` | `"Sistema de gestión empresarial integrado"` |
| `start_url` | `"/core/dashboard/"` |
| `scope` | `"/"` |
| `display` | `"standalone"` |
| `orientation` | `"any"` |
| `theme_color` | `"#7c3aed"` (violeta Synap) |
| `background_color` | `"#f3f4f6"` (gray-100) |
| `lang` | `"es"` |
| `dir` | `"ltr"` |
| `categories` | `["business", "productivity"]` |
| `icons` | Array con todos los tamaños (ver §7) |

**Criterios de aceptación (CA):**

- CA-MAN-01: El archivo contiene todos los campos de la tabla anterior.
- CA-MAN-02: La respuesta HTTP tiene `Content-Type: application/manifest+json`.
- CA-MAN-03: El JSON es válido y parseable.
- CA-MAN-04: `start_url` apunta a una URL existente que retorna 200 (autenticada) o 302 (redirect a login).
- CA-MAN-05: `icons` contiene al menos entradas para 192x192 y 512x512.

---

### 3.2. Service Worker (`sw.js`)

**Ubicación fuente:** `theme/static/sw.js`  
**URL pública:** `/sw.js` (servida por vista Django)

**Estructura:**

```
const CACHE_VERSION = 'v1';
const STATIC_CACHE = `synap-static-${CACHE_VERSION}`;
const PAGES_CACHE = `synap-pages-${CACHE_VERSION}`;
```

**Estrategia Cache-First (assets estáticos):**

| Patrón de URL | Comportamiento |
|---------------|----------------|
| `/static/css/` | Cache primero, red como fallback |
| `/static/js/` | Cache primero, red como fallback |
| `/static/fonts/` | Cache primero, red como fallback |
| `/static/img/` | Cache primero, red como fallback |
| CDN Tailwind (`cdn.tailwindcss.com`) | Cache primero, red como fallback |
| CDN Alpine (`unpkg.com/alpinejs`, `cdn.jsdelivr.net/npm/alpinejs`) | Cache primero, red como fallback |
| Google Fonts (`fonts.googleapis.com`, `fonts.gstatic.com`) | Cache primero, red como fallback |

**Estrategia Network-First (navegación HTML):**

| Condición | Comportamiento |
|-----------|----------------|
| `request.mode === 'navigate'` | Red primero; si falla, buscar en caché; si no hay caché, servir `/offline/` |
| URL contiene `/admin/` | No interceptar, pasar directo a red |
| URL contiene `/api/` | No interceptar, pasar directo a red |
| URL contiene `/logout/` | No interceptar, pasar directo a red |
| Método !== GET | No interceptar, pasar directo a red |

**Eventos del ciclo de vida:**

| Evento | Acción |
|--------|--------|
| `install` | Precachear `/offline/` y `skipWaiting()` |
| `activate` | Borrar cachés cuyo nombre no coincida con `CACHE_VERSION` actual; `clients.claim()` |
| `fetch` | Aplicar estrategia según tipo de request |

**Criterios de aceptación:**

- CA-SW-01: La respuesta tiene `Content-Type: application/javascript`.
- CA-SW-02: La cabecera `Cache-Control` es `no-cache` o `max-age=0` (el navegador siempre verifica nueva versión).
- CA-SW-03: El contenido incluye la constante `CACHE_VERSION`.
- CA-SW-04: El contenido contiene event listeners para `install`, `activate` y `fetch`.
- CA-SW-05: El contenido implementa lógica de exclusión para `/admin/`, `/api/`, `/logout/`.
- CA-SW-06: No intercepta requests POST.
- CA-SW-07: En `activate`, elimina cachés con versión antigua.

---

### 3.3. Página Offline (`offline.html`)

**Ubicación fuente:** `theme/templates/offline.html`  
**URL pública:** `/offline/`

**Contenido:**
- Documento HTML5 autocontenido.
- Estilos vía Tailwind CDN (no depende de archivos locales).
- Mensaje: "Sin conexión — Revisa tu conexión a internet e intenta de nuevo".
- Botón "Reintentar" que ejecuta `window.location.reload()`.
- Branding Synap (nombre y gradiente violeta/azul).
- Soporte dark mode vía `prefers-color-scheme`.

**Criterios de aceptación:**

- CA-OFF-01: La URL `/offline/` retorna HTTP 200.
- CA-OFF-02: La respuesta tiene `Content-Type: text/html`.
- CA-OFF-03: El HTML contiene el texto "Sin conexión" o "sin conexión".
- CA-OFF-04: El HTML contiene un botón o enlace con `reload()`.
- CA-OFF-05: No depende de archivos en `/static/` (usa CDN o estilos inline).

---

### 3.4. Vistas Django (`core/views/pwa_views.py`)

**Dos vistas, sin autenticación requerida (públicas):**

| Vista | URL | Content-Type | Cache-Control |
|-------|-----|-------------|---------------|
| `serve_sw` | `/sw.js` | `application/javascript` | `no-cache` |
| `serve_manifest` | `/manifest.json` | `application/manifest+json` | `public, max-age=86400` |

**Lógica de resolución de archivos:**

1. Intentar leer desde `settings.STATIC_ROOT / <archivo>` (producción post-collectstatic).
2. Si no existe, fallback a `settings.STATICFILES_DIRS[0] / <archivo>` (desarrollo).
3. Si ninguno existe, retornar HTTP 404.

**Criterios de aceptación:**

- CA-VIEW-01: `/sw.js` retorna 200 cuando el archivo existe.
- CA-VIEW-02: `/manifest.json` retorna 200 cuando el archivo existe.
- CA-VIEW-03: Content-Type correcto en cada vista.
- CA-VIEW-04: `Cache-Control: no-cache` en la respuesta de `/sw.js`.
- CA-VIEW-05: Ambas vistas son accesibles sin autenticación.
- CA-VIEW-06: Retornan 404 si el archivo fuente no existe.

---

### 3.5. URLs (`django_project/urls.py`)

**Nuevas rutas en `urlpatterns` base (antes de la sección de static/media):**

```python
path('sw.js', serve_sw, name='pwa_sw'),
path('manifest.json', serve_manifest, name='pwa_manifest'),
path('offline/', TemplateView.as_view(template_name='offline.html'), name='pwa_offline'),
```

**Criterios de aceptación:**

- CA-URL-01: La URL name `pwa_sw` resuelve a `/sw.js`.
- CA-URL-02: La URL name `pwa_manifest` resuelve a `/manifest.json`.
- CA-URL-03: La URL name `pwa_offline` resuelve a `/offline/`.
- CA-URL-04: Las tres URLs son resolvibles por `reverse()`.

---

### 3.6. Feature Flag PWA por dispositivo en `base_app.html`

**Estrategia:** En lugar de crear un template separado `base_mobile.html`, se inyecta el bloque PWA directamente en `base_app.html` con condicional de dispositivo. Toda la app hereda PWA automáticamente, pero solo se activa en móviles.

**Middleware existente:** `core.middleware.DeviceDetectionMiddleware` (en `core/middleware/base_middleware.py`, líneas 458-506).  
**Variables disponibles en request:** `request.is_mobile` (bool), `request.is_desktop` (bool), `request.device_type` (str: `android`, `iphone`, `ipad`, `windows_phone`, `desktop`, `mobile`).

**Implementación en `base_app.html` — bloque `extra_meta`:**

```html
{% if request.is_mobile %}
<!-- PWA: solo en dispositivos móviles -->
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#7c3aed">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Synap">
<link rel="apple-touch-icon" href="{% static 'img/pwa/icon-180.png' %}">
<meta name="msapplication-TileColor" content="#7c3aed">
{% endif %}
```

**Registro del SW (antes de `</body>` en `base_app.html`):**

```html
{% if request.is_mobile %}
<script>
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js', { scope: '/' })
        .then(function(reg) { console.log('SW registrado:', reg.scope); })
        .catch(function(err) { console.warn('SW error:', err); });
}
</script>
{% endif %}
```

**Meta tags PWA inyectados (solo móvil):**

| Meta tag | Valor |
|----------|-------|
| `<link rel="manifest" href="/manifest.json">` | Obligatorio |
| `<meta name="theme-color" content="#7c3aed">` | Color de la barra del navegador |
| `<meta name="mobile-web-app-capable" content="yes">` | Chrome/Android |
| `<meta name="apple-mobile-web-app-capable" content="yes">` | iOS Safari |
| `<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">` | Estilo barra iOS |
| `<meta name="apple-mobile-web-app-title" content="Synap">` | Título en iOS |
| `<link rel="apple-touch-icon" href="...icon-180.png">` | Icono iOS principal |
| `<meta name="msapplication-TileColor" content="#7c3aed">` | Windows tiles |

**Criterios de aceptación:**

- CA-TPL-01: `base_app.html` contiene el bloque PWA envuelto en `{% if request.is_mobile %}`.
- CA-TPL-02: Contiene `<link rel="manifest"` apuntando a `/manifest.json`.
- CA-TPL-03: Contiene `apple-mobile-web-app-capable`.
- CA-TPL-04: Contiene el script de registro con `serviceWorker.register('/sw.js')`.
- CA-TPL-05: Contiene `theme-color`.
- CA-TPL-06: En request desktop (`is_mobile=False`), el HTML renderizado **no** contiene `rel="manifest"` ni registro del SW.
- CA-TPL-07: En request mobile (`is_mobile=True`), el HTML renderizado **sí** contiene `rel="manifest"` y registro del SW.

---

## 4. Feature flag: comportamiento por dispositivo

| Dispositivo | `request.is_mobile` | Meta tags PWA | Registro SW | Manifest link | Instalable |
|-------------|---------------------|---------------|-------------|---------------|------------|
| Android | `True` | Si | Si | Si | Si |
| iPhone | `True` | Si | Si | Si | Si |
| iPad | `True` | Si | Si | Si | Si |
| Desktop | `False` | No | No | No | No |

**Nota:** Las vistas `/sw.js`, `/manifest.json` y `/offline/` siguen accesibles desde cualquier dispositivo (son URLs públicas). La restricción es solo en la inyección de los meta tags y el script de registro en el HTML. Esto asegura que el navegador de desktop nunca intente registrar el SW ni interpretar el manifest.

**Módulos cubiertos (toda la app vía herencia de `base_app.html`):**

| Módulo | Template | Hereda PWA condicional |
|--------|----------|----------------------|
| Login | `login/login_app_base.html` → `base_app.html` | Si (móvil) |
| Perfil | `core/perfil.html` → `core/core_app_base.html` → `base_app.html` | Si (móvil) |
| Dashboard | `dashboard/dashboard.html` → ... → `base_app.html` | Si (móvil) |
| Stock | `stock/alta_movimiento.html` → `base_app.html` | Si (móvil) |
| MPR | `mpr/base_mpr.html` → `base_app.html` | Si (móvil) |
| Configuraciones | `core/system_config/*.html` → `core/core_app_base.html` → `base_app.html` | Si (móvil) |

---

## 5. Iconos PWA

### 5.1. Tamaños requeridos

| Tamaño | Uso | Archivo esperado |
|--------|-----|-----------------|
| 72x72 | Android legacy | `theme/static/img/pwa/icon-72.png` |
| 96x96 | Android legacy | `theme/static/img/pwa/icon-96.png` |
| 128x128 | Chrome Web Store | `theme/static/img/pwa/icon-128.png` |
| 144x144 | Windows tile, Android | `theme/static/img/pwa/icon-144.png` |
| 152x152 | iPad (iOS) | `theme/static/img/pwa/icon-152.png` |
| 180x180 | iPhone (apple-touch-icon) | `theme/static/img/pwa/icon-180.png` |
| 192x192 | Android (obligatorio manifest) | `theme/static/img/pwa/icon-192.png` |
| 384x384 | Android splash | `theme/static/img/pwa/icon-384.png` |
| 512x512 | Android splash (obligatorio manifest) | `theme/static/img/pwa/icon-512.png` |

### 5.2. Herramienta recomendada

- **pwa-asset-generator:** `npx pwa-asset-generator logo-512.png theme/static/img/pwa/ --icon-only --type png`
- **RealFaviconGenerator:** https://realfavicongenerator.net/ (interfaz web).
- **Fuente:** PNG de al menos 512x512 con fondo transparente o con background_color.

---

## 6. Consideraciones iOS Safari

| Aspecto | Comportamiento iOS | Mitigación |
|---------|-------------------|------------|
| Caché del SW | Más agresivo; puede no actualizar automáticamente | Documentar que se debe cerrar y reabrir la app para forzar update |
| Push notifications | No soportadas en iOS < 16.4 | No aplica (fuera del alcance de esta spec) |
| Splash screen | Requiere `apple-touch-startup-image` por tamaño de dispositivo | Incluir meta tags con media queries (fase posterior) |
| Almacenamiento SW | Límite más bajo que Android | Los assets cacheados no deberían exceder los límites |
| `display: standalone` | Funciona con `apple-mobile-web-app-capable` | Ya incluido en meta tags |

---

## 7. Seguridad — CSRF, formularios, fetch

| Preocupación | Solución |
|-------------|----------|
| `{% csrf_token %}` en forms | El SW no intercepta POST; formularios funcionan sin cambio |
| fetch/AJAX existente (ej. `cambiar_empresa_branch`) | Son requests a red normal; el SW solo cachea GET de navegación |
| URLs de `/api/` | Excluidas explícitamente de la interceptación del SW |
| `/logout/` | Excluido del caché; siempre va a red |
| Cookies de sesión | El SW no modifica cookies; `fetch` del SW pasa credenciales con `credentials: 'same-origin'` |

---

## 8. Versionado y despliegue

### 8.1. Cambiar versión del caché

1. Editar `theme/static/sw.js`, cambiar `CACHE_VERSION = 'v1'` a `'v2'` (o incrementar).
2. Ejecutar `collectstatic` en el contenedor: `docker exec Synap_app python manage.py collectstatic --noinput`.
3. El navegador detecta el cambio en el archivo al hacer byte-comparison; activa el nuevo SW en el evento `activate` que borra cachés antiguas.

### 8.2. Headers del servidor

| URL | Cache-Control esperado |
|-----|----------------------|
| `/sw.js` | `no-cache` (vista Django lo envía; si hay nginx/proxy, no sobrescribir) |
| `/manifest.json` | `public, max-age=86400` |
| `/offline/` | Sin restricción especial |

### 8.3. Verificación post-deploy

```bash
curl -I https://synap.administranet.com.ar/sw.js
# Esperar: 200, Content-Type: application/javascript, Cache-Control: no-cache

curl -I https://synap.administranet.com.ar/manifest.json
# Esperar: 200, Content-Type: application/manifest+json

curl -I https://synap.administranet.com.ar/offline/
# Esperar: 200, Content-Type: text/html
```

---

## 9. Checklist de testing

### 9.1. Chrome DevTools > Application

- [ ] Manifest: todos los campos presentes, sin warnings.
- [ ] Service Worker: estado "activated and is running".
- [ ] Cache Storage: `synap-static-v1` y `synap-pages-v1` creados con entradas.
- [ ] Checkbox "Offline" en Network: la app muestra la página offline.
- [ ] "Update on reload" funciona para forzar nuevo SW.

### 9.2. Dispositivo Android

- [ ] Banner "Agregar a pantalla de inicio" aparece.
- [ ] App se abre en modo standalone (sin barra de navegación).
- [ ] Splash screen con `theme_color` y `background_color`.
- [ ] Funciona offline mostrando la página de fallback.

### 9.3. Dispositivo iOS (Safari)

- [ ] Compartir > "Agregar a pantalla de inicio" funciona.
- [ ] Icono correcto (apple-touch-icon 180x180).
- [ ] Se abre en standalone si `apple-mobile-web-app-capable` está activo.
- [ ] Barra de estado con estilo `black-translucent`.

### 9.4. Tests Django automatizados

- [ ] `docker exec Synap_app python manage.py test core.tests.test_pwa`
- [ ] Todos los tests pasan (CA-* cubiertos).

---

## 10. Dependencias

- **Python:** Ninguna nueva. Solo Django (`HttpResponse`, `FileResponse`, `TemplateView`).
- **JavaScript:** Ninguna nueva. Service Worker API nativa del navegador.
- **Frontend:** Tailwind y Alpine.js siguen sin cambios.

---

## 11. Archivos a crear/modificar

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `theme/static/manifest.json` | CREAR | Web App Manifest |
| `theme/static/sw.js` | CREAR | Service Worker |
| `theme/templates/offline.html` | CREAR | Página offline |
| `core/views/pwa_views.py` | CREAR | Vistas serve_sw y serve_manifest |
| `core/views/__init__.py` | MODIFICAR | Exportar vistas PWA (o importar directo en urls) |
| `django_project/urls.py` | MODIFICAR | Agregar rutas /sw.js, /manifest.json, /offline/ |
| `theme/templates/base_app.html` | MODIFICAR | Inyectar bloque PWA condicional `{% if request.is_mobile %}` |
| `theme/static/img/pwa/` | CREAR directorio | Iconos (generados manualmente) |
| `core/tests/test_pwa.py` | CREAR | Tests TDD |
| `docs/general/ESPEC_PWA_SYNAP.md` | CREAR | Esta especificación |
| `docs/general/PWA_SYNAP.md` | CREAR | Documentación operativa |

**Nota:** No se crea `base_mobile.html`. El feature flag PWA vive directamente en `base_app.html` con `{% if request.is_mobile %}`.
