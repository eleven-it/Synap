# Tabla `ingreso_temp`

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
| Visualiza_ReciboCobro.frm | 8053 | SELECT | data_ingreso_temp.RecordSource = "SELECT * FROM ingreso_temp… |
| Visualiza_ReciboCobro.frm | 8392 | SELECT | conn.Execute "DELETE FROM ingreso_temp WHERE id_ingreso_temp… |
| Visualiza_ReciboCobro.frm | 8392 | DELETE | conn.Execute "DELETE FROM ingreso_temp WHERE id_ingreso_temp… |
| Visualiza_ReciboCobro.frm | 10748 | SELECT | conn.Execute "delete from ingreso_temp where id_usuario = " … |
| Visualiza_ReciboCobro.frm | 10748 | DELETE | conn.Execute "delete from ingreso_temp where id_usuario = " … |
| Visualiza_ReciboCobro.frm | 15766 | SELECT | rs_total_ingreso.Open "SELECT SUM(importe_ingreso_temp) as i… |
| Visualiza_ReciboCobro.frm | 15780 | SELECT | data_ingreso_temp.RecordSource = "SELECT * FROM ingreso_temp… |
| CuentaCliente.frm | 2526 | SELECT | '                Visualiza_ReciboCobro.data_ingreso_temp.Rec… |
| CuentaCliente.frm | 2546 | SELECT | '                Visualiza_ReciboCobro.data_ingreso_temp.Rec… |
| trz_trazabilidad.frm | 7251 | SELECT | conn.Execute "delete from ingreso_temp where id_usuario = " … |
| trz_trazabilidad.frm | 7251 | DELETE | conn.Execute "delete from ingreso_temp where id_usuario = " … |
| trz_trazabilidad.frm | 7679 | SELECT | Visualiza_ReciboCobro.data_ingreso_temp.RecordSource = "SELE… |
| trz_trazabilidad.frm | 7720 | SELECT | Visualiza_ReciboCobro.data_ingreso_temp.RecordSource = "SELE… |
| Lista_Ingresos.frm | 625 | SELECT | rs_validacion.Open "SELECT * FROM ingreso_temp WHERE " & _ |
| Lista_MC.frm | 674 | SELECT | rs_validacion.Open "SELECT * FROM ingreso_temp WHERE " & _ |
| ReciboCobro.frm | 8449 | SELECT | data_ingreso_temp.RecordSource = "SELECT * FROM ingreso_temp… |
| ReciboCobro.frm | 8856 | SELECT | conn.Execute "DELETE FROM ingreso_temp WHERE id_ingreso_temp… |
| ReciboCobro.frm | 8856 | DELETE | conn.Execute "DELETE FROM ingreso_temp WHERE id_ingreso_temp… |
| ReciboCobro.frm | 11743 | SELECT | conn.Execute "delete from ingreso_temp where id_usuario = " … |
| ReciboCobro.frm | 11743 | DELETE | conn.Execute "delete from ingreso_temp where id_usuario = " … |
| ReciboCobro.frm | 16837 | SELECT | rs_total_ingreso.Open "SELECT SUM(importe_ingreso_temp) as i… |
| ReciboCobro.frm | 16851 | SELECT | data_ingreso_temp.RecordSource = "SELECT * FROM ingreso_temp… |
| Visualiza_ReciboCobroC.frm | 7819 | SELECT | data_ingreso_temp.RecordSource = "SELECT * FROM ingreso_temp… |
| Visualiza_ReciboCobroC.frm | 8158 | SELECT | conn.Execute "DELETE FROM ingreso_temp WHERE id_ingreso_temp… |
| Visualiza_ReciboCobroC.frm | 8158 | DELETE | conn.Execute "DELETE FROM ingreso_temp WHERE id_ingreso_temp… |
| Visualiza_ReciboCobroC.frm | 10405 | SELECT | conn.Execute "delete from ingreso_temp where id_usuario = " … |
| Visualiza_ReciboCobroC.frm | 10405 | DELETE | conn.Execute "delete from ingreso_temp where id_usuario = " … |
| Visualiza_ReciboCobroC.frm | 15383 | SELECT | rs_total_ingreso.Open "SELECT SUM(importe_ingreso_temp) as i… |
| Visualiza_ReciboCobroC.frm | 15397 | SELECT | data_ingreso_temp.RecordSource = "SELECT * FROM ingreso_temp… |
| Principal.frm | 6092 | SELECT | conn.Execute "delete from ingreso_temp where id_usuario = " … |
| Principal.frm | 6092 | DELETE | conn.Execute "delete from ingreso_temp where id_usuario = " … |
| Principal.frm | 6158 | SELECT | conn.Execute "delete from ingreso_temp where id_usuario = " … |
| Principal.frm | 6158 | DELETE | conn.Execute "delete from ingreso_temp where id_usuario = " … |
| Visualiza.bas | 6147 | SELECT | conn.Execute "delete from ingreso_temp where id_usuario = " … |
| Visualiza.bas | 6147 | DELETE | conn.Execute "delete from ingreso_temp where id_usuario = " … |
| Visualiza.bas | 6627 | SELECT | Visualiza_ReciboCobro.data_ingreso_temp.RecordSource = "SELE… |
| Visualiza.bas | 6668 | SELECT | Visualiza_ReciboCobro.data_ingreso_temp.RecordSource = "SELE… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)