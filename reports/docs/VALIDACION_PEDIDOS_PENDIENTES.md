# Validación Pedidos pendientes – Datos y consultas

Revisión del reporte **Pedidos pendientes** (`pedidos-pendientes`) frente a `CONTEXTO_TABLAS_VB6_INFORMES.md` y formularios VB6 (Pedido_prep, Pedido_prep_consulta, Pedido, Visualiza_Pedido, Remito, FacturaA/B, etc.).

---

## 1. Resumen del reporte

| Aspecto | Valor |
|--------|--------|
| **Slug** | `pedidos-pendientes` |
| **Nombre** | Pedidos pendientes |
| **Descripción** | Listado de pedidos pendientes de preparación. PED en estado **En preparación** o **Preparado**, no anulados. |
| **Tabla principal** | `comp_ped` (solo cabecera; no se usan renglones en `stockp`) |
| **Filtros** | `fecha_inicio`, `fecha_fin` (o dia/mes/año actual), `base_empresa` |
| **Valor mostrado** | `SubtotalDesc` por pedido; total = `SUM(SubtotalDesc)` |

---

## 2. Consulta actual

```sql
SELECT
    DATE_FORMAT(cp.Fecha, '%d/%m/%Y') AS fecha,
    cp.NroComprobante AS nro_comprobante,
    COALESCE(cp.SubtotalDesc, 0) AS subtotal_desc
FROM comp_ped cp
WHERE cp.Fecha >= %s
  AND cp.Fecha <= %s
  AND cp.TipoComprobante = 'PED'
  AND cp.Anulado = 'No'
  AND cp.Estado IN ('En preparación', 'Preparado')
ORDER BY cp.Fecha DESC, cp.NroComprobante ASC
```

---

## 3. Contexto VB6 relevante

### 3.1 Estados de pedidos (comp_ped.Estado)

En formularios se usan, entre otros:

- **Pendiente**: pedido tomado, aún no en preparación.
- **Parcial**: entrega parcial.
- **En preparación**: asignado a preparación; se está preparando (Pedido_prep actualiza a este estado al asignar).
- **Preparado**: preparación terminada (Pedido_prep actualiza al confirmar).
- **En Remito** / **Cerrado** / **Facturado**: posteriores.

Pedido_prep escribe en `comp_ped`:

- `estado = 'En preparación'` al asignar pedidos a una preparación.
- `estado = 'Preparado'` al marcar como preparados.

Listados “solo En preparación / Preparado” (FacturaA, FacturaB, Remito, Pedido, PFactura, etc.) usan:

```text
comp_ped.Estado IN ('En preparación', 'Preparado')
```

El reporte usa exactamente estos dos estados. **Correcto** respecto a VB6.

### 3.2 Tipo de comprobante

- **PED** = pedidos de venta. **PEDI** = pedidos internos. **PRE** = presupuestos.

El reporte filtra `TipoComprobante = 'PED'`. **Correcto**: solo pedidos de venta.

### 3.3 Anulado

`Anulado = 'No'` se usa en todos los listados de pedidos. **Correcto**.

### 3.4 Valor del pedido (SubtotalDesc vs ImporteVenta)

- En **comp_ped**, VB6 usa tanto `SubtotalDesc` como `ImporteVenta` según formulario (Lista_Comp_Gral muestra `ImporteVenta` para pedidos; otros flujos usan `SubtotalDesc`).
- **Remitos no facturados** y **BO** usan `comp_ped.SubtotalDesc`.
- El reporte usa `COALESCE(cp.SubtotalDesc, 0)`.

**Recomendación:** Confirmar en la base que `comp_ped` tiene `SubtotalDesc` poblado para PED. Si en algún flujo solo se guarda `ImporteVenta`, valorar usar `COALESCE(cp.SubtotalDesc, cp.ImporteVenta, 0)` como respaldo (igual que en exportación a AFIP).

### 3.5 Filtro por fecha

Se filtra por `cp.Fecha` (fecha del pedido) en el rango `[fecha_inicio, fecha_fin]`. En VB6, los listados de preparación suelen filtrar también por fecha. **Correcto**.

---

## 4. Validación campo a campo

