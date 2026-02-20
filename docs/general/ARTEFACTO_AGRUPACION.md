# Artefacto de agrupación (UI y comportamiento)

Cuando en el proyecto se pida **agrupación** para listados o reportes, debe usarse el **mismo artefacto** que en el dashboard de reportes (BO Stock / Facturación).

## Referencia visual y código

- **Pantalla de referencia:** Reportes → Dashboard → BO Stock Facturación → cualquier pestaña (Backorder, Detalle con stock, etc.).
- **HTML:** `reports/templates/reports/dashboard_detail.html` (buscar "Agrupar por", "Buscar campo de agrupación", `tags-filter-container`, `tags-chips`, `tags-dropdown`).
- **JS:** `reports/static/reports/js/bo_stock_facturacion.js` → `initializeBoGroupByUI` (opciones, chips, búsqueda, dropdown).

## Elementos del artefacto

1. **Etiqueta:** "Agrupar por" (texto superior al control).
2. **Control:**
   - Un `<select name="..." id="..." multiple class="hidden">` con las opciones (value = clave, text = etiqueta).
   - Un contenedor visible (`tags-filter-container`) que incluye:
     - `tags-chips`: div donde se renderizan los chips de los campos seleccionados (cada uno con botón × para quitar).
     - Input de búsqueda: `placeholder="Buscar campo de agrupación..."`, `autocomplete="off"`.
     - `tags-dropdown`: lista desplegable de opciones aún no seleccionadas, filtrada por el texto de búsqueda.
3. **Texto de ayuda:** "Puedes seleccionar múltiples campos para agrupar. El orden determina los niveles de agrupación."

## Comportamiento

- El usuario puede seleccionar **varios campos**; el **orden** de selección define los **niveles de agrupación** (primero = nivel superior, etc.).
- Los seleccionados se muestran como **chips**; se pueden quitar con ×.
- La búsqueda filtra las opciones disponibles en el dropdown.
- En envío de formulario (GET o POST), el parámetro se envía **múltiple** (ej. `agrupar_por=fecha&agrupar_por=motivo_movimiento`). Backend: `request.GET.getlist("agrupar_por")` o equivalente.

## Dónde está implementado

- **Reportes (BO):** `dashboard_detail.html` + `bo_stock_facturacion.js` (agrupación en cliente, colapso/expansión).
- **Stock – Consultas y Anulaciones:** La agrupación está **separada de la búsqueda**: el formulario solo lleva filtros; "Agrupar por" aparece encima de la tabla y se aplica en cliente sobre los resultados (`stock/templates/stock/visualiza_movimientos.html` con datos en JSON; colapso/expansión como en BO).

## Uso en nuevas pantallas

Replicar la misma estructura HTML (select múltiple oculto + contenedor tags + input + dropdown) y la lógica JS (chips, add/remove, filtro de búsqueda, sincronización con el select para el submit). Si la pantalla está en Django con submit GET, los valores seleccionados se pueden pre-rellenar con `data-initial="val1,val2"` en el contenedor y leerlos en JS para marcar las opciones del select y pintar los chips al cargar.
