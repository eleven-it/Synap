# Listado OPT — columna Estado (antes Estado + Fase)

## Análisis

En `opt_list.html` convivían dos columnas:

| Columna | Criterio en plantilla | Contenido típico |
|---------|------------------------|------------------|
| **Estado** (eliminada) | `fase_clave == cerrada` → Cerrada; `en_proceso_produccion == Si` → En proceso; si no → Pendiente; sin OPT creada → Demanda | Agrupación gruesa (~4 valores) |
| **Fase** (ahora **Estado**) | `fase_clave` + `etiqueta_fase` desde `OptListView` | Texto operativo: Demanda, Cerrada, Pendiente, Lista para cerrar, En producción (OPP pendiente), En producción, etc. |

**Conclusión:** no son el mismo campo en origen: la primera columna **ocultaba** matices que la segunda ya mostraba (p. ej. «En proceso» vs «Lista para cerrar»). Para evitar duplicidad visual y priorizar la información útil, se **eliminó** la columna agregada y se **renombró** «Fase» a **«Estado»**, manteniendo el render por `fase_clave` / `etiqueta_fase`.

El filtro GET **Estado** (Todos / En proceso / Pendiente / Atrasadas) sigue filtrando en servidor por `en_proceso_produccion` y atrasadas; no se confunde con el encabezado de columna.

## Referencia de código

- Vista: `mpr/views.py` — `OptListView.get_context_data` (asigna `fase_clave`, `etiqueta_fase`).
- Plantilla: `mpr/templates/mpr/opt_list.html`.
