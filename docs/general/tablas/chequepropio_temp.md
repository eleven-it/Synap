# Tabla `chequepropio_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| NroCheque | DECIMAL | Sí |  |  |  |
| CodBanco | INT | Sí |  |  |  |
| NroChequera | VARCHAR | Sí |  |  |  |
| CodCuenta | INT | Sí |  |  |  |
| CodChequera | INT | Sí |  |  |  |
| CodProveedor | VARCHAR | Sí |  |  |  |
| Importe | DECIMAL | Sí |  |  |  |
| FechaEmision | DATETIME | Sí |  |  |  |
| FechaCobro | DATETIME | Sí |  |  |  |
| FechaVto | DATETIME | Sí |  |  |  |
| Anulado | VARCHAR | Sí |  |  |  |
| CodUsuario | INT | No |  |  |  |
| CodigoMovimientoOP | DECIMAL | Sí |  |  |  |
| id_chequepropio_temp | INT | No | ✓ |  |  |
| id_caja_cheque | INT | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| tipo_cheque | VARCHAR | Sí |  |  |  |

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
| OrdenPago.frm | 9892 | SELECT | DataChequePropioTemp.RecordSource = "SELECT * FROM chequepro… |
| OrdenPago.frm | 10944 | SELECT | rs_total_chequepropio.Open "SELECT SUM(Importe) as TotalCheq… |
| OrdenPago.frm | 10953 | SELECT | DataChequePropioTemp.RecordSource = "select chequepropio_tem… |
| OrdenPago.frm | 12431 | SELECT | DataChequePropioTemp.RecordSource = "select * from chequepro… |
| OrdenPago.frm | 12550 | SELECT | conn.Execute "delete from chequepropio_temp where Codusuario… |
| OrdenPago.frm | 12550 | DELETE | conn.Execute "delete from chequepropio_temp where Codusuario… |
| trz_trazabilidadComp.frm | 4710 | SELECT | conn.Execute "delete from chequepropio_temp where Codusuario… |
| trz_trazabilidadComp.frm | 4710 | DELETE | conn.Execute "delete from chequepropio_temp where Codusuario… |
| trz_trazabilidadComp.frm | 4896 | SELECT | Visualiza_OrdenPago.DataChequePropioTemp.RecordSource = "sel… |
| trz_trazabilidadComp.frm | 4919 | SELECT | Visualiza_OrdenPago.DataChequePropioTemp.RecordSource = "sel… |
| Visualiza_OrdenPagoC.frm | 7004 | SELECT | DataChequePropioTemp.RecordSource = "SELECT * FROM chequepro… |
| Visualiza_OrdenPagoC.frm | 7717 | SELECT | rs_total_chequepropio.Open "SELECT SUM(Importe) as TotalCheq… |
| Visualiza_OrdenPagoC.frm | 7726 | SELECT | DataChequePropioTemp.RecordSource = "select chequepropio_tem… |
| Visualiza_OrdenPagoC.frm | 8599 | SELECT | DataChequePropioTemp.RecordSource = "select * from chequepro… |
| Visualiza_OrdenPagoC.frm | 8759 | SELECT | conn.Execute "delete from chequepropio_temp where Codusuario… |
| Visualiza_OrdenPagoC.frm | 8759 | DELETE | conn.Execute "delete from chequepropio_temp where Codusuario… |
| CuentaProveedor.frm | 1267 | SELECT | '        conn.Execute "delete from chequepropio_temp where C… |
| CuentaProveedor.frm | 1267 | DELETE | '        conn.Execute "delete from chequepropio_temp where C… |
| CuentaProveedor.frm | 1427 | SELECT | '          Visualiza_OrdenPago.DataChequePropioTemp.RecordSo… |
| CuentaProveedor.frm | 1449 | SELECT | '                Visualiza_OrdenPago.DataChequePropioTemp.Re… |
| Principal.frm | 6070 | SELECT | conn.Execute "delete from chequepropio_temp where Codusuario… |
| Principal.frm | 6070 | DELETE | conn.Execute "delete from chequepropio_temp where Codusuario… |
| Principal.frm | 6136 | SELECT | conn.Execute "delete from chequepropio_temp where Codusuario… |
| Principal.frm | 6136 | DELETE | conn.Execute "delete from chequepropio_temp where Codusuario… |
| CargaChequePropio.frm | 609 | SELECT | OrdenPago.DataChequePropioTemp.RecordSource = "select * from… |
| CargaChequePropio.frm | 836 | SELECT | rs_chequepropio_temp.Open "select * from chequepropio_temp W… |
| Visualiza_OrdenPago.frm | 7292 | SELECT | DataChequePropioTemp.RecordSource = "SELECT * FROM chequepro… |
| Visualiza_OrdenPago.frm | 8107 | SELECT | rs_total_chequepropio.Open "SELECT SUM(Importe) as TotalCheq… |
| Visualiza_OrdenPago.frm | 8116 | SELECT | DataChequePropioTemp.RecordSource = "select chequepropio_tem… |
| Visualiza_OrdenPago.frm | 8993 | SELECT | DataChequePropioTemp.RecordSource = "select * from chequepro… |
| Visualiza_OrdenPago.frm | 9140 | SELECT | conn.Execute "delete from chequepropio_temp where Codusuario… |
| Visualiza_OrdenPago.frm | 9140 | DELETE | conn.Execute "delete from chequepropio_temp where Codusuario… |
| Visualiza.bas | 7372 | SELECT | conn.Execute "delete from chequepropio_temp where Codusuario… |
| Visualiza.bas | 7372 | DELETE | conn.Execute "delete from chequepropio_temp where Codusuario… |
| Visualiza.bas | 7559 | SELECT | Visualiza_OrdenPago.DataChequePropioTemp.RecordSource = "sel… |
| Visualiza.bas | 7583 | SELECT | Visualiza_OrdenPago.DataChequePropioTemp.RecordSource = "sel… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)