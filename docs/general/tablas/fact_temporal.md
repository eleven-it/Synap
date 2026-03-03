# Tabla `fact_temporal`

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
| CondVenta | VARCHAR | Sí |  |  |  |
| Anulado | VARCHAR | Sí |  |  |  |
| Estado | VARCHAR | Sí |  |  |  |
| Modificado | VARCHAR | Sí |  |  |  |
| Imp | VARCHAR | Sí |  |  |  |
| Recibo | VARCHAR | Sí |  |  |  |
| ReciboMov | DECIMAL | Sí |  |  |  |
| Seleccionado | VARCHAR | Sí |  |  |  |
| Acuenta | DECIMAL | Sí |  |  |  |
| codigonumero | INT | Sí |  |  |  |
| CodUsuario | INT | No |  |  |  |
| id_fact_temporal | DOUBLE | No | ✓ |  |  |
| id_asig_cobranza | DOUBLE | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| id_recibo_factura | DOUBLE | Sí |  |  |  |

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
| Visualiza_ReciboCobro.frm | 6677 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporal whe… |
| Visualiza_ReciboCobro.frm | 6703 | SELECT | DataFactTemp.RecordSource = "SELECT * FROM fact_temporal WHE… |
| Visualiza_ReciboCobro.frm | 6780 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporal whe… |
| Visualiza_ReciboCobro.frm | 7537 | SELECT | conn.Execute "delete from fact_temporal where Codusuario = "… |
| Visualiza_ReciboCobro.frm | 7537 | DELETE | conn.Execute "delete from fact_temporal where Codusuario = "… |
| Visualiza_ReciboCobro.frm | 7953 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| Visualiza_ReciboCobro.frm | 7970 | SELECT | 'DataFactTemp.RecordSource = "select * from Fact_Temporal wh… |
| Visualiza_ReciboCobro.frm | 7990 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| Visualiza_ReciboCobro.frm | 8002 | SELECT | 'DataFactTemp.RecordSource = "select * from Fact_Temporal wh… |
| Visualiza_ReciboCobro.frm | 8286 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| Visualiza_ReciboCobro.frm | 9181 | SELECT | DataFactTemp.RecordSource = "SELECT * FROM fact_temporal WHE… |
| Visualiza_ReciboCobro.frm | 9210 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporal whe… |
| Visualiza_ReciboCobro.frm | 9253 | SELECT | DataFactTemp.RecordSource = "SELECT * FROM fact_temporal WHE… |
| Visualiza_ReciboCobro.frm | 9276 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporal whe… |
| Visualiza_ReciboCobro.frm | 9631 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| Visualiza_ReciboCobro.frm | 10744 | SELECT | conn.Execute "delete from fact_temporal where Codusuario = "… |
| Visualiza_ReciboCobro.frm | 10744 | DELETE | conn.Execute "delete from fact_temporal where Codusuario = "… |
| Visualiza_ReciboCobro.frm | 10780 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| CuentaCliente.frm | 2190 | SELECT | '        conn.Execute "delete from fact_temporal where Codus… |
| CuentaCliente.frm | 2190 | DELETE | '        conn.Execute "delete from fact_temporal where Codus… |
| CuentaCliente.frm | 2253 | SELECT | '         rs_fact_temporal.Open "SELECT * FROM fact_temporal… |
| CuentaCliente.frm | 2256 | SELECT | '            Visualiza_ReciboCobro.DataFactTemp.RecordSource… |
| CuentaCliente.frm | 2287 | SELECT | '        Visualiza_ReciboCobro.DataFactTemp.RecordSource = "… |
| Logi_Gestion2.frm | 9693 | SELECT | rs_FactTemp.Open "SELECT fact_temporal.*,usuarios.id_usuario… |
| Logi_Gestion.frm | 11358 | SELECT | rs_FactTemp.Open "SELECT fact_temporal.*,usuarios.id_usuario… |
| trz_trazabilidad.frm | 7247 | SELECT | conn.Execute "delete from fact_temporal where Codusuario = "… |
| trz_trazabilidad.frm | 7247 | DELETE | conn.Execute "delete from fact_temporal where Codusuario = "… |
| trz_trazabilidad.frm | 7355 | SELECT | rs_fact_temporal.Open "SELECT * FROM fact_temporal WHERE Cod… |
| trz_trazabilidad.frm | 7358 | SELECT | Visualiza_ReciboCobro.DataFactTemp.RecordSource = "SELECT * … |
| trz_trazabilidad.frm | 7389 | SELECT | Visualiza_ReciboCobro.DataFactTemp.RecordSource = "SELECT * … |
| ReciboCobro.frm | 6498 | SELECT | "From fact_temporal " & _ |
| ReciboCobro.frm | 7121 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporal whe… |
| ReciboCobro.frm | 7145 | SELECT | DataFactTemp.RecordSource = "SELECT * FROM fact_temporal WHE… |
| ReciboCobro.frm | 7236 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporal whe… |
| ReciboCobro.frm | 8057 | SELECT | conn.Execute "delete from fact_temporal where Codusuario = "… |
| ReciboCobro.frm | 8057 | DELETE | conn.Execute "delete from fact_temporal where Codusuario = "… |
| ReciboCobro.frm | 8340 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| ReciboCobro.frm | 8357 | SELECT | 'DataFactTemp.RecordSource = "select * from Fact_Temporal wh… |
| ReciboCobro.frm | 8377 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| ReciboCobro.frm | 8389 | SELECT | 'DataFactTemp.RecordSource = "select * from Fact_Temporal wh… |
| ReciboCobro.frm | 8736 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| ReciboCobro.frm | 8907 | SELECT | rs_recibo_factura.Open "SELECT fact_temporal.*,usuarios.id_u… |
| ReciboCobro.frm | 9825 | SELECT | DataFactTemp.RecordSource = "SELECT * FROM fact_temporal WHE… |
| ReciboCobro.frm | 9945 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporal whe… |
| ReciboCobro.frm | 10288 | SELECT | DataFactTemp.RecordSource = "SELECT * FROM fact_temporal WHE… |
| ReciboCobro.frm | 10317 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporal whe… |
| ReciboCobro.frm | 10450 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| ReciboCobro.frm | 10781 | SELECT | conn.Execute "delete from fact_temporal where Codusuario = "… |
| ReciboCobro.frm | 10781 | DELETE | conn.Execute "delete from fact_temporal where Codusuario = "… |
| ReciboCobro.frm | 10784 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporal whe… |
| ReciboCobro.frm | 11739 | SELECT | conn.Execute "delete from fact_temporal where Codusuario = "… |
| ReciboCobro.frm | 11739 | DELETE | conn.Execute "delete from fact_temporal where Codusuario = "… |
| ReciboCobro.frm | 11784 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| ReciboCobro.frm | 17392 | SELECT | conn.Execute "delete from fact_temporal where Codusuario = "… |
| ReciboCobro.frm | 17392 | DELETE | conn.Execute "delete from fact_temporal where Codusuario = "… |
| CargaComprobantesC.frm | 2198 | SELECT | DataFactTemp.RecordSource = "SELECT fact_temporal.*,usuarios… |
| CargaComprobantesC.frm | 2282 | SELECT | DataFactTemp.RecordSource = "SELECT fact_temporal.*,usuarios… |
| CargaComprobantesC.frm | 2430 | SELECT | DataFactTemp.RecordSource = "SELECT fact_temporal.*,usuarios… |
| CargaComprobantesC.frm | 2688 | SELECT | DataFactTemp.RecordSource = "SELECT fact_temporal.*,usuarios… |
| Visualiza_ReciboCobroC.frm | 6443 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporal whe… |
| Visualiza_ReciboCobroC.frm | 6469 | SELECT | DataFactTemp.RecordSource = "SELECT * FROM fact_temporal WHE… |
| Visualiza_ReciboCobroC.frm | 6546 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporal whe… |
| Visualiza_ReciboCobroC.frm | 7303 | SELECT | conn.Execute "delete from fact_temporal where Codusuario = "… |
| Visualiza_ReciboCobroC.frm | 7303 | DELETE | conn.Execute "delete from fact_temporal where Codusuario = "… |
| Visualiza_ReciboCobroC.frm | 7719 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| Visualiza_ReciboCobroC.frm | 7736 | SELECT | 'DataFactTemp.RecordSource = "select * from Fact_Temporal wh… |
| Visualiza_ReciboCobroC.frm | 7756 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| Visualiza_ReciboCobroC.frm | 7768 | SELECT | 'DataFactTemp.RecordSource = "select * from Fact_Temporal wh… |
| Visualiza_ReciboCobroC.frm | 8052 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| Visualiza_ReciboCobroC.frm | 8840 | SELECT | DataFactTemp.RecordSource = "SELECT * FROM fact_temporal WHE… |
| Visualiza_ReciboCobroC.frm | 8869 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporal whe… |
| Visualiza_ReciboCobroC.frm | 8912 | SELECT | DataFactTemp.RecordSource = "SELECT * FROM fact_temporal WHE… |
| Visualiza_ReciboCobroC.frm | 8935 | SELECT | DataFactTemp.RecordSource = "select * from fact_temporal whe… |
| Visualiza_ReciboCobroC.frm | 9267 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| Visualiza_ReciboCobroC.frm | 10401 | SELECT | conn.Execute "delete from fact_temporal where Codusuario = "… |
| Visualiza_ReciboCobroC.frm | 10401 | DELETE | conn.Execute "delete from fact_temporal where Codusuario = "… |
| Visualiza_ReciboCobroC.frm | 10437 | SELECT | rs_fact_temporal_total.Open "SELECT SUM(canceladoactual) AS … |
| Principal.frm | 6087 | SELECT | conn.Execute "delete from fact_temporal where Codusuario = "… |
| Principal.frm | 6087 | DELETE | conn.Execute "delete from fact_temporal where Codusuario = "… |
| Principal.frm | 6153 | SELECT | conn.Execute "delete from fact_temporal where Codusuario = "… |
| … | … | … | *(17 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)