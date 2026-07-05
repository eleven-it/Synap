# Mensajes Django — toasts globales Synap

Referencia para feedback de éxito/error en toda la aplicación web Synap.

## Problema resuelto

Antes, muchas pantallas **no consumían** los mensajes Django (`django.contrib.messages`) o los mostraban como **banners inline** dentro del contenido. Eso provocaba:

1. **Mensajes en pantalla equivocada** — p. ej. avisos de Config. Depósitos aparecían al abrir el Tablero de producción.
2. **Persistencia aparente** — los mensajes viven en sesión hasta que alguna plantilla los itera; si la pantalla origen no los mostraba, quedaban para la siguiente visita.
3. **Pérdida de espacio vertical** — varios banners empujaban tablas y grillas hacia abajo.

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

_Ver también `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md` para patrones UI MPR._
