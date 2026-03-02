# TPV Mobile — Refactor con Stitch MCP

> **Fecha:** 2 de marzo 2026  
> **Módulo:** `self_checkout` (TPV / Autoservicio)  
> **Rama:** `Desarrollo`  
> **Objetivo:** Refactor del TPV Mobile manteniendo paridad funcional total con desktop, usando Stitch MCP como insumo UX/UI.

---

## 1. Diagnóstico de deuda técnica (auditoría pre-refactor)

### 1.1 Duplicación de JS entre templates mobile

| Patrón duplicado | Archivos afectados | Líneas duplicadas (~) |
|---|---|---|
| `getCookie()` (lectura CSRF) | selector_kiosco, carritos_pendientes | 3 × 2 = 6 |
| `showToast()` / `showError()` | selector_kiosco, carritos_pendientes | 5 × 2 = 10 |
| Lógica fetch + CSRF header | selector_kiosco, carritos_pendientes | 8 × 4 = 32 |
| `setLoading()` (btn disabled + text swap) | carritos_pendientes | 6 |

**Total estimado:** ~54 líneas de JS repetido entre 2 templates, sin contar el desktop que tiene su propia copia.

### 1.2 CSS frágil en mobile/kiosco.html

- **30+ usos de `!important`** para override del desktop, necesarios pero frágiles.
- Selectores genéricos como `.fixed.inset-0 > div` que pueden capturar elementos no deseados si la estructura del desktop cambia.
- Sin `prefers-reduced-motion`: animaciones y transiciones forzadas sin respetar la preferencia del usuario.
- Sin soporte de `safe-area-inset` para dispositivos con notch.

### 1.3 Accesibilidad

| Problema | Severidad | Dónde |
|---|---|---|
| Sin `role="list"` / `role="listitem"` en cards dinámicas | Alta | selector_kiosco, carritos, config, talonarios |
| Sin `aria-label` en botones de acción contextual | Alta | Todos los templates mobile |
| Sin `aria-live` en contadores y mensajes de estado | Media | carritos (filtro), selector (carga) |
| Sin `aria-labelledby` en secciones principales | Media | Todos |
| Sin `<label>` para inputs de búsqueda/filtro | Media | carritos |
| Sin `:focus-visible` personalizado | Media | kiosco mobile |
| Sin `aria-busy` en botones durante carga | Baja | Todos con botones async |

### 1.4 Rendimiento

- Sin skeleton/placeholder durante carga inicial (selector_kiosco) → flash de contenido vacío.
- Toast sin transición de opacidad → aparición/desaparición abrupta.
- Sin `inputmode="search"` en inputs de búsqueda.

### 1.5 Dead code

- `_kiosco_script.html`: partial huérfano, marcado como "safe to delete" en su propio contenido. Nunca incluido por ningún template.

### 1.6 Archivos duplicados (copias con espacios)

Existen múltiples archivos `* 2.py`, `* 2.html` en el módulo (ej. `views 2.py`, `urls 2.py`, `kiosco 2.html`). No forman parte de este refactor pero representan deuda técnica de gestión de archivos.

---

## 2. Stitch MCP — Consulta y bloqueo

### 2.1 Intentos de acceso

| Método | Resultado | Detalle |
|---|---|---|
| `WebFetch` a `https://stitch.withgoogle.com/` | **Rechazado** | "User Rejected" — herramienta bloqueada por el entorno |
| Gemini CLI (`gemini --version`) | **Rechazado** | Shell command rechazado |
| Verificación extensión Stitch en `~/.gemini/extensions/Stitch/` | **Rechazado** | Shell command rechazado |

### 2.2 Contexto (memoria del 2 de marzo 2026)

Según notas previas de la sesión del mismo día:
- Gemini CLI instalado (`gemini 0.31.0`).
- Extensión Stitch instalada en `~/.gemini/extensions/Stitch`.
- Errores intermitentes de auth (401) y timeouts/SIGKILL en modo no interactivo.
- **Estado: no validado para uso automatizado estable.**

### 2.3 Prompts Stitch preparados (no ejecutados)

