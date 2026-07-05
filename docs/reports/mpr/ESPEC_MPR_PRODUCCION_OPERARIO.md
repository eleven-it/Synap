# Especificación: Reporte MPR — Producción por operario (tabla en Reportes MPR)

**Estado: IMPLEMENTADO (hub Producción)**  
**Prioridad: Media**  
**Módulos afectados:** mpr (views, services, templates)  
**Ubicación UI:** `/mpr/reportes/` → Grupo **Producción** → **Por operario**

---

## 1. Resumen

Ranking de productividad por operario desde **`mpr_parte_linea`** (flujo MPR diario).

---

## 2. Data sources

| Origen | Uso |
|--------|-----|
| `mpr_parte_linea` + `mpr_parte` | Unidades, partes y componentes por operario en período |
| `sue_abm_empleado` | Nombre del operario (fallback en `operario_nombre` de línea) |

**Servicio MPR:** `reporte_mpr_operario_parte(base_empresa, fecha_desde, fecha_hasta, limit=200)`.

**Nota:** `reporte_mpr_produccion_por_operario` (lista_produccion_historico / OPT) ya no se expone en `/mpr/reportes/`.

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
