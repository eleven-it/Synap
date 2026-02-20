# Reporte BO vs Stock vs Facturación – Rendimiento y error 3024

## ¿Es un error de sintaxis?

**No.** El error `(3024, 'Query execution was interrupted, maximum statement execution time exceeded')` indica que MySQL **canceló la consulta por superar el tiempo máximo** (MAX_EXECUTION_TIME, 90 s). La sintaxis es correcta; el problema es **rendimiento** (tabla grande, full scan, falta de índices).

---

## Consulta que dispara el timeout

La primera consulta del reporte BO es la de **facturación** sobre `cuentacliente`:

```sql
SELECT /*+ MAX_EXECUTION_TIME(90000) */
    SUM(CASE 
        WHEN TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM') 
        THEN COALESCE(SubtotalDesc, 0)
        ELSE 0 
    END) AS ventas,
    SUM(CASE 
        WHEN TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM') 
        THEN COALESCE(SubtotalDesc, 0)
        ELSE 0 
    END) AS notas_credito
FROM cuentacliente
WHERE Fecha >= '2026-01-01'
  AND Fecha <= '2026-12-31'
  AND Anulado = 'No'
  AND TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM', 'NCA', 'NCB', 'NCC', 'NCE', 'NCM');
```

Sustituir `'2026-01-01'` y `'2026-12-31'` por el período que uses.

---

## Cómo diagnosticar con EXPLAIN

En MySQL (base `administranet89`):

1. Ejecutar la consulta anterior sustituyendo las fechas.
2. Antes, ejecutar:

   ```sql
   EXPLAIN SELECT /*+ MAX_EXECUTION_TIME(90000) */
       SUM(CASE WHEN TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM') THEN COALESCE(SubtotalDesc, 0) ELSE 0 END) AS ventas,
       SUM(CASE WHEN TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM') THEN COALESCE(SubtotalDesc, 0) ELSE 0 END) AS notas_credito
   FROM cuentacliente
   WHERE Fecha >= '2026-01-01' AND Fecha <= '2026-12-31'
     AND Anulado = 'No'
     AND TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM', 'NCA', 'NCB', 'NCC', 'NCE', 'NCM');
   ```

3. Revisar:
   - **`type`**: si es `ALL` → full table scan (lento).
   - **`key`**: si es `NULL` → no se usa índice.
   - **`rows`**: estimación de filas leídas.

---

## Índices recomendados (administranet89)

Crear al menos uno de estos índices en `cuentacliente`:

```sql
CREATE INDEX idx_cc_fecha ON cuentacliente (Fecha);
```

O uno compuesto que cubra mejor el `WHERE`:

```sql
CREATE INDEX idx_cc_fecha_tipo_anul ON cuentacliente (Fecha, TipoComprobante, Anulado);
```

Luego volver a ejecutar `EXPLAIN` y comprobar que se use el índice (`key` no nulo, `type` no `ALL`).

---

## Otras medidas

- Probar **períodos más cortos** (por ejemplo un mes o una semana).
- Usar **filtros** (sucursal, punto de venta) para reducir volumen.
- El log del backend escribe la SQL exacta (con fechas) cuando se ejecuta el reporte BO; puedes copiarla de ahí para `EXPLAIN` si lo prefieres.

---

## BO IMPORTE y CON STOCK IMPORTE

**Origen:** `bo_importe` = `SUM(stockp.PrecioVentaxR)`. No se usa fallback de precio unitario: si el importe es 0, se considera correcto (el Backorder debe traer el precio bien cargado).

---

## CON INGRESO (Backorder con ingreso)

**Definición:** Cantidades en **órdenes de compra aprobadas y pendientes de entrega**.

**Origen:** `oc_pendiente` **calculado** desde stockp+cuentaproveedor (OC Estado=Pendiente). **No** usar stock_deposito.saldo_pedido_proveedor (no fiel). **Prioridad:** (1) Stock cubre primero reservado; disponible = max(0, stock − reservado). (2) OC pend. cubre primero el faltante de reservado (max(0, reservado − stock)); solo el resto se usa para BO. (3) Clasificación BO: con stock = min(BO, disponible); con ingreso = min(resto BO, OC restante para BO); sin stock = resto.
