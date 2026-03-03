# SQL de vistas / consultas: reportes VB6 y reporte BO

**Fecha:** 2026-03-02  
**Objetivo:** Recopilar el SQL equivalente de los informes VB6 que alimentan BBDDCALCULOCONSTOCK (Pedidos por cliente general id 208, Lista de existencias valorizado id 27) y el SQL real del reporte BO bo-stock-facturacion.

**Nota:** Los reportes VB6 usan **Crystal Reports** (.rpt); la consulta está definida dentro del .rpt (tablas, enlaces, fórmulas). El VB6 solo aplica `RecordSelectionFormula`. No existen vistas MySQL creadas para esos reportes. Aquí se documenta el **SQL equivalente** reconstruido a partir de la documentación (filtros, tablas) para poder comparar con el BO. El SQL del reporte BO está extraído de `reports/services/query_runner.py` → `_run_backorder_vs_stock_vs_facturacion`.

---

## 1. Reporte VB6 – Pedidos por cliente general (id 208)

**Archivo Crystal:** `ventas_pedidos_cliente_todos.rpt`  
**Formulario:** Info_Venta.frm (bloque `reporte.BoundText = 208`).  
**Filtros aplicados en VB6 (RecordSelectionFormula):** comp_ped.Anulado = 'No', comp_ped.Fecha en [Desde, Hasta], comp_ped.TipoComprobante = 'PED', comp_ped.CodigoMovimiento <> 0, comp_ped.CodSucursal <> 0 (todas las sucursales). Sin filtro por id_pv ni por cliente ni por estado.

### 1.1 SQL equivalente (consulta base)

```sql
-- Pedidos por cliente general (id 208) – equivalente a ventas_pedidos_cliente_todos.rpt
-- Parámetros: @fecha_desde, @fecha_hasta (ej. 2026-01-01 a hoy)

SELECT
    cp.Fecha,
    cp.NroComprobante,
    cp.CodigoMovimiento,
    cp.Codigo AS id_cliente,
    cl.nombre_cliente AS cliente,
    cp.CodSucursal,
    cp.id_pv,
    cp.Estado,
    spr.IDArt,
    a.id_manual AS cod_manual,
    COALESCE(spr.Descripcion, a.NombreArticulo) AS descripcion,
    spr.Cantidad,
    COALESCE(spr.cantidad_pendiente, spr.Cantidad - COALESCE(spr.cantidad_entregada, 0)) AS cant_pend,
    spr.PrecioNetoxR AS precio_x_renglon,
    r.NombreRubro AS nombre_rubro,
    sr.NombreSubRubro AS nombre_sub_rubro
FROM comp_ped cp
INNER JOIN stockp spr ON spr.CodigoMovimiento = cp.CodigoMovimiento
LEFT JOIN articulo a ON a.IDArt = spr.IDArt
LEFT JOIN rubro r ON r.CodigoRubro = a.CodigoRubro
LEFT JOIN subrubro sr ON sr.IDSubRubro = a.IDSubRubro
LEFT JOIN cliente cl ON cl.Codigo = cp.Codigo
WHERE cp.Anulado = 'No'
  AND cp.TipoComprobante = 'PED'
  AND cp.CodigoMovimiento <> 0
  AND cp.CodSucursal <> 0
  AND cp.Fecha >= @fecha_desde
  AND cp.Fecha <= @fecha_hasta
ORDER BY cp.Fecha, cp.NroComprobante, spr.IDArt;
```

Los filtros por **estado** (En preparación, Preparado, Pendiente) **no** van en esta consulta VB6; se aplican en el Excel (Hoja1) con SUMAR.SI.CONJUNTO. Para segmentar por estado en SQL sería: `AND cp.Estado = 'Pendiente'` (o IN ('En preparación','Preparado','Parcial') según el criterio).

---

## 2. Reporte VB6 – Lista de existencias valorizado (id 27)

**Archivos Crystal:** `stock_listado_existencia_valorizado.rpt`, `stock_listado_existencia_valorizado_todos.rpt` (todos los depósitos), `stock_listado_existencia_valorizado_fecha.rpt` (a fecha).  
**Formulario:** Info_Stock.frm (subrutina `Listado_Existencia_Valorizado`).  
**Filtros:** articulo.tipo_art <> 'Gasto'; depósito (todos o uno); opcional saldo > 0; valorización por **parámetro lista_precio** (origen: combo ListaPrecio en Info_Stock.frm; se pasa a Crystal como `lista_precio` = ListIndex). Mapeo: 0 = Costo (PrecioCosto), 1 = Lista Oficial (PNOficial), 2 = Lista 1 (Precio1V), 3 = Lista 2 (Precio2V), 4 = Lista 3 (Precio3V), 5 = Lista 4 (Precio4V), 6 = Lista 5 (Precio5V).

### 2.1 SQL equivalente (todos los depósitos, fecha actual)