| Campo reporte | Origen | VB6 / comp_ped | Conclusión |
|---------------|--------|-----------------|------------|
| **fecha** | `cp.Fecha` formateada | `comp_ped.Fecha` | Correcto. |
| **tipo_comprobante** | `cp.TipoComprobante` | PED | Correcto. |
| **nro_comprobante** | `cp.NroComprobante` | Sí | Correcto. |
| **subtotal_desc** | `COALESCE(cp.SubtotalDesc, 0)` | SubtotalDesc / ImporteVenta | Correcto; validar llenado de SubtotalDesc en DB. |
| **estado** | `cp.Estado` | En preparación, Preparado | Correcto. |

---

## 5. Uso en Sales summary (“Pedidos pendientes” KPI)

El **Resumen de ventas** (`sales_summary`) calcula el KPI “Pedidos pendientes” con una consulta propia:

```sql
SELECT SUM(COALESCE(cp.SubtotalDesc, 0)) AS total_pedidos
FROM comp_ped cp
WHERE cp.Fecha >= %s AND cp.Fecha <= %s
  AND cp.TipoComprobante = 'PED'
  AND cp.Anulado = 'No'
  AND cp.Estado IN ('En preparación', 'Preparado')
```

Misma definición que el reporte (PED, no anulados, mismos estados). **Consistente**.

---

## 6. Posibles mejoras o riesgos

### 6.1 Encoding del estado “En preparación”

En VB6 aparece tanto `'En preparación'` (con **ó**) como `'En preparacion'` (sin acento) según formulario (p. ej. Stock_Control). El reporte usa `'En preparación'`.

- Si en la base hay solo `'En preparacion'`, los `IN ('En preparación', 'Preparado')` no matchearían esos registros.
- **Recomendación:** Verificar en la base qué valores tiene `comp_ped.Estado` para pedidos en preparación. Si coexisten ambas formas, incluir las dos en el `IN` o normalizar en ETL.

### 6.2 Filtros por sucursal y punto de venta

- **Remitos no facturados** y **Ventas netas** permiten filtrar por sucursal y punto de venta (`comp_ped.CodSucursal`, `comp_ped.id_pv`).
- **Pedidos pendientes** no aplica estos filtros.

Si se requiere el mismo criterio (p. ej. por PV o sucursal), habría que añadir filtros opcionales sobre `comp_ped` y reutilizar la misma lógica que en remitos/ventas.

### 6.3 Detalle adicional (cliente, vendedor, sucursal, PV)

El reporte solo muestra: fecha, tipo, nro, subtotal, estado. No hay JOINs a `cliente`, `viajantes`, `sucursales`, `punto_venta`.

Para alinearse con remitos (que sí muestran sucursal y PV), se podría extender la query con:

- `LEFT JOIN cliente ON cliente.Codigo = cp.Codigo`
- `LEFT JOIN viajantes ON viajantes.CodViajante = cp.CodViajante`
- `LEFT JOIN sucursales ON sucursales.id_sucursal = cp.CodSucursal`
- `LEFT JOIN punto_venta ON punto_venta.id_punto_venta = cp.id_pv`

y exponer cliente, vendedor, sucursal, PV en columnas o filtros.

### 6.4 Renglones (stockp)

El reporte trabaja solo con **cabecera** (`comp_ped`). No usa `stockp`. Para un “listado de pedidos pendientes de preparación” a nivel cabecera, eso es coherente con la definición actual. Si más adelante se pidiera detalle por ítem (renglones), habría que usar `stockp` + `comp_ped` como en el informe BO.

---

## 7. Resumen de validación

| Aspecto | Estado |
|--------|--------|
| Tabla `comp_ped` | Correcto. |
| `TipoComprobante = 'PED'` | Correcto. |
| `Anulado = 'No'` | Correcto. |
| `Estado IN ('En preparación', 'Preparado')` | Correcto respecto a VB6; revisar encoding en DB. |
| Filtro por `Fecha` | Correcto. |
| Uso de `SubtotalDesc` | Correcto; validar que exista y se llene en `comp_ped` para PED. |
| Consistencia con Sales summary | Correcta. |
| Filtros sucursal/PV | No implementados; mejora posible. |
| Detalle cliente/vendedor/sucursal/PV | No implementado; mejora posible. |

En conjunto, **las consultas y datos del reporte Pedidos pendientes están bien alineados con el contexto VB6**. Las principales acciones sugeridas son: **(1) comprobar en base los valores reales de `Estado`** (y eventualmente `SubtotalDesc`), y **(2) valorar** añadir filtros sucursal/PV y columnas extra (cliente, vendedor, etc.) si se buscan paridad con otros reportes.
