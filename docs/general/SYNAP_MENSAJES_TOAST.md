# Mensajes Django — toasts globales Synap

Referencia para feedback de éxito/error en toda la aplicación web Synap.

## Problema resuelto

Antes, muchas pantallas **no consumían** los mensajes Django (`django.contrib.messages`) o los mostraban como **banners inline** dentro del contenido. Eso provocaba:

1. **Mensajes en pantalla equivocada** — p. ej. avisos de Config. Depósitos aparecían al abrir el Tablero de producción.
2. **Persistencia aparente** — los mensajes viven en sesión hasta que alguna plantilla los itera; si la pantalla origen no los mostraba, quedaban para la siguiente visita.
3. **Pérdida de espacio vertical** — varios banners empujaban tablas y grillas hacia abajo.

## Prohibido diálogos nativos

En la UI Synap **no** se usan los diálogos nativos del navegador
(`alert`, `confirm`, `prompt`, ni `window.alert/confirm/prompt`): bloquean el
hilo, ignoran tema e idioma y no se pueden testear. Regla permanente en
**`.cursor/rules/modales-sin-dialogos-nativos.mdc`**.

| Necesidad | Usar |
|-----------|------|
| Confirmación destructiva/operativa (eliminar, anular, archivar, aprobar/rechazar) | Modal Synap: patrón VCM `ecom/config_vendedor_cliente_marca.html`, o `ecom/pedidos_modal.html` + `order_dialogs.mjs`, o modal Alpine local tipo hub (`confirmOpen` + `pedirConfirmacion`) |
| Feedback AJAX corto (éxito/error sin recargar) | `mprShowAviso` (MPR) / `SynapMessages.show` — **nunca** `alert` |
| Entrada de texto (motivo de rechazo, nota) | Modal con `input`/`textarea` y validación de obligatorio — **nunca** `prompt` |

Excepción: solo la degradación **ya documentada** (p. ej. el fallback interno
de `mprShowAviso` a `window.alert` cuando el partial no está cargado). No
introducir nuevos fallbacks a diálogos nativos en pantallas nuevas.

## Solución canónica

| Pieza | Ubicación |
|-------|-----------|
| Partial toast | `theme/templates/partials/synap_messages_toast.html` |
| JS global | `theme/static/js/synap-messages.js` (`SynapMessages.show`, `initFromDom`) |
| Inclusión | `theme/templates/base_app.html` (todas las pantallas que extienden `base_app` / `base_mpr`) |

Comportamiento:

- **Posición fija** — esquina superior derecha, debajo del navbar (`z-index` 100).
- **Auto-cierre** — éxito ~5 s, info ~4 s, warning ~6 s, error ~8 s; pausa al pasar el mouse.
- **Cierre manual** — botón ×.
- **Deduplicación** — mismo texto no se apila dos veces en la misma carga.
- **Consumo único** — el partial itera `{% for message in messages %}` una sola vez por request.

## Reglas para desarrollo

1. **No** añadir bloques `{% if messages %}` en plantillas hijas de `base_app.html`.
2. En vistas, seguir usando `messages.success(request, "...")` / `messages.error(...)` en español.
3. Para feedback **AJAX** sin recargar, usar `SynapMessages.show('Texto', 'success')` desde JS.
4. Login y flujos con `login_base.html` mantienen su propio tratamiento hasta unificar.

## Pantallas migradas (2026-07-04)

Se quitaron bloques inline en MPR (tablero, parte, wizard, etc.), core, compras, fe_afip, self_checkout e ia. Reports conserva toasts propios del builder.

---

## Feedback operativo MPR en modal — `mprShowAviso`

En pantallas MPR (o que extienden `mpr/base_mpr.html`) el feedback de **acciones AJAX / validación en pantalla** (error de validación, conflicto, éxito de una acción hecha en la propia página) se muestra **siempre en modal**, no como banner inline.

### Cuándo usar cada mecanismo

