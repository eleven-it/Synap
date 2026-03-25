# Especificación SQL por módulo: posting legacy factura de compra

**Referencias:** [auditoria_facturas_compras_sql.md](auditoria_facturas_compras_sql.md), [auditoria_facturas_compras_tablas_campos.md](auditoria_facturas_compras_tablas_campos.md), [posting_contract.md](posting_contract.md).

**Convención:** sentencias en **SQL lógico** con placeholders `%s` / `:nombre` según implementación. No es código Python final. Los nombres de columnas deben validarse contra el DDL MySQL del cliente (*riesgo pendiente*: diferencias de mayúsculas).

**Transacción única:** todo en un `BEGIN … COMMIT` salvo nota explícita (ADR-0002).

---

## Orden global de ejecución (módulos)

| Paso | Módulo | Tablas principales |
|------|--------|-------------------|
| P0 | Preflight READ | `periodos`, `years`, `cuentaproveedor`, `proveedor`, `cond_venta` |
| P1 | Numerador | `codmov` |
| P2 | Cabecera + vales + percepciones cabecera + proveedor saldo + caja (contado) | `cuentaproveedor`, `en_vale_factura`, `en_vale_viaje`, `proveedor`, `percep_prov`, `percepcion_prov_convenio`, `caja_saldo`, `caja` |
| P3 | Detalle por línea | `stock`, `stock_deposito`, `stockp`, `lote`, `lote_stock`, `otro_egreso` |
| P4 | Lista compra (opcional) | `articulo`, `iva`, `precios_historial` |
| P5 | Crédito | `op_factura` |
| P6 | Puentes OC / Remito | `cuentaproveedor` (OC/REM), `oc_factp`, `remp_factp` |
| P7 | Artículo proveedor habitual (opcional) | `articulo` |
| P8 | Series | `serie_entrada`, `serie_movimiento` |
| P9 | Contabilidad (opcional) | `cont_ejercicio`, `cont_asiento`, `cont_ejercicio_saldo_cta`, `cont_periodo_saldo_cta`, … |
| P10 | Balanceo asiento | `cont_asiento` (UPDATE líneas) |

*Nota VB6:* el orden exacto entre sub-pasos de P2 (caja antes/después de parte de cabecera) sigue el bloque `Guardar`; aquí se mantiene el orden de [legacy_integration_spec.md](legacy_integration_spec.md) y el JSON `orden_persistencia_recomendado`.

---

## P0 — Preflight (solo lectura, puede ser misma conexión sin commit)

### P0.1 Período fiscal — fecha registro

```sql
SELECT periodos.*, years.*
FROM periodos
INNER JOIN years ON periodos.id_year = years.id_year
WHERE periodos.mes_numero_periodo = :mes_registro
  AND years.year = :anio_registro
  AND periodos.abierto_periodo = 'Si';
```

- Debe retornar ≥ 1 fila; comparar `vencimiento_fiscal_periodo` con `:fecha_servidor` (regla VB6).

### P0.2 Año comprobante

```sql
SELECT * FROM years WHERE year = :anio_comprobante;
```

### P0.3 Anti-duplicado (Validacion_Comp)

Variante con `nrocomprobante` formateado:

```sql
SELECT * FROM cuentaproveedor
WHERE nrocomprobante = :num_formateado
  AND Codigo = :codigo_proveedor
  AND Anulado = 'No'
  AND CodigoMovimiento <> 0
  AND (
    TipoComprobante = 'FA' OR TipoComprobante = 'FC' OR TipoComprobante = 'FB'
    /* + 'FM' si duplicate_check_includes_fm en command context */
  );
```

- Si `RecordCount >= 1` → error negocio `DUPLICATE_INVOICE`.

### P0.4 Proveedor y condición

```sql
SELECT codigo, saldo FROM proveedor WHERE codigo = :codigo_proveedor;
SELECT * FROM cond_venta WHERE Codigo = :id_cond_compra;
```

---

## P1 — Numerador `codmov`

```sql
SELECT CodigoMovimiento FROM codmov WHERE codigo = 1 FOR UPDATE;
```

Aplicación: `nuevo = actual + 1`

```sql
UPDATE codmov SET CodigoMovimiento = :nuevo WHERE codigo = 1;
```

