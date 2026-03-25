# Auditoría: Facturas de compras — Repositorio SQL (PFactura y rutinas directas)

**Fuente:** `administranet_vb6/Formularios/PFactura.frm` (líneas aproximadas según grep/read del repo).  
**Convención:** *Confirmado por código* | *Inferencia fuerte* | *Hipótesis / pendiente*

---

## 1. Transacciones y sesión

| Orden | Sentencia / acción | Propósito |
|-------|-------------------|-----------|
| T1-a | `conn.Execute "SET AUTOCOMMIT=0"` | Inicio modo transaccional (~3753, ~3772, ~7966) |
| T1-b | `BeginTrans` + `SELECT * FROM codmov where codigo = 1` (pessimistic) + `Update` | Numerador global (~3752–3761) |
| T1-c | `CommitTrans` | Cierra T1 (~3765–3767) |
| T2-a | `BeginTrans` + `SET AUTOCOMMIT=0` | Cuerpo del comprobante (~3770–3772) |
| T2-b | `CommitTrans` / `RollbackTrans` | Éxito o `captura:` (~5271–5274, ~5347–5354) |

---

## 2. SELECT previos a escritura (validación / carga)

| SQL (esqueleto) | Línea ref. | Propósito |
|-----------------|------------|-----------|
| `SELECT * from cuerpostockp where CodUsuario = … And NOT isnull(codmov_remito)` | ~3525 | Exigir renglón con remito si `Factura Remito` |
| `SELECT * from cuerpostockp where … NOT isnull(codmov_oc)` | ~3548 | Idem OC |
| `SELECT * FROM en_vale_factura_temp WHERE id_usuario=…` | ~3571 | Idem Vale |
| `SELECT periodos.*,years.* FROM periodos,years WHERE … abierto_periodo = 'Si'` | ~3647 | Período fiscal fecha registro |
| `SELECT * FROM Years WHERE year = …` | ~3691 | Año del comprobante |
| `SELECT * FROM codmov where codigo = 1` | ~3756 | Numerador |
| `SELECT * FROM cuentaproveedor WHERE CodigoMovimiento = 1` | ~3789 | Plantilla AddNew cabecera |
| `SELECT proveedor.codigo,proveedor.saldo FROM proveedor WHERE codigo = …` | ~3826, ~3868 | Saldo CC |
| `SELECT * FROM percep_prov_temp WHERE … id_usuario … AND visualiza = 'No'` | ~3892 | Percepciones IB |
| `SELECT * FROM percepcion_prov_convenio WHERE id_percepcion_prov_convenio = 1` | ~3897 | Plantilla |
| `SELECT * FROM percep_prov WHERE id_percep_prov = 1` | ~3898 | Plantilla |
| `SELECT * FROM caja_saldo WHERE id_caja = … AND moneda = 'Pesos'` | ~4045–4047 | Contado |
| `SELECT * from caja where codigo_movimiento = 1` | ~4057 | Plantilla movimiento caja |
| `SELECT * FROM stock where CodigoMovimiento = 1` | ~4193 | Plantilla renglón |
| `SELECT * FROM stock_deposito WHERE id_articulo = … And id_deposito = …` | ~4210 | Saldo depósito |
| `SELECT stockp.… FROM stockp WHERE …` | ~4220 | Pedido proveedor OC |
| `SELECT * FROM otro_egreso WHERE id_oe = 1` | ~4378 | Gasto |
| `SELECT * FROM lote WHERE cod_lote = … AND id_articulo = … AND anulado = 'No'` | ~4481 | Lote existente |
| `SELECT * FROM lote where id_lote = 0` / `last_insert_id()` | ~4526–4542 | Alta lote |
| `SELECT * FROM stockp WHERE … id_stock … AND CodigoMovimiento = … codmov_oc` | ~4582 | Línea OC |
| `SELECT * FROM op_factura WHERE CodigoMovimiento = 1` | ~5089 | Plantilla OP |
| `SELECT … FROM cuerpostockp WHERE … CodigoMovimiento … visualiza = 'No'` | ~5136 | Validación OC |
| `SELECT distinct(nro_oc) … FROM cuerpostockp …` | ~5142 | Agrupar OC |
| `SELECT * FROM oc_factp WHERE id_oc_factp = 1` | ~5152 | Plantilla vínculo |
| `SELECT * FROM cuentaproveedor WHERE CodigoMovimiento = … And TipoComprobante = 'OC'` | ~5157 | Estado OC |
| `SELECT stockp.IDArt FROM stockp WHERE … remitido_facturado='No'` | ~5159 | Parcial vs total |
| `SELECT distinct (nro_remito) … FROM cuerpostockp … GROUP BY nro_remito` | ~5206 | Remitos |
| `SELECT * FROM remp_factp WHERE id_remp_factp = 1` | ~5208 | Plantilla |
| `SELECT * FROM cuentaproveedor WHERE … TipoComprobante = 'REM'` | ~5217 | Actualizar remito |
| `SELECT * FROM configuracion` (activ_contabilidad) | ~8199 | `generar_asiento_cont` |
| Múltiples `SELECT * from cont_paramatriz where id_paramatriz = …` | ~8600–9027 | Cuentas IVA, impuestos, percepciones, descuentos, mercaderías, proveedor |
| `SELECT * from articulo where idart = …` | ~8331 | Tipo mercadería / gasto |
| `SELECT id_pc from gastos where codigo = …` | ~8389 | Imputación gasto |
| `Select * from cont_ejercicio …` / `cont_periodo …` | ~9192–9214 | Ejercicio/período |
| `SELECT * from cont_asiento WHERE id_asiento = 1` | ~9238 | Plantilla línea asiento |
| `SELECT * FROM cont_ejercicio_saldo_cta …` / `cont_periodo_saldo_cta …` | ~9301–9341 | Saldos |
| `SELECT * from cont_pc where id_pc = …` | ~9279 | Naturaleza cuenta |
| Subconsulta validación series vs `serie_entrada_temp` | ~9828–9833 | `ValCantSerie` |

