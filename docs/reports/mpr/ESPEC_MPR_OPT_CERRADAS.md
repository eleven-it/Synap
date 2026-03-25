# Especificación: Reporte MPR — OPT cerradas (tabla en Reportes MPR)

**Estado: PENDIENTE**  
**Prioridad: Media**  
**Módulos afectados:** mpr (views, services, templates)  
**Ubicación UI:** Menú MPR → Reportes → pestaña "OPT cerradas"

---

## 1. Resumen

Tabla de solo lectura en la sección **Reportes** del menú MPR. Lista OPT **cerradas**: `en_proceso_produccion = 'No'` y `cantidad_pendiente_prod = 0`. Opcional: filtrar por “fecha de cierre” (último movimiento de la OPT) en rango **fecha_desde**–**fecha_hasta**. No es reporte del módulo Reports.

---

## 2. Data sources

| Origen | Uso |
|--------|-----|
| `lista_produccion_agrupada` | Filtro: en_proceso_produccion = 'No', cantidad_pendiente_prod = 0. Agrupar por id_opt (una fila por OPT). |
| `movimiento_stock` (opcional) | Para obtener fecha máxima de movimiento por OPT y filtrar por rango |

**Servicio MPR:** `reporte_mpr_opt_cerradas(base_empresa, fecha_desde=None, fecha_hasta=None, limit=200)`.

---

## 3. Entradas

| Parámetro | Origen | Obligatorio | Descripción |
|-----------|--------|-------------|-------------|
| `tipo` | GET `?tipo=opt_cerradas` | Sí | Fija el reporte en la vista Reportes MPR |
| `base_empresa` | Sesión | Sí | Para ejecutar el servicio |
| `fecha_desde` | GET | No | Inicio rango (fecha cierre / última actividad) |
| `fecha_hasta` | GET | No | Fin rango |

---

## 4. Salidas (contexto vista)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `filas` | list[dict] | Una fila por OPT cerrada: id_opt, articulo(s), cantidad_total, fecha_cierre o ultima_actividad |
| `titulo_reporte` | str | `"OPT cerradas"` |
| `tipo_reporte` | str | `"opt_cerradas"` |

---

## 5. Reglas de negocio

- Solo filas con `en_proceso_produccion = 'No'` y `cantidad_pendiente_prod = 0`.
- Si no hay columna explícita de fecha de cierre: aproximar por fecha máxima de movimientos de esa OPT (movimiento_stock vinculado por codigo_movimiento o id_lista).
- Con fecha_desde/fecha_hasta: filtrar OPT cuya “fecha cierre” (o última actividad) esté en el rango.
- Sin `base_empresa` → redirect con mensaje (ReportesMPRView).

---

## 6. Criterios de aceptación

| ID | Descripción |
|----|-------------|
| CA-OC-01 | GET `/mpr/reportes/?tipo=opt_cerradas` con usuario logueado y base_empresa → HTTP 200, `context["filas"]` presente, `context["titulo_reporte"]` = "OPT cerradas". |
| CA-OC-02 | Solo se listan OPT cerradas (en_proceso = 'No', pendiente = 0). |
| CA-OC-03 | Con `fecha_desde` y `fecha_hasta` → filas filtradas por rango de fecha de cierre/última actividad (si está implementado). |

---

## 7. Casos borde

- Ninguna OPT cerrada: `filas = []`.
- OPT con múltiples ítems (múltiples filas en lista_produccion_agrupada con mismo id_opt): una fila por OPT con artículo(s) resumido o concatenado.
- Sin movimiento_stock para calcular fecha: fecha_cierre NULL o no mostrada.