- El valor `:nuevo` es `:codigo_movimiento` para todo el resto del posting.

---

## P2 — Cabecera `cuentaproveedor` y efectos inmediatos

### P2.1 Plantilla / INSERT cabecera

VB6 usa `SELECT * FROM cuentaproveedor WHERE CodigoMovimiento = 1` + `AddNew`. En SQL explícito:

```sql
INSERT INTO cuentaproveedor (
  /* columnas requeridas según DDL — listado funcional en auditoría tablas_campos §1 */
  Fecha, FechaRegistro, TipoComprobante, NroComprobante, NroCompBusq, Detalle,
  Saldo, OPMov, ImporteCompra, ImportePago, Iva1, Iva2, Iva3,
  Alicuota1, alicuota2, Alicuota3, PercepIB, PercepGan, PercepIVA, OtrosImp,
  NroCAI, FechaCAI, idUsuario, codSucursal, TipoFactura, Exento, anulado,
  Codigo, CodBanco, CodigoMovimiento, Subtotal1, Subtotal2, Subtotal3, SubtotalGral,
  ImpDesc1_1, TotalDesc, SubTotalDesc1, SubTotalDesc2, SubTotalDesc3, SubtotalDesc,
  CondCompra, id_condcompra, impuesto_interno, sobretasa_iva, Estado,
  Vencimiento, Vencido, ID_Proyecto, remite_factura_art, estado_fact_remito, CotiDolar
) VALUES (
  :fecha, :fecha_registro, :tipo_comprobante, :nro_formateado, :nro_busq, :detalle,
  :saldo, 0, :importe_compra, NULL, :iva1, :iva2, :iva3,
  :alic1, :alic2, :alic3, :percep_ib, :percep_gan, :percep_iva, :otros_imp,
  :nro_cai, :fecha_cai, :id_usuario, :cod_sucursal, :tipo_factura, :exento, 'No',
  :codigo_proveedor, 2, :codigo_movimiento, :st1, :st2, :st3, :st_gral,
  :imp_desc1_1, :total_desc, :std1, :std2, :std3, :std,
  :cond_compra_txt, :id_cond_compra, :imp_int, :sobretasa, :estado,
  :vencimiento, :vencido, :id_proyecto, :remite_fact_art, :estado_fact_remito, :coti_dolar
);
```

> **DDL:** la lista exacta de columnas NOT NULL debe generarse desde `INFORMATION_SCHEMA` del cliente; la auditoría lista campos **usados** en VB6.

### P2.2 Vales

```sql
INSERT INTO en_vale_factura (CodMovVale, CodMovFactura)
SELECT :codmov_vale, :codigo_movimiento
FROM DUAL
WHERE EXISTS (SELECT 1 FROM ... /* o una fila por vale en aplicación */);
```

*Patrón VB6:* un `INSERT…SELECT` desde temp; en Synap: **N** inserts parametrizados o un solo multi-row `INSERT` con tuplas del command.

```sql
UPDATE en_vale_viaje SET estado = 'En Factura' WHERE CodigoMovimiento = :codmov_vale;
```

(repetir por vale)

### P2.3 Percepciones IB (detalle)

Por fila de `PercepcionIBCommand`:

```sql
INSERT INTO percep_prov (id_jurisdiccion, importe_percep, codigo_movimiento, tipo_comp, id_proveedor)
VALUES (:id_jur, :importe, :codigo_movimiento, 'Factura', :id_proveedor);

INSERT INTO percepcion_prov_convenio (id_provincia, codigo_movimiento, tipo_comp, Fecha, monto_percepcion)
VALUES (:id_jur, :codigo_movimiento, :tipo_factura_letra, :fecha, :importe);
```

### P2.4 Saldo proveedor

```sql
UPDATE proveedor SET saldo = :nuevo_saldo WHERE codigo = :codigo_proveedor;
```

(`:nuevo_saldo` = mismo criterio que cabecera `Saldo` según crédito/contado — *confirmado por auditoría* §1 cabecera.)

### P2.5 Contado — `caja_saldo` y `caja`