**Validación duplicados comprobante:**  
`SELECT * FROM cuentaproveedor WHERE nrocomprobante = '…' And Codigo = … And (TipoComprobante = 'FA' or 'FC' or 'FB') And Anulado = 'No' …` (variantes con `nrocompbusq`, `ModTalonario`) — ~7641–7668. **FM no está en la tupla OR.** *Confirmado por código.*

---

## 3. INSERT / UPDATE / DELETE explícitos (Execute)

| Sentencia | Línea ref. | Propósito |
|-----------|------------|-----------|
| `INSERT INTO en_vale_factura(…) SELECT … FROM en_vale_factura_temp WHERE id_usuario=…` | ~3849 | Vincular vales |
| `UPDATE en_vale_viaje SET estado='En Factura' WHERE CodigoMovimiento=…` | ~3861 | Estado vale |
| `UPDATE articulo SET codigoProveedor = … WHERE idart = …` | ~4663 | Opción configuración |
| `DELETE FROM cuerpostockp WHERE Orden = …` | ~6700 | Borrar renglón en edición |
| `DELETE serie_entrada_temp.* FROM serie_entrada_temp …` | ~6705 | *Ver precedencia OR en doc pendientes* |
| `delete from cuerpostockp where Codusuario = … AND visualiza = 'No'` | ~7775 | `Elimina_Temporal` |
| `delete from percep_prov_temp where id_usuario = … AND visualiza = 'No'` | ~7776 | Idem |
| `DELETE FROM serie_entrada_temp WHERE … OR tipo_comprobante = 'PRemito'` | ~7780–7783 | Idem |
| `INSERT INTO serie_entrada (…) SELECT … FROM serie_entrada_temp WHERE … tipo_comprobante = 'PFactura'` | ~9962–9975 | `GuardarSerie` |
| `INSERT INTO serie_movimiento (…) SELECT … FROM serie_entrada INNER JOIN stock …` | ~9979–9996 | `GuardarSerie` |

**Recordset AddNew/Update** (no son cadenas SQL en claro): `cuentaproveedor`, `proveedor`, `percep_*`, `caja_saldo`, `caja`, `stock`, `stock_deposito`, `stockp`, `lote`, `lote_stock`, `otro_egreso`, `op_factura`, `oc_factp`, `remp_factp`, `pedido` (cuentaproveedor OC), `articulo`, `precios_historial`, `cont_asiento`, saldos contables, `codmov`, etc.

---

## 4. Orden de ejecución lógico (alta)

1. Validaciones SELECT en buffers (`cuerpostockp`, `en_vale_factura_temp`).  
2. Validación fiscal `periodos`/`years`.  
3. **codmov** (transacción 1).  
4. Formato `num`; **cuentaproveedor** + vales + percepciones + caja (contado) + **proveedor**.  
5. Loop **stock** y tablas asociadas por ítem.  
6. Opcional **articulo** / **precios_historial**.  
7. **op_factura**.  
8. **OC** / **Remito** (updates + inserts puente).  
9. **GuardarSerie**.  
10. **generar_asiento_cont**.  
11. **CommitTrans** → **Balancea_asiento** → **visualiza_asiento_cont** (post-commit).

---

## 5. Stored procedures

*Ninguno referenciado en los fragmentos analizados de PFactura.* *Hipótesis / pendiente:* pueden existir triggers en MySQL no visibles en VB6.

---

## 6. Objetos ADO citados

- **Connection:** `conn`  
- **Recordsets:** prefijos `rs_` según tabla lógica (lista en `auditoria_facturas_compras_objetos_vb6.md`)

---

## Trazabilidad ejemplo

| Hallazgo | Evidencia | Conclusión |
|----------|-----------|------------|
| Numerador separado | `codmov` + `CommitTrans` antes del bloque grande | *Confirmado por código* |
| FM excluido de duplicados | `WHERE (TipoComprobante = 'FA' or … 'FB')` sin FM | *Confirmado por código* |
| Series insert masivo | `INSERT INTO serie_entrada … SELECT … serie_entrada_temp` | *Confirmado por código* |
