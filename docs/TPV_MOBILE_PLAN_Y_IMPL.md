# TPV Mobile — Plan e Implementación

> **Fecha:** 2 de marzo 2026  
> **Módulo:** `self_checkout` (TPV / Autoservicio)  
> **Objetivo:** Rediseñar el módulo TPV para mobile manteniendo 100 % de funcionalidad desktop.

---

## 1. Relevamiento de templates desktop existentes

| Template desktop | Vista | Descripción |
|---|---|---|
| `selector_kiosco.html` | `index_view` | Selección de kiosco con JS vanilla (fetch API) |
| `kiosco.html` | `kiosco_view` | Pantalla principal TPV (~2617 líneas, Alpine.js `kioscoApp()`) |
| `config_list.html` | `config_list` | Lista de kioscos configurados (tabla) |
| `config_form.html` | `config_create` / `config_edit` | Formulario crear/editar kiosco (columna única) |
| `carritos_pendientes.html` | `carritos_pendientes_view` | Lista de carritos con estados (tabla) |
| `talonarios_list.html` | `talonarios_list` | Talonarios por PV (tabla) |
| `talonarios_edit.html` | `talonarios_edit` | Edición de talonario (formulario columna única) |
| `talonarios_create.html` | `talonarios_create` | Creación de talonario (formulario columna única) |
| `punto_venta_create.html` | `punto_venta_create` | Creación de punto de venta (formulario columna única) |
| `ticket_print.html` | `ticket_print_view` | Impresión de ticket térmico (layout fijo papel) |

### Funcionalidades mapeadas (paridad 100 %)

- Selección y bloqueo de kiosco (acquire / release / heartbeat).
- Escaneo de artículos por código de barras y búsqueda predictiva.
- Carrito completo: agregar, quitar, modificar cantidad, descuentos.
- Selección de cliente / consumidor final / CUIT.
- Selección de tipo de comprobante (FA / FB / FC) y emisión AFIP (CAE / CAEA).
- Pago con Mercado Pago (QR dinámico + dispositivo físico).
- Impresión de ticket con QR AFIP.
- Modo CAEA offline (autorización supervisor).
- Gestión de talonarios, puntos de venta y configuración de kioscos.
- Administración de carritos pendientes / error.

---

## 2. Propuesta UI/UX mobile

### 2.1 Bloqueo Stitch

Se intentó usar Stitch MCP (`https://stitch.withgoogle.com/`) para generar mockups interactivos. **La herramienta fue bloqueada** por el entorno (WebFetch rechazado). Se documentan los prompts que se habrían utilizado:

| Pantalla | Prompt Stitch propuesto |
|---|---|
| Selector kiosco | "Mobile card list for selecting a kiosk terminal, with status badges (available/in-use/my-session), large touch targets (min 44px), single column, sticky error toast at bottom." |
| TPV principal | "Mobile POS screen: search bar on top, scrollable product results, collapsible bottom sheet for cart with total and pay button, fullscreen modals for client selection and payment." |
| Config / Listas | "Mobile admin list with cards instead of tables, touch-friendly edit buttons, sticky header with back navigation." |

### 2.2 Decisiones de diseño

1. **Single-column layout** en mobile para todas las pantallas.
2. **Tablas → Cards**: las listas tabulares (`config_list`, `carritos_pendientes`, `talonarios_list`) se convierten a tarjetas apiladas verticalmente.
3. **Touch targets ≥ 44px**: botones, links e inputs con `min-height: 2.75rem` (44px).
4. **Inputs font-size ≥ 16px**: evita zoom automático en iOS.
5. **Modales fullscreen**: en mobile, los modales ocupan 100% viewport para maximizar área útil.
6. **Carrito como bottom sheet**: en `kiosco.html`, la columna derecha (carrito) se transforma en un bottom sheet con `max-height: 45vh` y scroll interno.
7. **Botón pantalla completa oculto**: no aplica en mobile.

---

## 3. Arquitectura de detección de dispositivo y selección de templates

### 3.1 DeviceDetectionMiddleware (preexistente)

Ubicación: `core/middleware/base_middleware.py` → clase `DeviceDetectionMiddleware`.