```sql
SELECT * FROM caja_saldo WHERE id_caja = :id_caja_abm AND moneda = 'Pesos' FOR UPDATE;
UPDATE caja_saldo SET Saldo = :saldo_nuevo, id_usuario = :id_usuario WHERE id_caja = :id_caja AND moneda = 'Pesos';

INSERT INTO caja (
  Fecha, tipo_comprobante, Tipo, nro_comprobante, nro_comp_busq, ingreso, id_usuario,
  cod_vendedor, cod_sucursal, Moneda, egreso, Detalle, codigo_movimiento,
  Codigo_Cliente, codigo_prov, tipo_cp, id_caja_abm_origen, anulado, Saldo, ID_Proyecto
) VALUES (...);
```

Literales *confirmados por auditoría:* `Tipo = 'Factura Compra Contado'`, `Moneda = 'Pesos'`, `tipo_cp = 'Proveedor'`, `Codigo_Cliente = 1`, `anulado = 'No'`.

---

## P3 — Detalle: por cada `StockLineCommand`

### P3.1 `stock` — INSERT

Un único `INSERT` por línea con columnas según [Anexo A](auditoria_facturas_compras_tablas_campos.md). Campos fijos:

- `TipoComp = 'Compra'`
- `CodigoMovimiento = :codigo_movimiento`
- `CodigoCP = :codigo_proveedor`
- `Tipo = 'Proveedor'`
- `anulado = 'No'`
- `Comprobante` = letra FA/FB/FC/FM según reglas VB6

### P3.2 `stock_deposito`

```sql
SELECT * FROM stock_deposito
WHERE id_articulo = :id_art AND id_deposito = :id_dep FOR UPDATE;
UPDATE stock_deposito SET Saldo = :saldo_nuevo WHERE ...;
```

- Lógica cantidad: embalaje / bulto / display según flags contexto (*auditoría* ~4242–4255).
- Si OC estadístico `saldo_pedido_proveedor` (*auditoría* ~4214–4226): `UPDATE` adicional mismo registro.

### P3.3 `otro_egreso` (si `cod_gasto <> 0`)

```sql
INSERT INTO otro_egreso (
  fecha_oe, nombre_oe, codigo_movimiento_op, tipo_oe, importe_oe, detalle_oe, id_gasto, tipo_comp
) VALUES (
  :fecha, :nombre, :codigo_movimiento, 'Otros Egresos', :importe, :detalle, :id_gasto, 'FACT Gasto'
);
```

`:importe` = `PrecioBrutoxR + total_otros_impuestos_oe` (proporción por cantidad de líneas en VB6).

### P3.4 Lotes

**Existente:**

```sql
SELECT * FROM lote WHERE cod_lote = :cod_lote AND id_articulo = :id_art AND anulado = 'No' FOR UPDATE;
UPDATE lote SET stock_total_lote = stock_total_lote + :delta WHERE id_lote = :id_lote;

SELECT * FROM lote_stock WHERE id_lote = :id_lote AND id_deposito = :id_dep FOR UPDATE;
-- UPDATE o INSERT lote_stock
```

**Nuevo lote:**

```sql
INSERT INTO lote (cod_lote, fecha_vto_lote, id_articulo, tipo_lote, stock_total_lote, anulado, cod_movimiento_entrada, id_proveedor)
VALUES (...);
SELECT LAST_INSERT_ID() AS id_lote;
INSERT INTO lote_stock (id_lote, stock_lote, id_deposito) VALUES (...);
```

### P3.5 `stockp` (OC, no Factura Remito)

```sql
SELECT * FROM stockp WHERE id_stock = :id_stock AND CodigoMovimiento = :codmov_oc FOR UPDATE;
UPDATE stockp SET cantidad_pendiente = :pendiente, remitido_facturado = :rem_fact WHERE ...;
```

---

## P4 — Lista compra (opcional)

*Especificación detallada pendiente de segunda pasada del bloque VB6 ~4674–5083.* Patrón:

```sql
SELECT * FROM articulo WHERE IDArt = :id AND tipo_art = 'Articulo' FOR UPDATE;
UPDATE articulo SET ... ;

SELECT * FROM iva WHERE id = :alicuota;

INSERT INTO precios_historial (...) VALUES (...);
```

---

## P5 — Crédito `op_factura`

```sql
INSERT INTO op_factura (/* columnas según auditoría y DDL */)
VALUES (...);
```

Condición: `cond_compra_dias <> '0'`.

---

## P6 — Puentes OC / Remito