| Caso | Mecanismo |
|------|-----------|
| Mensajes Django tras recarga/redirección (`messages.success/error`) | Toast global `SynapMessages` (partial `synap_messages_toast.html`) |
| Feedback AJAX genérico sin recargar en cualquier pantalla | `SynapMessages.show('Texto', 'success')` |
| Feedback operativo MPR en la propia página (validación, conflicto, éxito de acción AJAX) | **Modal `mprShowAviso`** |
| Carga/progreso de un POST MPR largo | Modal de loading (`mprShowPostLoading` / `mpr_post_loading_modal.html`) |

### API

Partial: `mpr/templates/mpr/includes/mpr_aviso_modal.html`, incluido desde `mpr/base_mpr.html` en `{% block extra_js %}` (junto al modal de loading). Overlay `z-[90]` (por debajo del loading `z-100`).

```js
// Forma corta: mensaje + tipo (default 'error')
window.mprShowAviso('La marca ya está asignada a otro vendedor.', 'error');
window.mprShowAviso('Relación creada.', 'success');

// Formas de tipo: 'error' (rojo) | 'success' (emerald) | 'warning' (ámbar) | 'info' (púrpura)

// Forma con objeto (título personalizado)
window.mprShowAviso('', { tipo: 'warning', titulo: 'Atención', mensaje: 'Revise las cantidades.' });

// Cerrar programáticamente (también cierra con «Entendido», Escape o click en backdrop)
window.mprHideAviso();
```

Degradación segura: si el partial no está presente, `mprShowAviso` cae a `window.alert`.

### Patrón en Alpine

En componentes Alpine (VCM, armado surtido, etc.) se expone un helper local `mostrarAviso(texto, tipo)` que delega en `window.mprShowAviso`, evitando estado `error`/`mensaje` con banners `x-show`.

### Pantallas migradas a modal (2026-07-16)

- `ecom/config_vendedor_cliente_marca.html` (VCM): se quitaron los banners `x-show="mensaje"` / `x-show="error"`; helper `mostrarAviso`.
- `mpr/armado_surtido.html`: `mostrarMensaje` ahora usa `mprShowAviso` (mapea `ok`→`success`, `warn`→`warning`); se quitó el banner `mensajeLote`.
- `mpr/imputacion_armado_1ra.html`: el banner `#imputacion-error-cliente` se reemplazó por `mprShowAviso`.

### Pantallas migradas a modal (2026-07-20)

- `ecom/pedido_masivo_sucursales.html` + `ecom/static/ecom/js/pedido_masivo_app.mjs` (Pedido simple / Pedido masivo): se quitaron los banners inline de la región «Mensajes» (`error`, `mensajeOk`, `advertenciasCarga`, `previewWarningBloqueante`, `alertasUltimoError`). Helper local `mostrarAviso(texto, tipo, titulo)` que delega en `mprShowAviso`.
  - Errores → modal `error`. El error de confirmación usa título **«No se pudo confirmar»** (antes hardcodeado como título del banner para todos los errores).
  - Éxito (confirmar, anular borrador/pedido, mail, repetir) → modal `success`.
  - Avisos de conversión/redondeo al cargar un PED (`advertenciasCarga`) → modal `warning` título **«Avisos al cargar el pedido»**.
  - `previewWarningBloqueante` sigue mostrándose dentro del modal de confirmación (`masivo_confirmar`); el detalle por sucursal del lote ya viaja en el mensaje del modal de error de confirmación (`_formatoErrorConfirmacion`), por lo que no se abre un modal extra de «Advertencias del lote».
  - Leftover intencional: el empty-state «Este cliente no tiene sucursales (domicilios) activas» se conserva como **estado de página** (no feedback de acción).

### Leftovers intencionales (no migrados)

Se dejaron por ser **ayuda contextual / estados de página o dropdown**, no feedback de acción:

- `mpr/trazabilidad_opt.html`: banner ámbar server-rendered `{% if fuentes_fallidas %}` (aviso de disponibilidad de datos de la página).
- `mpr/best_migration/*.html`: estados inline de dropdown de búsqueda («Error al buscar. Reintentá.», «Sin resultados») y errores de campo inline (`errorMsg`) junto a acciones.

---

_Ver también `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md` para patrones UI MPR._