| Pantalla | Prompt Stitch |
|---|---|
| Selector kiosco | "Mobile card list for kiosk terminal selection: status badges (available/in-use/my-session), loading skeletons, min 44px touch targets, single column, ARIA roles, toast notifications at bottom with fade animation." |
| TPV principal (kiosco) | "Mobile POS screen: search bar top, scrollable product grid (1 col), collapsible bottom-sheet cart with drag handle, sticky total+pay bar, fullscreen modals for client/payment selection, focus-visible rings, prefers-reduced-motion support." |
| Carritos pendientes | "Mobile admin list: filterable card list with search input (inputmode=search), status filter dropdown, action buttons per card (retry/delete/print), toast notifications, ARIA live regions for counter updates." |
| Config / Listas admin | "Mobile admin card list: semantic dl/dt/dd for data, nav landmark for action buttons, focus-within rings on cards, consistent 44px touch targets." |

### 2.4 Decisión

**Stitch bloqueado → se procede con refactor técnico basado en auditoría directa del código y principios WCAG 2.1 AA / Material Design touch guidelines.**

---

## 3. Cambios implementados

### 3.1 Nuevo: `mobile/_utils.html` — Partial de utilidades JS compartidas

**Problema resuelto:** Eliminación de ~54 líneas de JS duplicado entre templates mobile.

**Contenido:**
- `SynapMobile.getCookie(name)` — Lectura de cookie CSRF.
- `SynapMobile.showToast(msg, opts)` — Toast unificado con posición configurable, transición de opacidad, `role="alert"` + `aria-live="assertive"`.
- `SynapMobile.csrfFetch(url, opts)` — Wrapper de fetch con CSRF automático y `credentials: 'same-origin'`.
- `SynapMobile.setLoading(btn, loading)` — Toggle de estado loading en botones con `aria-busy`.
- `SynapMobile.showUrlError()` — Lectura de `?error=` en URL.

**Uso:** `{% include "self_checkout/mobile/_utils.html" %}` antes del `<script>` específico de cada template.

### 3.2 Refactor: `mobile/selector_kiosco.html`

| Mejora | Detalle |
|---|---|
| JS duplicado eliminado | Usa `SynapMobile.csrfFetch`, `showToast`, `setLoading` |
| Skeleton de carga | 2 cards placeholder con `animate-pulse` mientras se cargan los kioscos |
| ARIA | `aria-labelledby` en section, `role="list"` + `role="listitem"`, `role="status"` en estado, `aria-label` en cada botón |
| Focus | `focus-within:ring-2` en cards, `focus:ring-2` en todos los botones/links |
| Loading state en Abrir | Botón muestra "Abriendo…" con `aria-busy` durante acquire |
| Toast unificado | ID `synap-toast`, transición de opacidad |

### 3.3 Refactor: `mobile/carritos_pendientes.html`

| Mejora | Detalle |
|---|---|
| JS duplicado eliminado | Usa `SynapMobile.csrfFetch`, `showToast`, `setLoading` |
| Accesibilidad filtros | `<label class="sr-only">` para search y select, `inputmode="search"`, `aria-live="polite"` en contador |
| ARIA en cards | `role="list"` + `role="listitem"`, `aria-label` en cada botón de acción |
| Focus visible | `focus-within:ring-2` en cards, `focus:ring-2` en botones |
| Loading text mejorado | "Procesando…", "Buscando…", "Emitiendo…" en lugar de "…" genérico |
| Toast position | `position: 'top'` consistente para acciones |
| Conteo reactivo | `updateCount()` se llama al eliminar/confirmar cards |

### 3.4 Refactor: `mobile/config_list.html`

| Mejora | Detalle |
|---|---|
| Semántica | `<nav aria-label="...">` para acciones, `<dl>/<dt>/<dd>` para datos de kiosco |
| ARIA | `aria-labelledby`, `role="list"` + `role="listitem"`, `aria-label` en botón Editar |
| Focus | `focus-within:ring-2` en cards, `focus:ring-2` en links |

### 3.5 Refactor: `mobile/talonarios_list.html`

| Mejora | Detalle |
|---|---|
| Semántica | `<nav aria-label="...">` para acciones, `<dl>/<dt>/<dd>` para datos de talonario |
| ARIA | `aria-labelledby`, `role="list"` + `role="listitem"`, `aria-label` en select y botón Modificar |
| Focus | `focus-within:ring-2` en cards, `focus:ring-2` en links |

### 3.6 Refactor: `mobile/kiosco.html` (CSS overrides)