```sql
-- Lista de existencias valorizado (id 27) – equivalente a stock_listado_existencia_valorizado_todos.rpt
-- Parámetros: @lista_precio (0=Costo, 1=PNOficial, 2-6=Precio1V..Precio5V; mismo criterio que Info_Stock), opcional @id_deposito (NULL = todos)
-- Valorización: saldo * precio según lista. En aplicación (ej. Python) sustituir @lista_precio por el literal (0-6), ej. CASE 2 WHEN 0 THEN ...

SELECT
    a.IDArt AS id_articulo,
    a.id_manual AS cod_manual,
    a.NombreArticulo AS articulo,
    r.NombreRubro AS rubro,
    sr.NombreSubRubro AS subrubro,
    COALESCE(sd.saldo, 0) AS saldo,
    COALESCE(CASE @lista_precio WHEN 0 THEN a.PrecioCosto WHEN 1 THEN a.PNOficial WHEN 2 THEN a.Precio1V WHEN 3 THEN a.Precio2V WHEN 4 THEN a.Precio3V WHEN 5 THEN a.Precio4V WHEN 6 THEN a.Precio5V ELSE a.Precio1V END, 0) AS precio_lista,
    (COALESCE(sd.saldo, 0) * COALESCE(CASE @lista_precio WHEN 0 THEN a.PrecioCosto WHEN 1 THEN a.PNOficial WHEN 2 THEN a.Precio1V WHEN 3 THEN a.Precio2V WHEN 4 THEN a.Precio3V WHEN 5 THEN a.Precio4V WHEN 6 THEN a.Precio5V ELSE a.Precio1V END, 0)) AS saldo_valorizado,
    d.CodDeposito,
    d.NombreDeposito
FROM articulo a
INNER JOIN stock_deposito sd ON sd.id_articulo = a.IDArt
LEFT JOIN deposito d ON d.CodDeposito = sd.id_deposito AND (d.anulado IS NULL OR d.anulado = 'No')
LEFT JOIN rubro r ON r.CodigoRubro = a.CodigoRubro
LEFT JOIN subrubro sr ON sr.IDSubRubro = a.IDSubRubro
WHERE a.tipo_art <> 'Gasto'
  AND (sd.id_deposito <> 0 OR 1=1)   -- todos los depósitos
  -- AND (sd.saldo > 0)                -- opcional: solo con saldo
  -- AND sd.id_deposito = @id_deposito -- si depósito seleccionado
ORDER BY a.id_manual, d.CodDeposito;
```

### 2.2 SQL con múltiples depósitos

Para filtrar por **varios depósitos** (lista de `id_deposito`), usar `sd.id_deposito IN (...)`. Si la lista está vacía o es NULL, se puede interpretar como “todos los depósitos” (no aplicar el filtro).

**Detalle (una fila por artículo y depósito):**

```sql
-- Lista de existencias valorizado (id 27) – múltiples depósitos
-- Parámetros: @lista_precio (0-6), @ids_deposito = lista de CodDeposito (ej. 1, 2, 5). Si vacío/NULL = todos.
-- Valorización: saldo * precio según lista (CASE @lista_precio WHEN 0 THEN PrecioCosto ... WHEN 6 THEN Precio5V ELSE Precio1V END)

SELECT
    a.IDArt AS id_articulo,
    a.id_manual AS cod_manual,
    a.NombreArticulo AS articulo,
    r.NombreRubro AS rubro,
    sr.NombreSubRubro AS subrubro,
    COALESCE(sd.saldo, 0) AS saldo,
    COALESCE(CASE @lista_precio WHEN 0 THEN a.PrecioCosto WHEN 1 THEN a.PNOficial WHEN 2 THEN a.Precio1V WHEN 3 THEN a.Precio2V WHEN 4 THEN a.Precio3V WHEN 5 THEN a.Precio4V WHEN 6 THEN a.Precio5V ELSE a.Precio1V END, 0) AS precio_lista,
    (COALESCE(sd.saldo, 0) * COALESCE(CASE @lista_precio WHEN 0 THEN a.PrecioCosto WHEN 1 THEN a.PNOficial WHEN 2 THEN a.Precio1V WHEN 3 THEN a.Precio2V WHEN 4 THEN a.Precio3V WHEN 5 THEN a.Precio4V WHEN 6 THEN a.Precio5V ELSE a.Precio1V END, 0)) AS saldo_valorizado,
    d.CodDeposito,
    d.NombreDeposito
FROM articulo a
INNER JOIN stock_deposito sd ON sd.id_articulo = a.IDArt
LEFT JOIN deposito d ON d.CodDeposito = sd.id_deposito AND (d.anulado IS NULL OR d.anulado = 'No')
LEFT JOIN rubro r ON r.CodigoRubro = a.CodigoRubro
LEFT JOIN subrubro sr ON sr.IDSubRubro = a.IDSubRubro
WHERE a.tipo_art <> 'Gasto'
  AND sd.id_deposito IN (1, 2, 5)   -- reemplazar por la lista de depósitos seleccionados
  -- AND (sd.saldo > 0)              -- opcional: solo con saldo
ORDER BY a.id_manual, d.CodDeposito;
```

**Agregado por artículo (suma solo de los depósitos seleccionados):**

