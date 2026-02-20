# Tabla `fact_temporalp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| Fecha | DATE | Sí |  |  |  |
| TipoComprobante | VARCHAR | Sí |  |  |  |
| NroComprobante | VARCHAR | Sí |  |  |  |
| Importe | DECIMAL | Sí |  |  |  |
| ImporteNC | DECIMAL | Sí |  |  |  |
| Cancelado | DECIMAL | Sí |  |  |  |
| CanceladoActual | DECIMAL | Sí |  |  |  |
| Saldo | DECIMAL | Sí |  |  |  |
| Neto | DECIMAL | Sí |  |  |  |
| Codigo | VARCHAR | Sí |  |  |  |
| CodigoMovimiento | DECIMAL | Sí |  |  |  |
| Vencimiento | DATE | Sí |  |  |  |
| CondCompra | VARCHAR | Sí |  |  |  |
| Anulado | VARCHAR | Sí |  |  |  |
| Estado | VARCHAR | Sí |  |  |  |
| Modificado | VARCHAR | Sí |  |  |  |
| Imp | VARCHAR | Sí |  |  |  |
| OP | VARCHAR | Sí |  |  |  |
| OPMov | DECIMAL | Sí |  |  |  |
| Seleccionado | VARCHAR | Sí |  |  |  |
| Acuenta | DECIMAL | Sí |  |  |  |
| codigonumero | INT | Sí |  |  |  |
| CodUsuario | INT | No |  |  |  |
| importe_retencion | DECIMAL | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| id_fact_temporalp | DOUBLE | No | ✓ |  |  |
| id_op_factura | DOUBLE | Sí |  |  |  |
| id_asig_pago | DOUBLE | Sí |  |  |  |
| fecha_registro | DATE | Sí |  |  |  |
| fecha_recepcion | DATE | Sí |  |  |  |
| id_sucursal | INT | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