Inyecta en cada request:
- `request.is_mobile` (bool)
- `request.is_desktop` (bool)
- `request.device_type` (string: `android`, `iphone`, `ipad`, `windows_phone`, `desktop`, `mobile`)

Detecta via regex sobre `HTTP_USER_AGENT` (Android, iPhone, iPad, Mobile, etc.).

### 3.2 Selector de templates (`get_template_for_device`)

Ubicación: `core/utils/template_selector.py`.

```python
get_template_for_device(request, 'self_checkout/kiosco.html')
# Mobile → intenta 'self_checkout/mobile/kiosco.html'
# Si no existe → fallback a 'self_checkout/kiosco.html'
# Desktop → siempre devuelve el template original
```

Convención de rutas:
- Desktop: `<app>/templates/<app>/<nombre>.html`
- Mobile: `<app>/templates/<app>/mobile/<nombre>.html`

### 3.3 Integración en vistas

5 vistas modificadas en `self_checkout/views.py` para usar `get_template_for_device()`:

| Vista | Template desktop | Template mobile |
|---|---|---|
| `index_view` | `selector_kiosco.html` | `mobile/selector_kiosco.html` |
| `kiosco_view` | `kiosco.html` | `mobile/kiosco.html` |
| `config_list` | `config_list.html` | `mobile/config_list.html` |
| `talonarios_list` | `talonarios_list.html` | `mobile/talonarios_list.html` |
| `carritos_pendientes_view` | `carritos_pendientes.html` | `mobile/carritos_pendientes.html` |

Vistas SIN versión mobile (formularios columna única, ya responsivos):
- `config_create`, `config_edit` → `config_form.html`
- `talonarios_edit` → `talonarios_edit.html`
- `talonarios_create` → `talonarios_create.html`
- `punto_venta_create` → `punto_venta_create.html`
- `ticket_print_view` → `ticket_print.html` (layout fijo para papel térmico)

---

## 4. Templates mobile implementados

### 4.1 `mobile/kiosco.html` — Herencia multi-nivel

**Estrategia clave**: Este template usa **herencia multi-nivel de Django** en lugar de duplicar las 2617 líneas del desktop. Extiende `self_checkout/kiosco.html` y solo sobreescribe `{% block extra_css %}` con `{{ block.super }}` + overrides CSS mobile.

```
mobile/kiosco.html  →  extends  →  kiosco.html  →  extends  →  base_app.html
```

**Ventajas:**
- 0 duplicación de HTML/JS/Alpine.js.
- El mismo `kioscoApp()` con todos sus modales, validaciones y flujos.
- Cambios en la lógica desktop se reflejan automáticamente en mobile.
- Template mobile de ~80 líneas (solo CSS) vs 2617 líneas desktop.

**Overrides CSS principales:**
- Fuerza columna única (`.kiosk-main-two-cols { flex-direction: column }`)
- Carrito como bottom sheet (`max-height: 45vh`)
- Touch targets 44px mínimo
- Inputs 16px para evitar zoom iOS
- Modales fullscreen
- Oculta botón pantalla completa
- Scroll horizontal para barras de botones

**Viewport y usabilidad en celular (marzo 2026):** En dispositivos móviles la pantalla podía verse como "responsive desktop" (todo escalado y pequeño) porque `base_app.html` no incluye meta viewport. Se añadió en `theme/templates/base_app.html` el bloque `{% block extra_meta %}` y en `mobile/kiosco.html` se sobreescribe con `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">`. Además se reforzaron los overrides mobile: `body.kiosk-client-mode` con `min-height: 100dvh` y `font-size: 16px`, header más compacto con botones táctiles ≥ 44px, CTA "Pagar ahora" con `min-height: 3.5rem` y `font-size: 1.25rem`, e inputs de búsqueda/escaneo con `min-height: 3rem` y padding generoso. Con esto el TPV en celular se usa con tamaño de pantalla real y botones manejables.

**Estabilidad mobile vs desktop (marzo 2026):** Para evitar que el layout "cambie" a desktop escalado tras cargar, se introdujo la clase `tpv-mobile` en el body cuando se sirve el template mobile. Además, todos los templates mobile del módulo (selector_kiosco, config_list, carritos_pendientes, talonarios_list) incluyen `{% block extra_meta %}` con el mismo viewport.

