# Especificación: Reporte MPR — OPT atrasadas

**Estado: PENDIENTE**  
**Prioridad: Alta**  
**Módulos afectados:** reports (QueryRunnerService), mpr (services)  
**Slug reporte (Reports):** `mpr-opt-atrasadas`

---

## 1. Resumen

Reporte de solo lectura que lista OPT (Órdenes de Producción de Trabajo) con **fecha objetivo vencida** y **cantidad pendiente > 0**. Pensado para panel de producción en tiempo real. Se consume desde el catálogo de Reports, dashboard_detail y API de consulta. La base de datos (`base_empresa`) se obtiene desde la sesión del usuario.

---

## 2. Data sources

| Origen | Uso |
|--------|-----|
| `lista_produccion_agrupada` | Campos: `fecha_objetivo`, `cantidad_pendiente_prod`, `id_lista_produccion`, `id_opt`, `id_articulo`, relación con pedido |
| `articulo` | Código y descripción del artículo |
| `comp_ped` | Opcional: número de pedido asociado |

**Servicio MPR:** `listar_opt_listado(base_empresa, solo_atrasadas=True)` o `reporte_mpr_opt_atrasadas(base_empresa, limit=200)`.

---

## 3. Entradas

| Parámetro | Origen | Obligatorio | Descripción |
|-----------|--------|-------------|-------------|
| `base_empresa` | `payload.filters.base_empresa` (sesión) | Sí | Nombre de la base MySQL AdministraNET |
| `limit` | config o payload | No | Límite de filas (default: 200) |

---

## 4. Salidas

**Tipo:** `QueryResult` (reports).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `meta.slug` | str | `"mpr-opt-atrasadas"` |
| `data` | list[dict] | Una fila por OPT atrasada. Columnas: `id_lista`, `id_opt`, `codigo_articulo`, `descripcion_articulo`, `fecha_objetivo`, `dias_atraso`, `cantidad_pendiente_prod`, `nro_pedido` (u otras acordadas) |
| `totals` | dict | Al menos `total_opt_atrasadas` (int) = cantidad de filas |
| `notes` | list[str] | Incluir base_empresa usada; mensaje de error si falta base_empresa |

---

## 5. Reglas de negocio

- Solo se incluyen filas donde:
  - `fecha_objetivo < CURDATE()` (fecha objetivo vencida).
  - `cantidad_pendiente_prod > 0`.
- Orden: por `fecha_objetivo` ascendente (más atrasadas primero) o por urgencia.
- Si no hay `base_empresa`, no se ejecuta consulta MySQL; se devuelve resultado con data vacía y note explicativa (o error controlado).

---

## 6. Criterios de aceptación

| ID | Descripción |
|----|-------------|
| CA-OPT-A-01 | Sin `base_empresa` en payload → mensaje en `notes` y `data` vacía (o error controlado sin excepción no capturada). |
| CA-OPT-A-02 | Con `base_empresa` y datos existentes → `data` con al menos las columnas definidas en §4. |
| CA-OPT-A-03 | `totals` incluye el total de filas (ej. `total_opt_atrasadas`). |
| CA-OPT-A-04 | Respuesta API incluye `meta.slug = "mpr-opt-atrasadas"`. |

---

## 7. Casos borde

- Base de datos inexistente o inaccesible: devolver data vacía y note con error.
- Ninguna OPT atrasada: `data = []`, `totals.total_opt_atrasadas = 0`.
- `fecha_objetivo` NULL: la fila no se considera atrasada (excluir).