```sql
-- Lista existencias valorizado – múltiples depósitos, agregado por artículo
-- Parámetros: @lista_precio (0-6), @ids_deposito = lista de CodDeposito (ej. 1, 2, 5)

SELECT
    a.IDArt AS id_articulo,
    a.id_manual AS cod_manual,
    a.NombreArticulo AS articulo,
    r.NombreRubro AS rubro,
    sr.NombreSubRubro AS subrubro,
    SUM(COALESCE(sd.saldo, 0)) AS saldo,
    COALESCE(MAX(CASE @lista_precio WHEN 0 THEN a.PrecioCosto WHEN 1 THEN a.PNOficial WHEN 2 THEN a.Precio1V WHEN 3 THEN a.Precio2V WHEN 4 THEN a.Precio3V WHEN 5 THEN a.Precio4V WHEN 6 THEN a.Precio5V ELSE a.Precio1V END), 0) AS precio_lista,
    SUM(COALESCE(sd.saldo, 0)) * COALESCE(MAX(CASE @lista_precio WHEN 0 THEN a.PrecioCosto WHEN 1 THEN a.PNOficial WHEN 2 THEN a.Precio1V WHEN 3 THEN a.Precio2V WHEN 4 THEN a.Precio3V WHEN 5 THEN a.Precio4V WHEN 6 THEN a.Precio5V ELSE a.Precio1V END), 0) AS saldo_valorizado
FROM articulo a
INNER JOIN stock_deposito sd ON sd.id_articulo = a.IDArt
LEFT JOIN rubro r ON r.CodigoRubro = a.CodigoRubro
LEFT JOIN subrubro sr ON sr.IDSubRubro = a.IDSubRubro
WHERE a.tipo_art <> 'Gasto'
  AND sd.id_deposito IN (1, 2, 5)   -- reemplazar por la lista de depósitos seleccionados
GROUP BY a.IDArt, a.id_manual, a.NombreArticulo, r.NombreRubro, sr.NombreSubRubro
ORDER BY a.id_manual;
```

En aplicación (ej. Python/BO): construir la cláusula dinámicamente, por ejemplo `AND sd.id_deposito IN ({placeholders})` con tantos `%s` como depósitos, y pasar la lista como parámetros; si la lista está vacía, omitir la condición para mantener “todos los depósitos”.

**Variante agregada por artículo (todos los depósitos sumados):**

```sql
-- Lista existencias valorizado – agregado por artículo (suma depósitos)
-- Parámetros: @lista_precio (0=Costo, 1=PNOficial, 2-6=Precio1V..Precio5V)

SELECT
    a.IDArt AS id_articulo,
    a.id_manual AS cod_manual,
    a.NombreArticulo AS articulo,
    r.NombreRubro AS rubro,
    sr.NombreSubRubro AS subrubro,
    SUM(COALESCE(sd.saldo, 0)) AS saldo,
    COALESCE(MAX(CASE @lista_precio WHEN 0 THEN a.PrecioCosto WHEN 1 THEN a.PNOficial WHEN 2 THEN a.Precio1V WHEN 3 THEN a.Precio2V WHEN 4 THEN a.Precio3V WHEN 5 THEN a.Precio4V WHEN 6 THEN a.Precio5V ELSE a.Precio1V END), 0) AS precio_lista,
    SUM(COALESCE(sd.saldo, 0)) * COALESCE(MAX(CASE @lista_precio WHEN 0 THEN a.PrecioCosto WHEN 1 THEN a.PNOficial WHEN 2 THEN a.Precio1V WHEN 3 THEN a.Precio2V WHEN 4 THEN a.Precio3V WHEN 5 THEN a.Precio4V WHEN 6 THEN a.Precio5V ELSE a.Precio1V END), 0) AS saldo_valorizado
FROM articulo a
INNER JOIN stock_deposito sd ON sd.id_articulo = a.IDArt
LEFT JOIN rubro r ON r.CodigoRubro = a.CodigoRubro
LEFT JOIN subrubro sr ON sr.IDSubRubro = a.IDSubRubro
WHERE a.tipo_art <> 'Gasto'
GROUP BY a.IDArt, a.id_manual, a.NombreArticulo, r.NombreRubro, sr.NombreSubRubro
ORDER BY a.id_manual;
```

La definición exacta de “precio según lista” en VB6: parámetro **lista_precio** pasado desde Info_Stock (ListaPrecio.ListIndex). En el .rpt Crystal se usa para elegir la columna de artículo (PrecioCosto, PNOficial, Precio1V..Precio5V). En BO se usa el mismo mapeo 0–6 desde el filtro del dashboard.

---

## 3. Reporte BO – bo-stock-facturacion