**Diseño 100% app mobile (marzo 2026):** Se reemplazó el layout mobile por un diseño nativo tipo app, manteniendo toda la funcionalidad (mismo Alpine.js `kioscoApp()` y mismos modales). Cambios realizados:
- **Refactor de `kiosco.html`:** Se añadieron `{% block kiosk_header %}` y `{% block kiosk_main %}` para que el template mobile pueda sustituir solo header y área principal.
- **Header mobile** (`includes/_header_kiosk_mobile.html`): Logo + título compactos, terminal activa y badge homologación; fila de chips táctiles (Cliente, Lista de precios, Vendedor, Descuento, Cta. cte.) en lugar de la barra horizontal que truncaba en desktop escalado.
- **Main mobile** (`includes/_kiosk_main_mobile.html`): Una columna con búsqueda/escaneo arriba (mismo include `_search_scan`), barra fija inferior con resumen (X productos, total) y botón "Pagar", y sheet deslizable para ver el carrito completo (lista, totales, teclado de pago, Tarjeta regalo/Asistencia/Cancelar). Variable Alpine `cartSheetOpen` y método `toggleCartSheet()` para abrir/cerrar el sheet.
- **Estilos:** Viewport, safe-area, touch targets ≥ 44px, inputs ≥ 16px, modales a pantalla completa; banner de ofertas del include compactado en mobile.

### 4.2 Templates simples (tablas → cards)

Cada uno es un template independiente que extiende `base_app.html` y reimplementa el contenido como cards en lugar de tablas:

| Template | Cambio principal |
|---|---|
| `mobile/selector_kiosco.html` | Cards con badges de estado, botones Abrir/Cerrar sesión touch-friendly |
| `mobile/config_list.html` | Cards con datos del kiosco, botones de acción verticales |
| `mobile/carritos_pendientes.html` | Cards con filtros, búsqueda, acciones por carrito |
| `mobile/talonarios_list.html` | Cards con datos del talonario, selector PV con submit automático |

---

## 5. Archivos tocados

### Nuevos

| Archivo | Descripción |
|---|---|
| `core/utils/template_selector.py` | Utilidad `get_template_for_device()` |
| `self_checkout/templates/self_checkout/mobile/kiosco.html` | Template mobile TPV (herencia multi-nivel) |
| `self_checkout/templates/self_checkout/mobile/selector_kiosco.html` | Template mobile selector |
| `self_checkout/templates/self_checkout/mobile/config_list.html` | Template mobile config lista |
| `self_checkout/templates/self_checkout/mobile/carritos_pendientes.html` | Template mobile carritos |
| `self_checkout/templates/self_checkout/mobile/talonarios_list.html` | Template mobile talonarios |
| `self_checkout/tests/test_mobile_templates.py` | Tests de regresión |

### Modificados

| Archivo | Cambio |
|---|---|
| `self_checkout/views.py` | Import `get_template_for_device`, 5 vistas usan selector |

### Login y Ajustes (perfil) mobile

Cuando el dispositivo es móvil (`request.is_mobile`), se sirven templates específicos basados en Stitch:

| Vista (app login) | Template desktop | Template mobile |
|---|---|---|
| `login_view` | `login/login_administranet.html` | `login/mobile/login_administranet.html` |
| `perfil_view` | `login/perfil.html` | `login/mobile/perfil.html` |

- **Login mobile:** Diseño Stitch `administranet_login_es` (logo, bienvenida, empresa/usuario/contraseña, mismo POST JSON que desktop).
- **Ajustes mobile:** Diseño Stitch `administranet_ajustes_es` (header con volver, perfil rápido, secciones Perfil de Negocio, POS, Seguridad, Cerrar sesión, barra inferior Ventas/Productos/Informes/Ajustes).

Archivos: `login/views.py` (usa `get_template_for_device`), `login/templates/login/mobile/login_administranet.html`, `login/templates/login/mobile/perfil.html`.

### No modificados (intactos)

- `self_checkout/urls.py` — Sin cambios en rutas.
- `self_checkout/permissions.py` — Sin cambios en permisos.
- `self_checkout/middleware.py` — Sin cambios.
- `core/middleware/base_middleware.py` — `DeviceDetectionMiddleware` ya existía.
- Todos los templates desktop — Sin modificaciones.