| Mejora | Detalle |
|---|---|
| `prefers-reduced-motion: reduce` | Desactiva animaciones y transiciones para usuarios con sensibilidad al movimiento |
| `:focus-visible` | Anillo azul de 2px con offset para navegación por teclado |
| Handle del bottom sheet | Pseudoelemento `::before` en `.kiosk-col-right` como barra visual de arrastre |
| Mejora de contrastes | Override de `bg-emerald-100`/`text-emerald-700` y `bg-amber-100`/`text-amber-700` con valores más contrastados |
| Safe area insets | `env(safe-area-inset-bottom)` para dispositivos con notch |
| `-webkit-overflow-scrolling: touch` | Scroll nativo suave en columnas y bottom sheet |
| Transición condicional | `transition` en bottom sheet solo con `prefers-reduced-motion: no-preference` |

---

## 4. Archivos tocados

### Nuevos

| Archivo | Descripción |
|---|---|
| `self_checkout/templates/self_checkout/mobile/_utils.html` | Partial JS compartido para templates mobile |

### Modificados

| Archivo | Cambio |
|---|---|
| `self_checkout/templates/self_checkout/mobile/selector_kiosco.html` | Refactor: usa _utils, skeleton, ARIA, focus |
| `self_checkout/templates/self_checkout/mobile/kiosco.html` | Refactor CSS: reduced-motion, focus-visible, handle, contrastes, safe-area |
| `self_checkout/templates/self_checkout/mobile/carritos_pendientes.html` | Refactor: usa _utils, labels, ARIA, loading mejorado |
| `self_checkout/templates/self_checkout/mobile/config_list.html` | Refactor: semántica dl/dt/dd, nav, ARIA, focus |
| `self_checkout/templates/self_checkout/mobile/talonarios_list.html` | Refactor: semántica dl/dt/dd, nav, ARIA, focus |
| `self_checkout/tests/test_mobile_templates.py` | Ampliado: tests de accesibilidad, _utils, inclusión |

### No modificados (intactos)

- **Todos los templates desktop** — Sin cambios.
- **`self_checkout/views.py`** — Sin cambios (rutas, permisos, validaciones intactos).
- **`self_checkout/urls.py`** — Sin cambios.
- **`self_checkout/permissions.py`** — Sin cambios.
- **`core/utils/template_selector.py`** — Sin cambios.
- **`core/middleware/base_middleware.py`** — Sin cambios.

### Pendiente de limpieza

| Archivo | Acción | Motivo |
|---|---|---|
| `_kiosco_script.html` | Eliminar | Dead code confirmado, nunca incluido. No se pudo borrar en esta sesión (permisos). |

---

## 5. Tests de regresión

### Archivo: `self_checkout/tests/test_mobile_templates.py`

| Clase | Tests | Qué valida |
|---|---|---|
| `DeviceDetectionMiddlewareTest` | 5 | Chrome desktop, iPhone, Android, iPad, UA vacío |
| `TemplateSelectorTest` | 5 | Desktop original, mobile existente, fallback, sin subdirectorio, sin atributo |
| `MobileTemplatesExistTest` | 1 | 6 templates mobile (incluyendo `_utils.html`) se cargan sin error |
| `KioscoMobileInheritanceTest` | 1 | `mobile/kiosco.html` extiende `self_checkout/kiosco.html` |
| **`MobileAccessibilityTest`** | **6** | **ARIA en selector, carritos, config, talonarios, kiosco (reduced-motion), utils (aria-live/busy)** |
| **`MobileUtilsInclusionTest`** | **2** | **selector y carritos incluyen `_utils.html` y usan `SynapMobile`** |

**Total: 20 tests** (12 previos + 8 nuevos)

### Comando de ejecución

```bash
docker exec Synap_app python manage.py test self_checkout.tests.test_mobile_templates --verbosity=2
```

**Nota:** No se pudieron ejecutar en esta sesión (Docker no accesible desde el entorno). Ejecutar manualmente antes del merge.

---

## 6. Checklist QA manual

### Desktop (regresión — no debe haber cambios)

- [ ] Chrome: Selector → abrir kiosco → operar TPV completo → emitir comprobante
- [ ] Firefox: misma secuencia
- [ ] Config list, carritos pendientes, talonarios: layout tabular intacto
- [ ] Formularios (config_form, talonarios_edit/create, punto_venta_create): sin cambios

### Mobile