**Origen:** `reports/services/query_runner.py`, método `_run_backorder_vs_stock_vs_facturacion`.  
**Filtros desde payload:** fecha_inicio, fecha_fin, base_empresa, sucursales, punto_venta, **depositos_incluidos** (opcional: solo se suman al stock estos depósitos; si vacío, todos), clientes_excluidos, **lista_precio** (0–6: Costo, Lista Oficial, Lista 1–5; mismo mapeo que VB6 Info_Stock; por defecto 2 = Lista 1).  
**Filtro fijo (alineado con VB6):** artículos con `articulo.tipo_art = 'Gasto'` se excluyen del detalle BO y del detalle por renglón.  
**Reservado:** solo estados **En preparación** y **Preparado** (sin Parcial), alineado con Excel Hoja1.  
**Valorización:** costo = articulo.PrecioCosto; saldo_valorizado = stock_actual × precio según lista_precio (CASE 0→PrecioCosto, 1→PNOficial, 2→Precio1V, …, 6→Precio5V).  
**Filtro por fecha en backorder:** las consultas que filtran por `stockp.Fecha` (sp.Fecha, spr.Fecha) reciben fechas en formato **YYYYMMDD** (ej. `'20260101'`, `'20260302'`). En bases AdministraNET donde `stockp.Fecha` es INT (YYYYMMDD), enviar `'YYYY-MM-DD'` hace que MySQL convierta a 2026 y el rango incluya todo el año; usar YYYYMMDD alinea el bo_importe con VB6.

### 3.1 Facturación (total)

```sql
-- Facturación neta (ventas - notas de crédito)
-- where_fact: Fecha >= %s, Fecha <= %s, Anulado = 'No', TipoComprobante IN ('FA','FB','FC','FE','FM','NCA','NCB','NCC','NCE','NCM')
-- + opcional: Codigo NOT IN (clientes_excluidos)

SELECT
    SUM(CASE WHEN TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM') THEN COALESCE(SubtotalDesc, 0) ELSE 0 END) AS ventas,
    SUM(CASE WHEN TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM') THEN COALESCE(SubtotalDesc, 0) ELSE 0 END) AS notas_credito
FROM cuentacliente
WHERE Fecha >= %s AND Fecha <= %s
  AND Anulado = 'No'
  AND TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM', 'NCA', 'NCB', 'NCC', 'NCE', 'NCM');
```

### 3.2 Facturación por cliente

```sql
SELECT
    cl.Codigo AS id_cliente,
    CONCAT(COALESCE(MAX(cl.nombre_cliente), ''), ' (Cod: ', cl.Codigo, ')') AS cliente,
    SUM(CASE WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM') THEN COALESCE(cc.SubtotalDesc, 0) ELSE 0 END)
      - SUM(CASE WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM') THEN COALESCE(cc.SubtotalDesc, 0) ELSE 0 END) AS sub_total,
    MAX(cc.Fecha) AS ultima_compra,
    COALESCE(MAX(v.Nombre), '') AS vendedor,
    COALESCE(MAX(z.nombre_zona), '') AS zona,
    COALESCE(MAX(cl.telefono), '') AS telefono,
    COALESCE(MAX(cl.Email), '') AS email,
    COALESCE(MAX(cl.CUIT), '') AS cuit
FROM cuentacliente cc
INNER JOIN cliente cl ON cl.Codigo = cc.Codigo
LEFT JOIN viajantes v ON v.CodViajante = cl.CodViajante
LEFT JOIN erp_zona z ON z.id_zona = cl.id_zona AND (z.anulado IS NULL OR z.anulado = 'No')
WHERE cc.Fecha >= %s AND cc.Fecha <= %s
  AND cc.Anulado = 'No'
  AND cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM', 'NCA', 'NCB', 'NCC', 'NCE', 'NCM')
GROUP BY cl.Codigo
ORDER BY sub_total DESC
LIMIT 1000;
```

### 3.3 Remitos no facturados (total y detalle)

```sql
-- Total remitos
SELECT SUM(COALESCE(cp.SubtotalDesc, 0)) AS total_remitos
FROM comp_ped cp
WHERE cp.Fecha >= %s AND cp.Fecha <= %s
  AND cp.TipoComprobante = 'REM'
  AND cp.Anulado = 'No'
  AND cp.Estado = 'Pendiente';

-- Detalle remitos
SELECT
    DATE_FORMAT(cp.Fecha, '%d/%m/%Y') AS fecha,
    cp.NroComprobante AS nro_comprobante,
    cp.CodSucursal AS id_sucursal,
    COALESCE(s.nombre_sucursal, 'Sin Sucursal') AS sucursal,
    cp.id_pv AS id_punto_venta,
    COALESCE(CAST(pv.nro_punto_venta AS CHAR), CAST(cp.id_pv AS CHAR), 'Sin PV') AS punto_venta,
    COALESCE(cp.SubtotalDesc, 0) AS subtotal_desc
FROM comp_ped cp
LEFT JOIN sucursales s ON s.id_sucursal = cp.CodSucursal
LEFT JOIN punto_venta pv ON pv.id_punto_venta = cp.id_pv
WHERE cp.Fecha >= %s AND cp.Fecha <= %s
  AND cp.TipoComprobante = 'REM'
  AND cp.Anulado = 'No'
  AND cp.Estado = 'Pendiente'
ORDER BY cp.Fecha DESC, cp.NroComprobante ASC;
```

### 3.4 Backorder detalle (por artículo, con stock, reservado, disponible, OC pendiente, costo, saldo_valorizado)