*No se encontraron JOINs que involucren esta tabla en el código escaneado.*

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| OrdenPago.frm | 7314 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporalp wh… |
| OrdenPago.frm | 7334 | SELECT | DataFactTemp.RecordSource = "SELECT * FROM fact_temporalp WH… |
| OrdenPago.frm | 7409 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporalp wh… |
| OrdenPago.frm | 8922 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| OrdenPago.frm | 8965 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| OrdenPago.frm | 9300 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| OrdenPago.frm | 9580 | SELECT | rs_op_factura.Open "SELECT fact_temporalp.*,usuarios.id_usua… |
| OrdenPago.frm | 10058 | SELECT | DataFactTemp.RecordSource = "SELECT * FROM fact_temporalp WH… |
| OrdenPago.frm | 10105 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporalp wh… |
| OrdenPago.frm | 10740 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| OrdenPago.frm | 11592 | SELECT | '        rs_factemp.Open "SELECT SUM(neto) as SumNetoTemp FR… |
| OrdenPago.frm | 11835 | SELECT | '        rs_factemp.Open "SELECT SUM(neto) as SumNetoTemp FR… |
| OrdenPago.frm | 11838 | SELECT | rs_factemp.Open "SELECT SUM(Neto*CanceladoActual/Importe) as… |
| OrdenPago.frm | 11975 | SELECT | rs_factemp.Open "SELECT SUM(Neto*CanceladoActual/Importe) as… |
| OrdenPago.frm | 12445 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporalp wh… |
| OrdenPago.frm | 12549 | SELECT | conn.Execute "delete from fact_temporalp where Codusuario = … |
| OrdenPago.frm | 12549 | DELETE | conn.Execute "delete from fact_temporalp where Codusuario = … |
| OrdenPago.frm | 16523 | SELECT | conn.Execute "delete from fact_temporalp where Codusuario = … |
| OrdenPago.frm | 16523 | DELETE | conn.Execute "delete from fact_temporalp where Codusuario = … |
| OrdenPago.frm | 16597 | SELECT | DataFactTemp.RecordSource = "SELECT * FROM fact_temporalp WH… |
| OrdenPago.frm | 16626 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporalp wh… |
| AsigPago.frm | 915 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporalp wh… |
| AsigPago.frm | 951 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporalp wh… |
| AsigPago.frm | 981 | SELECT | DataAcuentaTemp.RecordSource = "select * from fact_temporalp… |
| AsigPago.frm | 1013 | SELECT | DataAcuentaTemp.RecordSource = "select * from fact_temporalp… |
| AsigPago.frm | 1084 | SELECT | .Source = "SELECT * FROM fact_temporalp WHERE " & _ |
| AsigPago.frm | 1109 | SELECT | .Source = "SELECT * FROM fact_temporalp WHERE " & _ |
| AsigPago.frm | 1278 | SELECT | .Source = "SELECT * FROM fact_temporalp WHERE " & _ |
| AsigPago.frm | 1556 | SELECT | conn.Execute "delete from fact_temporalp where Codusuario = … |
| AsigPago.frm | 1556 | DELETE | conn.Execute "delete from fact_temporalp where Codusuario = … |
| trz_trazabilidadComp.frm | 4711 | SELECT | conn.Execute "delete from fact_temporalp  where Codusuario =… |
| trz_trazabilidadComp.frm | 4711 | DELETE | conn.Execute "delete from fact_temporalp  where Codusuario =… |
| trz_trazabilidadComp.frm | 4810 | SELECT | Visualiza_OrdenPago.DataFactTemp.RecordSource = "SELECT * FR… |
| trz_trazabilidadComp.frm | 4847 | SELECT | Visualiza_OrdenPago.DataFactTemp.RecordSource = "select * fr… |
| Visualiza_OrdenPagoC.frm | 6356 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| Visualiza_OrdenPagoC.frm | 6398 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| Visualiza_OrdenPagoC.frm | 6667 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| Visualiza_OrdenPagoC.frm | 7155 | SELECT | DataFactTemp.RecordSource = "SELECT * FROM fact_temporalp WH… |
| Visualiza_OrdenPagoC.frm | 7184 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporalp wh… |
| Visualiza_OrdenPagoC.frm | 7600 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| Visualiza_OrdenPagoC.frm | 8613 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporalp wh… |
| Visualiza_OrdenPagoC.frm | 8758 | SELECT | conn.Execute "delete from fact_temporalp where Codusuario = … |
| Visualiza_OrdenPagoC.frm | 8758 | DELETE | conn.Execute "delete from fact_temporalp where Codusuario = … |
| CargaComprobantesP.frm | 3473 | SELECT | DataFactTemp.RecordSource = "SELECT fact_temporalp.*,usuario… |
| CargaComprobantesP.frm | 3574 | SELECT | DataFactTemp.RecordSource = "SELECT fact_temporalp.*,usuario… |
| CargaComprobantesP.frm | 3657 | SELECT | DataFactTemp.RecordSource = "SELECT fact_temporalp.*,usuario… |
| CuentaProveedor.frm | 1268 | SELECT | '        conn.Execute "delete from fact_temporalp  where Cod… |
| CuentaProveedor.frm | 1268 | DELETE | '        conn.Execute "delete from fact_temporalp  where Cod… |
| CuentaProveedor.frm | 1344 | SELECT | '        Visualiza_OrdenPago.DataFactTemp.RecordSource = "SE… |
| CuentaProveedor.frm | 1381 | SELECT | '        Visualiza_OrdenPago.DataFactTemp.RecordSource = "se… |
| Principal.frm | 6088 | SELECT | conn.Execute "delete from fact_temporalp where Codusuario = … |
| Principal.frm | 6088 | DELETE | conn.Execute "delete from fact_temporalp where Codusuario = … |
| Principal.frm | 6154 | SELECT | conn.Execute "delete from fact_temporalp where Codusuario = … |
| Principal.frm | 6154 | DELETE | conn.Execute "delete from fact_temporalp where Codusuario = … |
| Visualiza_OrdenPago.frm | 6620 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| Visualiza_OrdenPago.frm | 6662 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| Visualiza_OrdenPago.frm | 6931 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| Visualiza_OrdenPago.frm | 7447 | SELECT | DataFactTemp.RecordSource = "SELECT * FROM fact_temporalp WH… |
| Visualiza_OrdenPago.frm | 7476 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporalp wh… |
| Visualiza_OrdenPago.frm | 7990 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| Visualiza_OrdenPago.frm | 9007 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporalp wh… |
| Visualiza_OrdenPago.frm | 9139 | SELECT | conn.Execute "delete from fact_temporalp where Codusuario = … |
| Visualiza_OrdenPago.frm | 9139 | DELETE | conn.Execute "delete from fact_temporalp where Codusuario = … |
| Visualiza.bas | 7373 | SELECT | conn.Execute "delete from fact_temporalp  where Codusuario =… |
| Visualiza.bas | 7373 | DELETE | conn.Execute "delete from fact_temporalp  where Codusuario =… |
| Visualiza.bas | 7457 | SELECT | Visualiza_OrdenPago.DataFactTemp.RecordSource = "SELECT * FR… |
| Visualiza.bas | 7509 | SELECT | Visualiza_OrdenPago.DataFactTemp.RecordSource = "select * fr… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)