---

## 6. Tests de regresión

Archivo: `self_checkout/tests/test_mobile_templates.py`

### Test classes

| Clase | Tests | Qué valida |
|---|---|---|
| `DeviceDetectionMiddlewareTest` | 5 | Chrome desktop, iPhone, Android, iPad, UA vacío → `is_mobile`/`device_type` correctos |
| `TemplateSelectorTest` | 5 | Desktop siempre original, mobile con template existente, fallback a desktop, template sin subdirectorio, request sin atributo |
| `MobileTemplatesExistTest` | 1 | Los 5 templates mobile se cargan sin `TemplateDoesNotExist` |
| `KioscoMobileInheritanceTest` | 1 | `mobile/kiosco.html` extiende `self_checkout/kiosco.html` (herencia multi-nivel) |

### Comando de ejecución

```bash
docker exec Synap_app python manage.py test self_checkout.tests.test_mobile_templates --verbosity=2
```

### Checklist QA manual

- [ ] **Desktop Chrome**: Navegar selector → abrir kiosco → operar TPV completo (escanear, pagar, emitir). Verificar layout 2 columnas.
- [ ] **Desktop Firefox**: Misma secuencia que Chrome.
- [ ] **Mobile iPhone Safari**: Selector muestra cards. Kiosco en columna única. Carrito como bottom sheet. Modales fullscreen. Inputs sin zoom.
- [ ] **Mobile Android Chrome**: Misma secuencia que iPhone.
- [ ] **Tablet iPad**: Selector y listas como cards. Kiosco hereda CSS mobile.
- [ ] **Config list (mobile)**: Cards con datos, botón editar funcional.
- [ ] **Carritos pendientes (mobile)**: Filtro por estado, búsqueda, reintentar/eliminar.
- [ ] **Talonarios (mobile)**: Selector PV funciona, cards con modificar.
- [ ] **Formularios (config_form, talonarios_edit/create, punto_venta_create)**: Funcionan en mobile sin template dedicado (ya son columna única).
- [ ] **Ticket impresión**: Sin cambios, layout papel térmico correcto.
- [ ] **Permisos**: Un usuario sin `self_checkout.admin` NO ve config/talonarios. Un usuario sin `self_checkout.supervisor` NO ve carritos.

---

## 7. Riesgos

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| CSS mobile de `kiosco.html` no cubre algún modal específico | Media | Los selectores `.fixed.inset-0 > div` capturan todos los modales. Revisar en QA manual. |
| Herencia multi-nivel rompe si `kiosco.html` deja de definir `{% block extra_css %}` | Baja | Test `KioscoMobileInheritanceTest` detectaría la ruptura. |
| iPad detectado como mobile (puede preferir layout desktop) | Media | `DeviceDetectionMiddleware` incluye iPad en patrones mobile. Si se quiere tratar como desktop, eliminar `iPad` de la lista. |
| `get_template_for_device` busca template en disco en cada request | Baja | Django cachea templates internamente. Si hay impacto, cachear resultado en `request`. |

---

## 8. Pendientes

1. **Ejecutar tests**: No se pudieron ejecutar en esta sesión por restricciones del entorno. Ejecutar en Docker.
2. **Tema oscuro mobile**: Los overrides CSS heredan dark mode del desktop. Verificar contraste en QA.
3. **iPad como desktop (opcional)**: Si los usuarios de iPad prefieren layout 2 columnas, excluir `iPad` del middleware.
4. **PWA / Service Worker**: Fuera de alcance actual. Si se requiere offline, considerar.
5. **Teclado virtual mobile**: `use_virtual_keyboard` ya se soporta por query param. Evaluar si activar por defecto en mobile.
6. **Eliminar `_kiosco_script.html`**: Partial huérfano que no se usa. Se puede borrar de forma segura.

---

## 9. Pasos de despliegue

1. Merge de la rama con estos cambios a `Desarrollo`.
2. Ejecutar tests: `docker exec Synap_app python manage.py test self_checkout.tests.test_mobile_templates -v2`
3. QA manual con dispositivos reales (iPhone, Android, iPad, desktop).
4. Deploy a staging.
5. Validar que las rutas existentes siguen funcionando idénticamente en desktop (sin regresión).
6. Deploy a producción.