```sql
-- sd_where_excl: vacío o " WHERE id_deposito IN (...)" si depositos_incluidos (solo esos depósitos suman al stock)
-- reservado_excl_clause: vacío o " AND cp_res.Codigo NOT IN (...)" si clientes_excluidos
-- clientes_excl_bo: vacío o " AND cp.Codigo NOT IN (...)" si clientes_excluidos
-- bo_estados = "('Pendiente')"
-- lista_precio: 0-6 desde payload (default 2). precio_segun_lista_sql = CASE N WHEN 0 THEN a.PrecioCosto WHEN 1 THEN a.PNOficial WHEN 2 THEN a.Precio1V ... WHEN 6 THEN a.Precio5V ELSE a.Precio1V END

SELECT
    sp.IDArt AS id_art,
    a.id_manual AS codigo,
    a.NombreArticulo AS articulo,
    COALESCE(r.NombreRubro, 'Sin Rubro') AS categoria,
    SUM(sp.Cantidad) AS bo_qty,
    SUM(sp.PrecioNetoxR) AS bo_importe,
    COALESCE(sd.stock_total, 0) AS stock_actual,
    COALESCE(reservado_sub.reservado, 0) AS stock_reservado,
    GREATEST(0, COALESCE(sd.stock_total, 0) - COALESCE(reservado_sub.reservado, 0)) AS disponible,
    GREATEST(0, COALESCE(oc_pendiente_sub.oc_pendiente, 0)) AS oc_pendiente,
    COALESCE(MAX(a.PrecioCosto), 0) AS costo,
    (COALESCE(sd.stock_total, 0) * COALESCE(MAX(CASE 2 WHEN 0 THEN a.PrecioCosto WHEN 1 THEN a.PNOficial WHEN 2 THEN a.Precio1V WHEN 3 THEN a.Precio2V WHEN 4 THEN a.Precio3V WHEN 5 THEN a.Precio4V WHEN 6 THEN a.Precio5V ELSE a.Precio1V END), 0)) AS saldo_valorizado
FROM stockp sp
INNER JOIN comp_ped cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
LEFT JOIN articulo a ON a.IDArt = sp.IDArt
LEFT JOIN rubro r ON r.CodigoRubro = a.CodigoRubro
LEFT JOIN (
    SELECT id_articulo, SUM(saldo) AS stock_total
    FROM stock_deposito
    -- + sd_where_excl
    GROUP BY id_articulo
) sd ON sd.id_articulo = sp.IDArt
LEFT JOIN (
    SELECT sp_oc.IDArt AS id_articulo,
           SUM(COALESCE(sp_oc.cantidad_pendiente, sp_oc.Cantidad - COALESCE(sp_oc.cantidad_entregada, 0))) AS oc_pendiente
    FROM stockp sp_oc
    INNER JOIN cuentaproveedor cp_oc ON cp_oc.CodigoMovimiento = sp_oc.CodigoMovimiento
    WHERE cp_oc.TipoComprobante = 'OC'
      AND (sp_oc.Comprobante = 'OC' OR sp_oc.Comprobante IS NULL)
      AND cp_oc.Estado = 'Pendiente'
      AND cp_oc.Anulado = 'No'
      AND (sp_oc.anulado IS NULL OR sp_oc.anulado = 'No')
      AND (COALESCE(sp_oc.cantidad_pendiente, sp_oc.Cantidad - COALESCE(sp_oc.cantidad_entregada, 0)) > 0)
    GROUP BY sp_oc.IDArt
) oc_pendiente_sub ON oc_pendiente_sub.id_articulo = sp.IDArt
LEFT JOIN (
    SELECT sp_res.IDArt AS id_articulo,
           SUM(COALESCE(sp_res.cantidad_pendiente, sp_res.Cantidad - COALESCE(sp_res.cantidad_entregada, 0))) AS reservado
    FROM stockp sp_res
    INNER JOIN comp_ped cp_res ON cp_res.CodigoMovimiento = sp_res.CodigoMovimiento
    WHERE cp_res.TipoComprobante = 'PED'
      AND (sp_res.Comprobante = 'PED' OR sp_res.Comprobante IS NULL)
      AND cp_res.Anulado = 'No'
      AND (sp_res.anulado IS NULL OR sp_res.anulado = 'No')
      AND cp_res.Estado IN ('En preparación', 'Preparado')
      AND (COALESCE(sp_res.cantidad_pendiente, sp_res.Cantidad - COALESCE(sp_res.cantidad_entregada, 0)) > 0)
    -- + reservado_excl_clause
    GROUP BY sp_res.IDArt
) reservado_sub ON reservado_sub.id_articulo = sp.IDArt
WHERE cp.TipoComprobante = 'PED'
  AND (sp.Comprobante = 'PED' OR sp.Comprobante IS NULL)
  AND cp.Anulado = 'No'
  AND (sp.anulado IS NULL OR sp.anulado = 'No')
  AND cp.Estado IN ('Pendiente')
  AND sp.CodigoMovimiento IS NOT NULL
  AND sp.Fecha >= %s AND sp.Fecha <= %s
-- + clientes_excl_bo
  AND (a.IDArt IS NULL OR a.tipo_art IS NULL OR a.tipo_art <> 'Gasto')
GROUP BY sp.IDArt, a.id_manual, a.NombreArticulo, r.NombreRubro, sd.stock_total, oc_pendiente_sub.oc_pendiente, reservado_sub.reservado
HAVING bo_qty > 0
ORDER BY bo_importe DESC;
```