### P6.1 Estado OC

```sql
SELECT * FROM cuentaproveedor WHERE CodigoMovimiento = :codmov_oc AND TipoComprobante = 'OC' FOR UPDATE;
SELECT stockp.IDArt FROM stockp WHERE CodigoMovimiento = :codmov_oc AND remitido_facturado = 'No';
UPDATE cuentaproveedor SET Estado = :estado_oc WHERE ...;  -- 'Facturado' | 'Parcial'
```

### P6.2 `oc_factp`

```sql
INSERT INTO oc_factp (Codigo_MovimientoF, codigo_movimiento_oc, ...)
VALUES (:codigo_movimiento, :codmov_oc, ...);
```

### P6.3 Remito

```sql
SELECT DISTINCT nro_remito, CodigoMovimiento FROM ... /* derivado del command */;
SELECT * FROM cuentaproveedor WHERE CodigoMovimiento = :codmov_rem AND TipoComprobante = 'REM' FOR UPDATE;
UPDATE cuentaproveedor SET estado_remito = 'Facturado' WHERE ...;

INSERT INTO remp_factp (...) VALUES (:cod_mov_f, :cod_mov_r, ...);
```

---

## P7 — Proveedor habitual por artículo

```sql
UPDATE articulo SET codigoProveedor = :codigo_proveedor WHERE idart = :id_art;
```

Solo si flag `compras_cambia_prov_factura`.

---

## P8 — Series

Equivalente `GuardarSerie` (*auditoría*):

```sql
INSERT INTO serie_entrada (
  anulado, codigo_mov_entrada, desc_serie, disponible, fecha, id_articulo,
  nro_serie, tipo_comprobante, vto_serie, id_deposito
)
SELECT 'No', :codigo_movimiento, desc_serie, 'Si', :fecha, id_articulo,
       nro_serie, 'PFactura', vto_serie, id_deposito
FROM (/* valores del command */) AS v
ORDER BY orden;

INSERT INTO serie_movimiento (...)
SELECT ...
FROM serie_entrada
INNER JOIN stock ON stock.CodigoMovimiento = serie_entrada.codigo_mov_entrada
  AND stock.idart = serie_entrada.id_articulo
WHERE serie_entrada.codigo_mov_entrada = :codigo_movimiento
  AND serie_entrada.tipo_comprobante = 'PFactura';
```

> Ajustar nombres de columna (`idart` vs `IDArt`) al DDL real.

---

## P9 — Contabilidad

Secuencia lógica (*auditoría* `generar_asiento_cont`):

1. `SELECT activ_contabilidad FROM configuracion`
2. Lecturas `cont_paramatriz`, `cont_pc`, `articulo`, `gastos` según matriz de asiento
3. `SELECT * FROM cont_ejercicio WHERE ... FOR UPDATE` — incremento `Nro_asiento_ejercicio`
4. Por línea: `INSERT INTO cont_asiento (...)`
5. `UPDATE cont_ejercicio_saldo_cta`, `UPDATE cont_periodo_saldo_cta` según naturaleza cuenta

---

## P10 — Balanceo asiento

```sql
SELECT SUM(debe_asiento) AS sdebe, SUM(haber_asiento) AS shaber
FROM cont_asiento WHERE codigo_movimiento = :codigo_movimiento;

-- UPDATE de una o más líneas cont_asiento para compensar diferencia de centavos
```

---

## Parámetros de sesión MySQL (opcional)

```sql
SET SESSION innodb_lock_wait_timeout = :segundos;
```

---

## Lista de módulos → archivos de implementación sugeridos (futuro)

| Módulo | Archivo Python sugerido |
|--------|-------------------------|
| P1 | `legacy/numerador.py` |
| P2 | `legacy/cabecera.py` |
| P3 | `legacy/detalle_stock.py` |
| P4 | `legacy/lista_compra.py` |
| P5 | `legacy/op_factura.py` |
| P6 | `legacy/puentes.py` |
| P8 | `legacy/series.py` |
| P9–P10 | `legacy/contabilidad.py` |

---

## Trazabilidad

Cada bloque P* debe enlazarse en código a sección de [auditoria_facturas_compras_sql.md](auditoria_facturas_compras_sql.md) o líneas PFactura citadas en auditoría.
