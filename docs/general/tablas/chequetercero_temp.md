# Tabla `chequetercero_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| Nrocheque | DECIMAL | Sí |  |  |  |
| CodBanco | INT | Sí |  |  |  |
| Librador | VARCHAR | Sí |  |  |  |
| CodCliente | INT | Sí |  |  |  |
| CodProveedor | INT | Sí |  |  |  |
| Importe | DECIMAL | Sí |  |  |  |
| FechaEmision | DATE | Sí |  |  |  |
| FechaCobro | DATE | Sí |  |  |  |
| FechaVto | DATE | Sí |  |  |  |
| NroChequera | VARCHAR | Sí |  |  |  |
| Anulado | VARCHAR | Sí |  |  |  |
| CUITLibrador | VARCHAR | Sí |  |  |  |
| Rechazado | CHAR | Sí |  |  |  |
| id_chequetercero_temp | DOUBLE | No | ✓ |  |  |
| CodUsuario | INT | No |  |  |  |
| CodigoMovimientoOP | DECIMAL | Sí |  |  |  |
| CodigoMovimientoREC | DECIMAL | Sí |  |  |  |
| id_caja_cheque | INT | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| codigo_movimiento_fact | DOUBLE | Sí |  |  |  |
| tipo_cheque | VARCHAR | Sí |  |  |  |
| id_cheque | BIGINT | Sí |  |  |  |
| NroCompREC | VARCHAR | Sí |  |  |  |

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
| CargaBDeposito.frm | 1808 | SELECT | conn.Execute "DELETE FROM chequetercero_temp WHERE id_cheque… |
| CargaBDeposito.frm | 1808 | DELETE | conn.Execute "DELETE FROM chequetercero_temp WHERE id_cheque… |
| CargaBDeposito.frm | 1811 | SELECT | DataChequeTerceroTemp.RecordSource = "SELECT chequetercero_t… |
| CargaBDeposito.frm | 2065 | SELECT | DataChequeTerceroTemp.RecordSource = "SELECT * FROM chequete… |
| CargaBDeposito.frm | 2201 | SELECT | conn.Execute "DELETE FROM chequetercero_temp WHERE Codusuari… |
| CargaBDeposito.frm | 2201 | DELETE | conn.Execute "DELETE FROM chequetercero_temp WHERE Codusuari… |
| Visualiza_ReciboCobro.frm | 7536 | SELECT | conn.Execute "delete from chequetercero_temp where Codusuari… |
| Visualiza_ReciboCobro.frm | 7536 | DELETE | conn.Execute "delete from chequetercero_temp where Codusuari… |
| Visualiza_ReciboCobro.frm | 9003 | SELECT | conn.Execute "DELETE FROM chequetercero_temp WHERE id_cheque… |
| Visualiza_ReciboCobro.frm | 9003 | DELETE | conn.Execute "DELETE FROM chequetercero_temp WHERE id_cheque… |
| Visualiza_ReciboCobro.frm | 9958 | SELECT | rs_chequetercero_temp_total.Open "SELECT SUM(Importe) as Tot… |
| Visualiza_ReciboCobro.frm | 9969 | SELECT | DataChequeTerceroTemp.RecordSource = "SELECT chequetercero_t… |
| Visualiza_ReciboCobro.frm | 10317 | SELECT | DataChequeTerceroTemp.RecordSource = "select * from chequete… |
| Visualiza_ReciboCobro.frm | 10743 | SELECT | conn.Execute "delete from chequetercero_temp where Codusuari… |
| Visualiza_ReciboCobro.frm | 10743 | DELETE | conn.Execute "delete from chequetercero_temp where Codusuari… |
| Visualiza_ReciboCobro.frm | 12615 | SELECT | Visualiza_TPV.DataChequeTerceroTemp.RecordSource = "SELECT *… |
| Visualiza_ReciboCobro.frm | 12638 | SELECT | Visualiza_TPV.DataChequeTerceroTemp.RecordSource = "select c… |
| Visualiza_TPV.frm | 5658 | SELECT | conn.Execute "DELETE FROM chequetercero_temp WHERE id_cheque… |
| Visualiza_TPV.frm | 5658 | DELETE | conn.Execute "DELETE FROM chequetercero_temp WHERE id_cheque… |
| Visualiza_TPV.frm | 6155 | SELECT | conn.Execute "delete from chequetercero_temp where Codusuari… |
| Visualiza_TPV.frm | 6155 | DELETE | conn.Execute "delete from chequetercero_temp where Codusuari… |
| Visualiza_TPV.frm | 7654 | SELECT | rs_chequetercero_temp_total.Open "SELECT SUM(Importe) as Tot… |
| Visualiza_TPV.frm | 7666 | SELECT | DataChequeTerceroTemp.RecordSource = "SELECT chequetercero_t… |
| TPV.frm | 12116 | SELECT | conn.Execute "DELETE FROM chequetercero_temp WHERE id_cheque… |
| TPV.frm | 12116 | DELETE | conn.Execute "DELETE FROM chequetercero_temp WHERE id_cheque… |
| TPV.frm | 12937 | SELECT | conn.Execute "delete from chequetercero_temp where Codusuari… |
| TPV.frm | 12937 | DELETE | conn.Execute "delete from chequetercero_temp where Codusuari… |
| TPV.frm | 17214 | SELECT | rs_chequetercero_temp_total.Open "SELECT SUM(Importe) as Tot… |
| TPV.frm | 17226 | SELECT | DataChequeTerceroTemp.RecordSource = "SELECT chequetercero_t… |
| CuentaCliente.frm | 2189 | SELECT | '        conn.Execute "delete from chequetercero_temp where … |
| CuentaCliente.frm | 2189 | DELETE | '        conn.Execute "delete from chequetercero_temp where … |
| CuentaCliente.frm | 2298 | SELECT | '            Visualiza_ReciboCobro.DataChequeTerceroTemp.Rec… |
| CuentaCliente.frm | 2320 | SELECT | '                Visualiza_ReciboCobro.DataChequeTerceroTemp… |
| CuentaCliente.frm | 3055 | SELECT | Visualiza_TPV.DataChequeTerceroTemp.RecordSource = "SELECT *… |
| CuentaCliente.frm | 3079 | SELECT | Visualiza_TPV.DataChequeTerceroTemp.RecordSource = "select c… |
| Logi_Gestion2.frm | 5110 | SELECT | '                conn.Execute "DELETE FROM chequetercero_tem… |
| Logi_Gestion2.frm | 5110 | DELETE | '                conn.Execute "DELETE FROM chequetercero_tem… |
| Logi_Gestion2.frm | 5113 | SELECT | conn.Execute "DELETE FROM chequetercero_temp WHERE CodUsuari… |
| Logi_Gestion2.frm | 5113 | DELETE | conn.Execute "DELETE FROM chequetercero_temp WHERE CodUsuari… |
| Logi_Gestion2.frm | 5929 | SELECT | conn.Execute "DELETE FROM chequetercero_temp WHERE codUsuari… |
| Logi_Gestion2.frm | 5929 | DELETE | conn.Execute "DELETE FROM chequetercero_temp WHERE codUsuari… |
| Logi_Gestion2.frm | 9774 | JOIN | '                "LEFT JOIN chequetercero_temp ON (chequeter… |
| Logi_Gestion2.frm | 9805 | SELECT | "FROM chequetercero_temp " & _ |
| Logi_Gestion2.frm | 9855 | SELECT | rs_chequetercero_temp_total.Open "SELECT SUM(Importe) as Tot… |
| Logi_Gestion2.frm | 9868 | SELECT | '    DataChequeTerceroTemp.RecordSource = "SELECT chequeterc… |
| Logi_Gestion.frm | 6353 | SELECT | conn.Execute "DELETE FROM chequetercero_temp WHERE CodUsuari… |
| Logi_Gestion.frm | 6353 | DELETE | conn.Execute "DELETE FROM chequetercero_temp WHERE CodUsuari… |
| Logi_Gestion.frm | 6356 | SELECT | '                conn.Execute "DELETE FROM chequetercero_tem… |
| Logi_Gestion.frm | 6356 | DELETE | '                conn.Execute "DELETE FROM chequetercero_tem… |
| Logi_Gestion.frm | 7253 | SELECT | conn.Execute "DELETE FROM chequetercero_temp WHERE codUsuari… |
| Logi_Gestion.frm | 7253 | DELETE | conn.Execute "DELETE FROM chequetercero_temp WHERE codUsuari… |
| Logi_Gestion.frm | 11439 | JOIN | '                "LEFT JOIN chequetercero_temp ON (chequeter… |
| Logi_Gestion.frm | 11470 | SELECT | "FROM chequetercero_temp " & _ |
| Logi_Gestion.frm | 11520 | SELECT | rs_chequetercero_temp_total.Open "SELECT SUM(Importe) as Tot… |
| Logi_Gestion.frm | 11533 | SELECT | '    DataChequeTerceroTemp.RecordSource = "SELECT chequeterc… |
| OrdenPago.frm | 9863 | SELECT | DataChequeTerceroTemp.RecordSource = "SELECT * FROM chequete… |
| OrdenPago.frm | 10913 | SELECT | rs_total_chequetercero.Open "SELECT SUM(Importe) as TotalChe… |
| OrdenPago.frm | 10923 | SELECT | rs_total_chequetercero.Open "SELECT AVG(TIMESTAMPDIFF(DAY, C… |
| OrdenPago.frm | 10933 | SELECT | DataChequeTerceroTemp.RecordSource = "select chequetercero_t… |
| OrdenPago.frm | 12548 | SELECT | conn.Execute "delete from chequetercero_temp where Codusuari… |
| OrdenPago.frm | 12548 | DELETE | conn.Execute "delete from chequetercero_temp where Codusuari… |
| trz_trazabilidad.frm | 6894 | SELECT | Visualiza_TPV.DataChequeTerceroTemp.RecordSource = "SELECT *… |
| trz_trazabilidad.frm | 6918 | SELECT | Visualiza_TPV.DataChequeTerceroTemp.RecordSource = "select c… |
| trz_trazabilidad.frm | 7246 | SELECT | conn.Execute "delete from chequetercero_temp where Codusuari… |
| trz_trazabilidad.frm | 7246 | DELETE | conn.Execute "delete from chequetercero_temp where Codusuari… |
| trz_trazabilidad.frm | 7400 | SELECT | Visualiza_ReciboCobro.DataChequeTerceroTemp.RecordSource = "… |
| trz_trazabilidad.frm | 7422 | SELECT | Visualiza_ReciboCobro.DataChequeTerceroTemp.RecordSource = "… |
| trz_trazabilidadComp.frm | 4709 | SELECT | conn.Execute "delete from chequetercero_temp where Codusuari… |
| trz_trazabilidadComp.frm | 4709 | DELETE | conn.Execute "delete from chequetercero_temp where Codusuari… |
| trz_trazabilidadComp.frm | 4858 | SELECT | Visualiza_OrdenPago.DataChequeTerceroTemp.RecordSource = "se… |
| trz_trazabilidadComp.frm | 4882 | SELECT | Visualiza_OrdenPago.DataChequeTerceroTemp.RecordSource = "se… |
| Visualiza_OrdenPagoC.frm | 6990 | SELECT | DataChequeTerceroTemp.RecordSource = "SELECT * FROM chequete… |
| Visualiza_OrdenPagoC.frm | 7697 | SELECT | rs_total_chequetercero.Open "SELECT SUM(Importe) as TotalChe… |
| Visualiza_OrdenPagoC.frm | 7706 | SELECT | DataChequeTerceroTemp.RecordSource = "select chequetercero_t… |
| Visualiza_OrdenPagoC.frm | 8757 | SELECT | conn.Execute "delete from chequetercero_temp where Codusuari… |
| Visualiza_OrdenPagoC.frm | 8757 | DELETE | conn.Execute "delete from chequetercero_temp where Codusuari… |
| ListaCheque3.frm | 577 | SELECT | CargaBDeposito.DataChequeTerceroTemp.RecordSource = "select … |
| ListaCheque3.frm | 603 | SELECT | CargaBDeposito.DataChequeTerceroTemp.RecordSource = "SELECT … |
| ListaCheque3.frm | 635 | SELECT | DataChequeTerceroTemp.RecordSource = "select * from chequete… |
| ListaCheque3.frm | 654 | SELECT | OrdenPago.DataChequeTerceroTemp.RecordSource = "select * fro… |
| … | … | … | *(67 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)