En el código real el primer argumento del CASE es el **literal** del parámetro lista_precio (0–6), no un nombre de columna (p. ej. `CASE 2 WHEN 0 THEN ...` para Lista 1).

### 3.5 Backorder detalle row-level (un renglón por fila stockp)

```sql
-- where_bo_rows: cp.TipoComprobante='PED', (spr.Comprobante='PED' OR spr.Comprobante IS NULL),
--   cp.Anulado='No', (spr.anulado IS NULL OR spr.anulado='No'), cp.Estado IN ('Pendiente'),
--   spr.CodigoMovimiento IS NOT NULL, spr.Fecha >= %s AND spr.Fecha <= %s,
--   (a.IDArt IS NULL OR a.tipo_art IS NULL OR a.tipo_art <> 'Gasto')
--   + opcional cp.Codigo NOT IN (clientes_excluidos)

SELECT
    DATE_FORMAT(cp.Fecha, '%d/%m/%y') AS fecha,
    cp.NroComprobante AS nro_comp,
    COALESCE(spr.Descripcion, a.NombreArticulo, '') AS descripcion,
    COALESCE(a.id_manual, spr.id_manual, '') AS cod_manual,
    spr.Cantidad AS cantidad,
    COALESCE(spr.cantidad_pendiente, 0) AS cant_pend,
    cp.Estado AS estado,
    COALESCE(cli.nombre_cliente, '') AS cliente,
    cp.Codigo AS id_cliente,
    COALESCE(spr.PrecioNetoxR, 0) AS precio_x_renglon,
    COALESCE(r.NombreRubro, '') AS nombre_rubro,
    COALESCE(sr.NombreSubRubro, '') AS nombre_sub_rubro,
    COALESCE(v.Nombre, '') AS nombre_vendedor
FROM comp_ped cp
INNER JOIN stockp spr ON spr.CodigoMovimiento = cp.CodigoMovimiento
LEFT JOIN articulo a ON a.IDArt = spr.IDArt
LEFT JOIN rubro r ON r.CodigoRubro = a.CodigoRubro
LEFT JOIN subrubro sr ON sr.IDSubRubro = a.IDSubRubro
LEFT JOIN cliente cli ON cli.Codigo = cp.Codigo
LEFT JOIN viajantes v ON v.CodViajante = cp.CodViajante
WHERE cp.TipoComprobante = 'PED'
  AND (spr.Comprobante = 'PED' OR spr.Comprobante IS NULL)
  AND cp.Anulado = 'No'
  AND (spr.anulado IS NULL OR spr.anulado = 'No')
  AND cp.Estado IN ('Pendiente')
  AND spr.CodigoMovimiento IS NOT NULL
  AND spr.Fecha >= %s AND spr.Fecha <= %s
  AND (a.IDArt IS NULL OR a.tipo_art IS NULL OR a.tipo_art <> 'Gasto')
ORDER BY cp.Fecha DESC, cp.NroComprobante ASC, COALESCE(spr.Descripcion, a.NombreArticulo, '') ASC;
```

### 3.6 Detalle OC pendiente (tooltip)

```sql
-- ids_oc = lista de id_art con oc_pendiente > 0

SELECT
    sp.IDArt,
    cp.Fecha,
    COALESCE(cp.NroCompBusq, '') AS nro_comp_busq,
    COALESCE(cp.NroComprobante, '') AS nro_comprobante,
    cp.Vencimiento,
    COALESCE(prov.Nombre, '') AS proveedor,
    COALESCE(sp.cantidad_pendiente, sp.Cantidad - COALESCE(sp.cantidad_entregada, 0)) AS qty_pend
FROM stockp sp
INNER JOIN cuentaproveedor cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
LEFT JOIN proveedor prov ON prov.Codigo = cp.Codigo
WHERE cp.TipoComprobante = 'OC' AND (sp.Comprobante = 'OC' OR sp.Comprobante IS NULL)
  AND cp.Estado = 'Pendiente' AND cp.Anulado = 'No'
  AND (sp.anulado IS NULL OR sp.anulado = 'No')
  AND sp.IDArt IN (%s)  -- placeholders para ids_oc
  AND (COALESCE(sp.cantidad_pendiente, sp.Cantidad - COALESCE(sp.cantidad_entregada, 0)) > 0)
ORDER BY sp.IDArt, cp.Fecha, cp.NroCompBusq;
```

### 3.7 Detalle reservado (tooltip)

Reservado = PED en estado **En preparación** o **Preparado** (sin Parcial).

