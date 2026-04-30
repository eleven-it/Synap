# SDD — Objetivos REM/PED por artículo + KPI ventas consolidado

**Fecha:** 30/04/2026  
**Cambio (slug):** `objetivos-bo-rem-ped-art-y-ventas-kpi`  
**Contexto analítico:** `ANALISIS_REMITOS_PED_ARMADO_LINEAS_VS_CABECERA_OBJETIVOS.md`  
**Rollback operativo:** `ROLLBACK_O_NOTA_IMPLEMENTACION_REM_PED_ART_OBJETIVOS.md`

## Artefactos Engram (proyecto almacén detectado: `sebastian`)

| Fase | Clave tópico | Observación (referencia sesión) |
|------|----------------|----------------------------------|
| Exploración | `sdd/objetivos-bo-rem-ped-art-y-ventas-kpi/explore` | #25 |
| Propuesta | `sdd/objetivos-bo-rem-ped-art-y-ventas-kpi/propose` | #26 |
| Especificación | `sdd/objetivos-bo-rem-ped-art-y-ventas-kpi/spec` | #27 |
| Diseño | `sdd/objetivos-bo-rem-ped-art-y-ventas-kpi/design` | #28 |
| Tareas | `sdd/objetivos-bo-rem-ped-art-y-ventas-kpi/tasks` | #29 |

Para el detalle completo usar `mem_get_observation` con el id correspondiente en Engram.

## Resumen ejecutivo

1. **Informe ventas-objetivos-vs-bo:** agregar importes por artículo para remitos (líneas `stockp`, período de facturación) y pedidos en armado (sin filtro de fecha en cabecera PED), con merge/rollup análogo al BO; campos JSON sugeridos en diseño: `remitos_lineas`, `pedidos_armado_lineas` en nodos artículo.
2. **Resumen ventas (`sales_summary`):** alinear `_get_pedidos_pendientes_total` con `filtrar_por_fecha=False` como en total consolidado operativo; recalcular `total_consolidado`; actualizar etiquetas/tooltips si cambia el significado respecto a “pedidos del período”.

## Siguiente paso recomendado

**`sdd-apply`** (implementación por fases según lista de tareas en Engram #29).

## Contrato de documentación en repo

- `SPEC_INFORME_OBJETIVOS_VENTAS_BO.md` deberá actualizarse en la fase de implementación para reflejar columnas/contrato JSON y semántica temporal.
- Tras cada fase atómica, anotar SHAs en `ROLLBACK_O_NOTA_IMPLEMENTACION_REM_PED_ART_OBJETIVOS.md`.
