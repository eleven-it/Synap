# Rendimiento: jerarquía Objetivos de ventas vs BO

## Problema

Al expandir la cabecera de un **vendedor** con muchos clientes y detalle rubro/subrubro/artículo, el hilo principal podía tardar varios segundos: muchas consultas `querySelectorAll` sobre todo el contenedor por cada cliente y refiltrado de búsqueda sobre **toda** la tabla con texto ≥ 2 caracteres.

## Cambios implementados (30/04/2026)

1. **Toggle de vendedor (HTML actual):** con `<tbody data-vo-vendor-details>` el expand/colapso es **`tbody.hidden` solamente** (sin barrido de `classList` en todo el subárbol). **`applyVendorGroupVisibilityAfterExpand`** queda solo para **tabla legacy** sin ese `tbody` (una pasada O(filas) sobre `tr[data-vo-vendor-group="…"]`).
2. **`applyClientDetalleVisibility`:** resuelve el grupo del vendedor con la fila cabecera del cliente (`tr[data-vo-client]`) y reutiliza el mismo barrido acotado.
3. **Búsqueda tras toggle:** con filtro activo (≥ 2 caracteres), `applySearchFilterVendorSubtree` actualiza solo filas de ese vendedor y su fila cabecera; el filtrado completo al escribir en el input no cambia.
4. **Filas hoja (artículo):** clase `vo-jerarquia-cv-art` con `content-visibility: auto` y `contain-intrinsic-size` en la plantilla del informe para reducir coste de pintura.
5. **Overlay de espera (`#vo-jerarquia-busy-overlay`):** queda disponible en la plantilla, pero **desactivado en runtime** (`VO_BUSY_OVERLAY_ENABLED = false`) por UX, ya que el lag de expansión de vendedor quedó mitigado y se prioriza respuesta inmediata al clic.
6. **Antipatrón corregido:** no llamar `queryVendorSubtreeRows` / conteos **antes** de mostrar el overlay en el clic de vendedor: `tbody.querySelectorAll("tr")` recorría miles de nodos y retrasaba el modal ~el mismo tiempo que el lag percibido. Con `<tbody data-vo-vendor-details>`, las filas se obtienen con `tbody.rows` (hijos directos) y solo en la rama **legacy** o dentro del callback tras el primer pintado.

7. **Carga diferida de detalle (VO y VPV):** cuando el cliente está colapsado (o el bloque Con/Sin compra está cerrado), no se insertan filas rubro/subrubro/artículo en el DOM inicial. Se materializan al expandir el cliente; con búsqueda activa (≥ 2 caracteres) se materializa bajo demanda para preservar coincidencias por texto de detalle.
8. **Colores por columna en VO y VPV (filas de datos):** se restauran fondos suaves por bloque para lectura visual (en VPV, sobre unidades/facturación).

## Cómo medir (baseline y regresión)

1. Abrir el informe `ventas-objetivos-vs-bo` con un período que genere jerarquía grande.
2. Chrome → **Más herramientas** → **Herramientas para desarrolladores** → pestaña **Rendimiento** → grabar.
3. Un solo clic en **expandir** un vendedor pesado; detener la grabación.
4. En el resumen del rango, anotar **Scripting** y **Rendering** (y duración total del evento de clic si se marca el `click`).
5. Repetir con **búsqueda** de 2+ caracteres activa y sin búsqueda.

Objetivo de producto: que el trabajo síncrono perceptible al expandir quede **claramente por debajo de 1 s** en el peor caso habitual; la medición concreta depende del hardware y del volumen de datos.

## Checklist manual post-cambio

- [ ] Expandir / colapsar vendedor: estados Con compra / Sin compra respetan `localStorage` y chevrons.
- [ ] Cliente con detalle: rubro / subrubro / artículo y persistencia de expansión.
- [ ] Búsqueda vacía o 1 carácter: sin regresión; con ≥ 2 caracteres: cabecera de vendedor coherente tras expandir/colapsar.
- [ ] **Expandir todo** / **Contraer todo** y orden.
- [ ] Modo claro y oscuro; cabecera sticky sigue usable.

## Logs de diagnóstico

- **Servidor (terminal / `docker logs Synap_app`):** al completar el informe, `ventas_objetivos_bo_runner` registra `[ventas_objetivos_bo] informe listo` con `clientes_grilla`, conteos de nodos (vendedores, estados, rubros, subrubros, artículos), `tiempo_total_ms` y el dict `fases_ms` de fases internas.
- **Navegador (DevTools → Consola):** prefijo `[vo-jerarquia]` — carga completa de la grilla (`render_dom_ms`, `stats_jerarquia` desde `meta.extra.jerarquia_stats` o recalculado) y cada expandir/colapsar vendedor (`callback_sync_ms`, `desde_evento_click_ms`, `filas_en_subarbol_dom`).

## Archivos

- `reports/static/reports/js/objetivos_ventas_bo.js`
- `reports/templates/reports/dashboard_detail.html` (estilos VO + `?v=` del script)
- `reports/services/ventas_objetivos_bo_runner.py` (log al armar respuesta)
