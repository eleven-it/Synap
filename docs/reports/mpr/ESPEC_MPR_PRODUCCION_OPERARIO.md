# Especificación: Reporte MPR — Producción por operario (tabla en Reportes MPR)

**Estado: PENDIENTE**  
**Prioridad: Media**  
**Módulos afectados:** mpr (views, services, templates)  
**Ubicación UI:** Menú MPR → Reportes → pestaña "Producción por operario"

---

## 1. Resumen

Tabla de solo lectura en la sección **Reportes** del menú MPR. Muestra por **operario**: número de OPT asignadas y opcionalmente cantidad total de packs. Incluye filtro opcional por **fecha_desde** y **fecha_hasta** (período). No es reporte del módulo Reports.

---

## 2. Data sources

| Origen | Uso |
|--------|-----|
| `lista_produccion_agrupada` | Campo `id_operario_opt` para agrupar por operario |
| `sue_abm_empleado` | Nombre del operario |
| `movimiento_stock` (opcional) | Para filtrar por período si se usa fecha de movimiento tipo OPT |

**Servicio MPR:** `reporte_mpr_produccion_por_operario(base_empresa, fecha_desde=None, fecha_hasta=None, limit=200)`.

---

## 3. Entradas

| Parámetro | Origen | Obligatorio | Descripción |
|-----------|--------|-------------|-------------|
| `tipo` | GET `?tipo=produccion_operario` | Sí | Fija el reporte en la vista Reportes MPR |
| `base_empresa` | Sesión | Sí | Para ejecutar el servicio |
| `fecha_desde` | GET | No | Inicio período (YYYY-MM-DD) |
| `fecha_hasta` | GET | No | Fin período (YYYY-MM-DD) |

---

## 4. Salidas (contexto vista)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `filas` | list[dict] | Una fila por operario: nombre_operario (o id), nro_opt_asignadas, cantidad_packs (opcional) |
| `titulo_reporte` | str | `"Producción por operario"` |
| `tipo_reporte` | str | `"produccion_operario"` |

---

## 5. Reglas de negocio

- Agrupar por `id_operario_opt`; resolver nombre desde `sue_abm_empleado`.
- Si se envían fechas: filtrar OPT/movimientos por ese rango (definir si por fecha de creación OPT o por fecha de movimiento).
- Operarios sin OPT en el período: pueden aparecer con 0 o no listarse (definir en implementación).
- Sin `base_empresa` → redirect con mensaje (comportamiento ReportesMPRView).

---

## 6. Criterios de aceptación

| ID | Descripción |
|----|-------------|
| CA-PO-01 | GET `/mpr/reportes/?tipo=produccion_operario` con usuario logueado y base_empresa → HTTP 200, `context["filas"]` presente, `context["titulo_reporte"]` = "Producción por operario". |
| CA-PO-02 | Con `fecha_desde` y `fecha_hasta` → filtro de período aplicado (filas coherentes con el rango). |
| CA-PO-03 | Operarios sin OPT en período: pueden mostrarse con 0 o no aparecer (documentar criterio en spec o en código). |

---

## 7. Casos borde

- Ningún operario con OPT: `filas = []` o filas con cantidad 0 según criterio.
- `id_operario_opt` NULL: agrupar como "Sin asignar" o excluir (definir).