```sql
SELECT
    sp_res.IDArt,
    cp_res.Fecha,
    COALESCE(NULLIF(TRIM(cp_res.NroComprobante), ''), cp_res.NroCompBusq, '') AS nro_comprobante,
    COALESCE(NULLIF(TRIM(cli.nombre_cliente), ''), '—') AS cliente,
    COALESCE(NULLIF(TRIM(cp_res.Estado), ''), '—') AS estado,
    COALESCE(sp_res.cantidad_pendiente, sp_res.Cantidad - COALESCE(sp_res.cantidad_entregada, 0)) AS cantidad
FROM stockp sp_res
INNER JOIN comp_ped cp_res ON cp_res.CodigoMovimiento = sp_res.CodigoMovimiento
LEFT JOIN cliente cli ON cli.Codigo = cp_res.Codigo
WHERE cp_res.TipoComprobante = 'PED'
  AND (sp_res.Comprobante = 'PED' OR sp_res.Comprobante IS NULL)
  AND cp_res.Anulado = 'No'
  AND (sp_res.anulado IS NULL OR sp_res.anulado = 'No')
  AND cp_res.Estado IN ('En preparación', 'Preparado')
  AND sp_res.CodigoMovimiento IS NOT NULL
  AND (COALESCE(sp_res.cantidad_pendiente, sp_res.Cantidad - COALESCE(sp_res.cantidad_entregada, 0)) > 0)
ORDER BY sp_res.IDArt, cp_res.Fecha, cp_res.NroComprobante;
```

### 3.8 Stock por depósito (tooltip)

```sql
-- Lista de depósitos (solo los incluidos si depositos_incluidos no vacío; si vacío, todos)
SELECT d.CodDeposito, COALESCE(NULLIF(TRIM(d.NombreDeposito), ''), 'Sin nombre') AS nombre_deposito
FROM deposito d
WHERE (d.anulado IS NULL OR d.anulado = 'No')
ORDER BY d.CodDeposito;

-- Saldo por artículo y depósito (ids_art = artículos del backorder_detalle)
SELECT sd.id_articulo, sd.id_deposito, COALESCE(sd.saldo, 0)
FROM stock_deposito sd
WHERE sd.id_articulo IN (%s);  -- placeholders para ids_art
-- + AND sd.id_deposito IN (...) si depositos_incluidos (solo esos depósitos)
```

### 3.9 Consistencia bo_importe vs Precio x renglón (investigación)

**Problema observado:** Para un mismo artículo (ej. id_art 5753, codigo 391586), la consulta agregada (3.4) devolvía `bo_importe` ≈ 22.336.360 mientras en la pestaña Backorder (renglón a renglón) se mostraba "Precio x renglón" ≈ 32.727.258 en una fila.

**Causa identificada y validada:** En bases donde `stockp.Fecha` es **INT** (formato YYYYMMDD), si las fechas se enviaban en formato `'YYYY-MM-DD'` (ej. `'2026-01-01'`), MySQL las convertía a entero y el rango quedaba ampliado (todo el año 2026). Si **solo una** de las dos consultas (agregada vs row-level) recibía ese formato y la otra YYYYMMDD, los conjuntos de filas diferían: el agregado podía devolver `bo_importe` ≈ 22,3M (período correcto) y los renglones incluir más filas del año → suma ≈ 32,7M. La **solución** es que ambas usen exactamente el mismo filtro de fecha en **YYYYMMDD** (`fecha_inicio_bo`, `fecha_fin_bo`). Los tests en `TestCausaInconsistenciaValidada` reproducen el escenario: mismo filtro → sin inconsistencia; filtro distinto (agregado 22,3M, renglones 32,7M) → 1 inconsistencia detectada.

**Invariante:** Para cada artículo (codigo), la suma de `precio_x_renglon` sobre `backorder_detalle_rows` (filas con ese `cod_manual`) debe ser igual al `bo_importe` de ese artículo en `backorder_detalle`.

**Comprobación en runtime:** En `query_runner._run_backorder_vs_stock_vs_facturacion`, tras construir `backorder_detalle` y `backorder_detalle_rows`, se ejecuta una comprobación: por cada artículo se suma `precio_x_renglon` de las filas con ese `cod_manual` y se compara con `bo_importe` (tolerancia 0,01). Si difieren, se registra un **warning** en log: `[BO] Inconsistencia agregado vs renglones: codigo=... bo_importe=... sum(precio_x_renglon)=...`. Eso indica que conviene revisar que ambas consultas usen el mismo filtro de fecha (YYYYMMDD) y los mismos estados/ exclusiones.

**Tests:** Tests unitarios en `reports/tests/test_bo_report_consistency.py` cubren: (1) conversión de fechas a YYYYMMDD (`parse_fecha_bo_yyyymmdd`), (2) consistencia agregado vs renglones (`check_bo_agregado_vs_renglones_consistency`), (3) que el prorrateo con_stock/con_ingreso/sin_stock suma bo_importe, (4) que la columna precio_x_renglon en el SELECT row-level es el índice 9. Ejecutar: `docker exec Synap_app python manage.py test reports.tests.test_bo_report_consistency`. Para validar contra datos reales, ejecutar el reporte BO y revisar logs por el warning de consistencia.

### 3.10 Uso de bo_importe y precio_x_renglon en el reporte (sin transformar el dato de la DB)

Si las consultas a la DB son correctas y aun así se ve un valor distinto en pantalla (ej. 32,7M en “Precio x renglón”), los únicos usos y “cálculos” en el reporte son los siguientes. **Ninguno reemplaza ni recalcula bo_importe o precio_x_renglon a partir de otro campo.**

**Backend (`query_runner.py`):**

