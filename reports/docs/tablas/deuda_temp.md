# Tabla `deuda_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_deuda_temp | DOUBLE | No | ✓ |  |  |
| id_deuda_abm | INT | No |  |  |  |
| nombre_deuda_temp | VARCHAR | Sí |  |  |  |
| tipo_deuda_temp | VARCHAR | Sí |  |  |  |
| fecha_deuda_temp | DATE | Sí |  |  |  |
| importe_deuda_temp | DOUBLE | Sí |  |  |  |
| estado_deuda_temp | VARCHAR | Sí |  |  |  |
| codigo_movimiento_op | DOUBLE | Sí |  |  |  |
| fecha_emision_deuda_temp | DATE | Sí |  |  |  |
| fecha_vencimiento_deuda_temp | DATE | Sí |  |  |  |
| nro_deuda_temp | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |

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
| OrdenPago.frm | 8813 | SELECT | data_mp_temp.RecordSource = "SELECT * FROM deuda_temp WHERE … |
| OrdenPago.frm | 8829 | SELECT | data_mp_temp.RecordSource = "SELECT * FROM deuda_temp WHERE … |
| OrdenPago.frm | 8843 | SELECT | rs_total_mp.Open "SELECT SUM(importe_deuda_temp) as total_mp… |
| OrdenPago.frm | 9233 | SELECT | conn.Execute "DELETE FROM deuda_temp WHERE id_deuda_temp = "… |
| OrdenPago.frm | 9233 | DELETE | conn.Execute "DELETE FROM deuda_temp WHERE id_deuda_temp = "… |
| OrdenPago.frm | 9236 | SELECT | data_mp_temp.RecordSource = "SELECT * FROM deuda_temp WHERE … |
| OrdenPago.frm | 9248 | SELECT | rs_total_mp.Open "SELECT SUM(importe_deuda_temp) as total_mp… |
| OrdenPago.frm | 12552 | SELECT | conn.Execute "delete from deuda_temp where id_usuario = " & … |
| OrdenPago.frm | 12552 | DELETE | conn.Execute "delete from deuda_temp where id_usuario = " & … |
| trz_trazabilidadComp.frm | 4713 | SELECT | conn.Execute "delete from deuda_temp where id_usuario = " & … |
| trz_trazabilidadComp.frm | 4713 | DELETE | conn.Execute "delete from deuda_temp where id_usuario = " & … |
| trz_trazabilidadComp.frm | 5175 | SELECT | Visualiza_OrdenPago.data_mp_temp.RecordSource = "SELECT * FR… |
| trz_trazabilidadComp.frm | 5195 | SELECT | Visualiza_OrdenPago.data_mp_temp.RecordSource = "SELECT * FR… |
| Visualiza_OrdenPagoC.frm | 6253 | SELECT | data_mp_temp.RecordSource = "SELECT * FROM deuda_temp WHERE … |
| Visualiza_OrdenPagoC.frm | 6269 | SELECT | data_mp_temp.RecordSource = "SELECT * FROM deuda_temp WHERE … |
| Visualiza_OrdenPagoC.frm | 6283 | SELECT | rs_total_mp.Open "SELECT SUM(importe_deuda_temp) as total_mp… |
| Visualiza_OrdenPagoC.frm | 6602 | SELECT | conn.Execute "DELETE FROM deuda_temp WHERE id_deuda_temp = "… |
| Visualiza_OrdenPagoC.frm | 6602 | DELETE | conn.Execute "DELETE FROM deuda_temp WHERE id_deuda_temp = "… |
| Visualiza_OrdenPagoC.frm | 6605 | SELECT | data_mp_temp.RecordSource = "SELECT * FROM deuda_temp WHERE … |
| Visualiza_OrdenPagoC.frm | 6617 | SELECT | rs_total_mp.Open "SELECT SUM(importe_deuda_temp) as total_mp… |
| Visualiza_OrdenPagoC.frm | 8761 | SELECT | conn.Execute "delete from deuda_temp where id_usuario = " & … |
| Visualiza_OrdenPagoC.frm | 8761 | DELETE | conn.Execute "delete from deuda_temp where id_usuario = " & … |
| CuentaProveedor.frm | 1605 | SELECT | '                Visualiza_OrdenPago.data_mp_temp.RecordSour… |
| CuentaProveedor.frm | 1624 | SELECT | '                Visualiza_OrdenPago.data_mp_temp.RecordSour… |
| Principal.frm | 6081 | SELECT | conn.Execute "delete from deuda_temp where id_usuario = " & … |
| Principal.frm | 6081 | DELETE | conn.Execute "delete from deuda_temp where id_usuario = " & … |
| Principal.frm | 6147 | SELECT | conn.Execute "delete from deuda_temp where id_usuario = " & … |
| Principal.frm | 6147 | DELETE | conn.Execute "delete from deuda_temp where id_usuario = " & … |
| Visualiza_OrdenPago.frm | 6517 | SELECT | data_mp_temp.RecordSource = "SELECT * FROM deuda_temp WHERE … |
| Visualiza_OrdenPago.frm | 6533 | SELECT | data_mp_temp.RecordSource = "SELECT * FROM deuda_temp WHERE … |
| Visualiza_OrdenPago.frm | 6547 | SELECT | rs_total_mp.Open "SELECT SUM(importe_deuda_temp) as total_mp… |
| Visualiza_OrdenPago.frm | 6866 | SELECT | conn.Execute "DELETE FROM deuda_temp WHERE id_deuda_temp = "… |
| Visualiza_OrdenPago.frm | 6866 | DELETE | conn.Execute "DELETE FROM deuda_temp WHERE id_deuda_temp = "… |
| Visualiza_OrdenPago.frm | 6869 | SELECT | data_mp_temp.RecordSource = "SELECT * FROM deuda_temp WHERE … |
| Visualiza_OrdenPago.frm | 6881 | SELECT | rs_total_mp.Open "SELECT SUM(importe_deuda_temp) as total_mp… |
| Visualiza_OrdenPago.frm | 9142 | SELECT | conn.Execute "delete from deuda_temp where id_usuario = " & … |
| Visualiza_OrdenPago.frm | 9142 | DELETE | conn.Execute "delete from deuda_temp where id_usuario = " & … |
| Visualiza.bas | 7375 | SELECT | conn.Execute "delete from deuda_temp where id_usuario = " & … |
| Visualiza.bas | 7375 | DELETE | conn.Execute "delete from deuda_temp where id_usuario = " & … |
| Visualiza.bas | 7928 | SELECT | Visualiza_OrdenPago.data_mp_temp.RecordSource = "SELECT * FR… |
| Visualiza.bas | 7948 | SELECT | Visualiza_OrdenPago.data_mp_temp.RecordSource = "SELECT * FR… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)