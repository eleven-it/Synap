# Tabla `ingreso_op_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_ingreso_temp | DOUBLE | No | ✓ |  |  |
| id_ingreso_abm | DOUBLE | Sí |  |  |  |
| id_ingreso | DOUBLE | Sí |  |  |  |
| fecha_ingreso_temp | DATE | Sí |  |  |  |
| nombre_ingreso_temp | VARCHAR | Sí |  |  |  |
| fecha_emision_ingreso_temp | DATE | Sí |  |  |  |
| fecha_vencimiento_ingreso_temp | DATE | Sí |  |  |  |
| nro_ingreso_temp | VARCHAR | Sí |  |  |  |
| importe_ingreso_temp | DECIMAL | Sí |  |  |  |
| detalle_ingreso_temp | VARCHAR | Sí |  |  |  |
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
| OrdenPago.frm | 9754 | SELECT | conn.Execute "DELETE FROM ingreso_op_temp WHERE id_ingreso_t… |
| OrdenPago.frm | 9754 | DELETE | conn.Execute "DELETE FROM ingreso_op_temp WHERE id_ingreso_t… |
| OrdenPago.frm | 9757 | SELECT | data_ingreso_temp.RecordSource = "SELECT * FROM ingreso_op_t… |
| OrdenPago.frm | 9769 | SELECT | rs_total_ingreso.Open "SELECT SUM(importe_ingreso_temp) as t… |
| OrdenPago.frm | 12554 | SELECT | conn.Execute "delete from ingreso_op_temp where id_usuario =… |
| OrdenPago.frm | 12554 | DELETE | conn.Execute "delete from ingreso_op_temp where id_usuario =… |
| OrdenPago.frm | 12756 | SELECT | rs_total_ingreso.Open "SELECT SUM(importe_ingreso_temp) as i… |
| OrdenPago.frm | 12770 | SELECT | data_ingreso_temp.RecordSource = "SELECT * FROM ingreso_op_t… |
| Lista_Ingresos.frm | 667 | SELECT | rs_validacion.Open "SELECT * FROM ingreso_op_temp WHERE " & … |
| Lista_Ingresos.frm | 683 | SELECT | OrdenPago.data_ingreso_temp.RecordSource = "SELECT * FROM in… |
| trz_trazabilidadComp.frm | 4715 | SELECT | conn.Execute "delete from ingreso_op_temp where id_usuario =… |
| trz_trazabilidadComp.frm | 4715 | DELETE | conn.Execute "delete from ingreso_op_temp where id_usuario =… |
| trz_trazabilidadComp.frm | 5138 | SELECT | Visualiza_OrdenPago.data_ingreso_temp.RecordSource = "SELECT… |
| trz_trazabilidadComp.frm | 5158 | SELECT | Visualiza_OrdenPago.data_ingreso_temp.RecordSource = "SELECT… |
| Visualiza_OrdenPagoC.frm | 6884 | SELECT | conn.Execute "DELETE FROM ingreso_op_temp WHERE id_ingreso_t… |
| Visualiza_OrdenPagoC.frm | 6884 | DELETE | conn.Execute "DELETE FROM ingreso_op_temp WHERE id_ingreso_t… |
| Visualiza_OrdenPagoC.frm | 6887 | SELECT | data_ingreso_temp.RecordSource = "SELECT * FROM ingreso_op_t… |
| Visualiza_OrdenPagoC.frm | 6899 | SELECT | rs_total_ingreso.Open "SELECT SUM(importe_ingreso_temp) as t… |
| Visualiza_OrdenPagoC.frm | 8763 | SELECT | conn.Execute "delete from ingreso_op_temp where id_usuario =… |
| Visualiza_OrdenPagoC.frm | 8763 | DELETE | conn.Execute "delete from ingreso_op_temp where id_usuario =… |
| Visualiza_OrdenPagoC.frm | 8951 | SELECT | rs_total_ingreso.Open "SELECT SUM(importe_ingreso_temp) as i… |
| Visualiza_OrdenPagoC.frm | 8965 | SELECT | data_ingreso_temp.RecordSource = "SELECT * FROM ingreso_op_t… |
| CuentaProveedor.frm | 1569 | SELECT | '                Visualiza_OrdenPago.data_ingreso_temp.Recor… |
| CuentaProveedor.frm | 1588 | SELECT | '                Visualiza_OrdenPago.data_ingreso_temp.Recor… |
| Principal.frm | 6091 | SELECT | conn.Execute "delete from ingreso_op_temp where id_usuario =… |
| Principal.frm | 6091 | DELETE | conn.Execute "delete from ingreso_op_temp where id_usuario =… |
| Principal.frm | 6157 | SELECT | conn.Execute "delete from ingreso_op_temp where id_usuario =… |
| Principal.frm | 6157 | DELETE | conn.Execute "delete from ingreso_op_temp where id_usuario =… |
| Visualiza_OrdenPago.frm | 7172 | SELECT | conn.Execute "DELETE FROM ingreso_op_temp WHERE id_ingreso_t… |
| Visualiza_OrdenPago.frm | 7172 | DELETE | conn.Execute "DELETE FROM ingreso_op_temp WHERE id_ingreso_t… |
| Visualiza_OrdenPago.frm | 7175 | SELECT | data_ingreso_temp.RecordSource = "SELECT * FROM ingreso_op_t… |
| Visualiza_OrdenPago.frm | 7187 | SELECT | rs_total_ingreso.Open "SELECT SUM(importe_ingreso_temp) as t… |
| Visualiza_OrdenPago.frm | 9144 | SELECT | conn.Execute "delete from ingreso_op_temp where id_usuario =… |
| Visualiza_OrdenPago.frm | 9144 | DELETE | conn.Execute "delete from ingreso_op_temp where id_usuario =… |
| Visualiza_OrdenPago.frm | 9332 | SELECT | rs_total_ingreso.Open "SELECT SUM(importe_ingreso_temp) as i… |
| Visualiza_OrdenPago.frm | 9346 | SELECT | data_ingreso_temp.RecordSource = "SELECT * FROM ingreso_op_t… |
| Visualiza.bas | 7377 | SELECT | conn.Execute "delete from ingreso_op_temp where id_usuario =… |
| Visualiza.bas | 7377 | DELETE | conn.Execute "delete from ingreso_op_temp where id_usuario =… |
| Visualiza.bas | 7891 | SELECT | Visualiza_OrdenPago.data_ingreso_temp.RecordSource = "SELECT… |
| Visualiza.bas | 7911 | SELECT | Visualiza_OrdenPago.data_ingreso_temp.RecordSource = "SELECT… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)