| Dato | Origen | Cálculo / uso |
|------|--------|----------------|
| `bo_importe` | `row[5]` del SELECT agregado (3.4), es decir `SUM(sp.PrecioNetoxR)` | Se envía tal cual. Se usa solo para **prorratear** por cantidad y obtener `con_stock_importe`, `con_ingreso_importe`, `sin_stock_importe` (proporción de bo_importe según con_stock_qty/bo_qty, etc.). Esos tres se envían además de `bo_importe`, no en lugar de él. |
| `precio_x_renglon` | `r[9]` del SELECT row-level (3.5), es decir `COALESCE(spr.PrecioNetoxR, 0)` | Se convierte a `float` y se envía tal cual. No hay ningún cálculo que lo modifique. |

**Frontend (`bo_stock_facturacion.js`):**

| Dónde se muestra | Campo usado | Transformación |
|------------------|-------------|----------------|
| Pestañas “Detalle con stock”, “Con ingreso”, “Sin stock” (tabla por **artículo**) | `r.bo_importe` | Solo `formatCurrency(r.bo_importe)` (formato es-AR, sin cambiar el número). |
| Pestaña “Backorder” (tabla por **renglón**) | `row.precio_x_renglon` | Solo `formatCurrency(row.precio_x_renglon)`. Cada fila es un elemento de `backorder_detalle_rows`; no se mezcla con `backorder_detalle` ni con `bo_importe`. |
| Pestaña “Backorder” **con “Agrupar por”** activo | Para filas de **detalle**: `row.precio_x_renglon`. Para filas de **grupo**: `g.totals['precio_x_renglon']` | En grupos, el total es la **suma** de `precio_x_renglon` de todos los renglones del grupo (ej. si se agrupa por Rubro, el total del rubro “LOREAL PRESTIGE” es la suma de todos los renglones de ese rubro). Un valor como 32,7M en una **fila de grupo** podría ser esa suma (varios artículos/renglones), no el importe de un solo renglón. |

**Conclusión:** El reporte no hace ningún cálculo que “transforme” el valor de la DB para la columna “Precio x renglón”: se pinta `precio_x_renglon` de cada renglón (o la suma del grupo si hay agrupación). Si se ve 32,7M donde la DB solo tiene renglones de ~21M y ~1M para ese artículo, hay que comprobar: (1) que no se esté mirando una **fila de grupo** (total de un rubro/cliente/etc.), y (2) que el payload del reporte use las fechas en YYYYMMDD y el mismo filtro que la consulta manual (ver 3.9).

### 3.11 PrecioVentaxR vs PrecioNetoxR (origen del valor 32.727.262)

En `stockp` existen dos importes por renglón:

| Campo | Significado | Ejemplo (120 u) |
|-------|-------------|-----------------|
| **PrecioVentaxR** | Importe por renglón a **precio de venta** (antes de descuentos/IVA neto) | 120 × PrecioVentaxU (272.727,23) ≈ **32.727.268** |
| **PrecioNetoxR** | Importe por renglón a **precio neto** (el que usa el reporte BO) | 120 × PrecioNetoxU (177.272,70) ≈ **21.272.724** |

Si se ve **32.727.262,08** y al dividir por la cantidad pendiente (120) da **272.727,18** ≈ **PrecioVentaxU**, ese valor **no sale de PrecioNetoxR**: sale de **PrecioVentaxR** (o de PrecioVentaxU × Cantidad). El PrecioNetoxR correcto para ese renglón es PrecioNetoxU × Cantidad ≈ 21.272.724.

- **Reporte BO Synap:** usa solo **PrecioNetoxR** (`spr.PrecioNetoxR` → `precio_x_renglon`). Si en la base ese renglón tuviera 32.727.262 en la columna PrecioNetoxR, sería un error de dato (se habría escrito el importe de venta en el campo neto).
- Cualquier pantalla o informe que muestre 32.727.262 como "Precio x renglón" para ese renglón está usando **precio de venta por renglón** (PrecioVentaxR), no precio neto (PrecioNetoxR).

---

## 4. Referencias

- Pedidos por cliente general (208): [INFORME_VB6_PEDIDOS_POR_CLIENTE_GENERAL_Y_EXCEL_BBDDCALCULOCONSTOCK.md](INFORME_VB6_PEDIDOS_POR_CLIENTE_GENERAL_Y_EXCEL_BBDDCALCULOCONSTOCK.md).
- Lista existencias valorizado (27) y comparativa BO: [COMPARATIVA_VB6_LISTA_EXISTENCIAS_VALORIZADO_VS_BO_SYNAP.md](COMPARATIVA_VB6_LISTA_EXISTENCIAS_VALORIZADO_VS_BO_SYNAP.md).
- Análisis BBDDCALCULOCONSTOCK y fórmulas Excel: [ANALISIS_BBDDCALCULOCONSTOCK_VB6_VS_BO.md](ANALISIS_BBDDCALCULOCONSTOCK_VB6_VS_BO.md).
- Código BO: [reports/services/query_runner.py](../../reports/services/query_runner.py) → `_run_backorder_vs_stock_vs_facturacion`.
- Tablas: [docs/general/tablas/](../general/tablas/).