- [ ] **Selector kiosco:** Skeleton visible durante carga → cards con badges → Abrir muestra "Abriendo…" → redirección
- [ ] **Kiosco TPV:** Layout single-column → carrito como bottom sheet con handle visual → modales fullscreen → inputs sin zoom iOS
- [ ] **Carritos pendientes:** Filtro por estado + búsqueda → contador actualiza → Reintentar/Emitir/Eliminar funcionales → toast verde/rojo
- [ ] **Config list:** Cards con dl/dt/dd → Editar lleva al formulario → nav con acciones
- [ ] **Talonarios:** Selector PV → cards con Modificar → nav con acciones
- [ ] **Focus:** Tab navega todos los elementos interactivos con anillo visible azul
- [ ] **Reduced motion:** Con `prefers-reduced-motion: reduce` activado, no hay animaciones
- [ ] **Notch:** En iPhone X+, el bottom sheet respeta safe area inset

### Permisos (sin cambios)

- [ ] Usuario sin `self_checkout.admin` NO ve config/talonarios
- [ ] Usuario sin `self_checkout.supervisor` NO ve carritos
- [ ] Rutas API (`/api/self-checkout/*`) mantienen validación de permisos

---

## 7. Riesgos

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| `_utils.html` cargado en desktop por error de include | Baja | JS innecesario en desktop | Solo se incluye en templates `mobile/`, nunca en desktop |
| CSS `!important` en kiosco mobile se desincroniza con desktop | Media | Layout roto en mobile | Tests de herencia + QA manual |
| `SynapMobile` colisiona con otro global | Baja | JS roto | Namespace encapsulado en IIFE |
| Skeleton flash si API responde < 100ms | Baja | Parpadeo visual | Se remueve skeleton inmediatamente al recibir datos |
| `::before` handle interfiere con scroll del bottom sheet | Baja | UX incómoda | Handle es decorativo (no interactivo), no bloquea scroll |

---

## 8. Decisiones de diseño

1. **Partial JS vs archivo estático:** Se eligió partial (`_utils.html`) sobre un archivo `.js` estático porque permite usar template tags de Django si fuera necesario en el futuro, y simplifica el include sin dependencia de collectstatic.

2. **`SynapMobile` como namespace global:** Encapsulado en IIFE para evitar contaminación. Los templates mobile lo usan explícitamente.

3. **Toast unificado con `id="synap-toast"`:** Reemplaza los diversos `id="error-toast"` y `id="toast"` de los templates originales. Posición configurable (`top` / `bottom`).

4. **Semántica `<dl>/<dt>/<dd>` en config y talonarios:** Reemplaza `<div>/<span>` genéricos para datos clave-valor. Mejora accesibilidad y parseo por lectores de pantalla.

5. **`<nav>` para barras de acciones:** Reemplaza `<div>` genéricos en config_list y talonarios_list.

6. **Handle visual del bottom sheet:** Pseudoelemento CSS puro, sin interacción. En una iteración futura podría convertirse en toggle expandir/colapsar.

7. **No se modificó el desktop:** Cero riesgo de regresión en producción desktop.

---

## 9. Relación con documentación existente

- **`docs/TPV_MOBILE_PLAN_Y_IMPL.md`**: Plan original de implementación mobile (commit `9726b765`). Este documento complementa ese plan con el refactor posterior.
- **`docs/general/PLAN_PRINCIPAL_FODA_BRECHAS_SYNAP.md`**: Plan oficial del proyecto. El refactor respeta el flujo de ramas y las medidas de seguridad descritas.

---

## 10. Próximos pasos

1. **Ejecutar tests:** `docker exec Synap_app python manage.py test self_checkout.tests.test_mobile_templates -v2`
2. **QA manual** con dispositivos reales (iPhone, Android, iPad).
3. **Eliminar `_kiosco_script.html`** manualmente (dead code).
4. **Limpiar archivos duplicados** (`* 2.py`, `* 2.html`) — fuera de alcance de este refactor.
5. **Stitch interactivo:** Cuando se estabilice la auth de Gemini+Stitch, ejecutar los prompts documentados (§2.3) para validar/mejorar las decisiones visuales.
6. **Bottom sheet interactivo:** Convertir handle visual en toggle expandir/colapsar con gesture.
7. **Rotar API key** expuesta en chat de configuración previa (pendiente de §seguridad del 2/3/26).
