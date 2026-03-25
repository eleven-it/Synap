# Especificación: Reporte MPR — Resumen pedidos por estado

**Estado: PENDIENTE**  
**Prioridad: Alta**  
**Módulos afectados:** reports (QueryRunnerService), mpr (services)  
**Slug reporte (Reports):** `mpr-pedidos-estado`

---

## 1. Resumen

Conteo de pedidos (`comp_ped`) por **estado de producción** (`estado_pedido_opt`): Pendiente, Produccion, Parcial, Terminado. Pensado para panel de producción en tiempo real. Se consume desde el catálogo de Reports, dashboard_detail y API de consulta. `base_empresa` desde sesión.

---

## 2. Data sources

| Origen | Uso |
|--------|-----|
| `comp_ped` | Campo `estado_pedido_opt`. Acceso vía `listar_pedidos_fabrica(base_empresa, limit=500, estado=None)` |

**Servicio MPR:** `reporte_mpr_pedidos_por_estado(base_empresa)` — agrega por estado y devuelve lista de `{ "estado": str, "cantidad": int }`.

---

## 3. Entradas

| Parámetro | Origen | Obligatorio | Descripción |
|-----------|--------|-------------|-------------|
| `base_empresa` | `payload.filters.base_empresa` (sesión) | Sí | Nombre de la base MySQL |

---

## 4. Salidas

**Tipo:** `QueryResult` (reports).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `meta.slug` | str | `"mpr-pedidos-estado"` |
| `data` | list[dict] | Una fila por estado: `{ "estado": str, "cantidad": int }`. Estados: Pendiente, Produccion, Parcial, Terminado. |
| `totals` | dict | `total_pedidos` (int) = suma de todas las cantidades |
| `notes` | list[str] | base_empresa usada; mensaje si falta base_empresa |

---

## 5. Reglas de negocio

- Estados fijos: **Pendiente**, **Produccion**, **Parcial**, **Terminado**.
- Incluir los cuatro estados en `data`; si un estado no tiene pedidos, cantidad = 0 (tabla completa para gráficos/KPIs).
- Sin `base_empresa` → no ejecutar consulta; data vacía o error en notes.

---

## 6. Criterios de aceptación

| ID | Descripción |
|----|-------------|
| CA-PE-01 | Sin `base_empresa` → `data` vacía o error en `notes`. |
| CA-PE-02 | Con datos → exactamente 4 filas en `data` (una por estado), cada una con `cantidad >= 0`. |
| CA-PE-03 | Suma de `cantidad` de las 4 filas = `totals["total_pedidos"]` (o equivalente). |
| CA-PE-04 | `meta.slug = "mpr-pedidos-estado"`. |

---

## 7. Casos borde

- Base inexistente: data vacía, note con error.
- Ningún pedido: 4 filas con cantidad 0, total_pedidos = 0.
- Valores de `estado_pedido_opt` no estándar en DB: normalizar a los 4 estados o agrupar en "Otro" según política.
