# Tabla `otro_egreso_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_oe_temp | INT | No | ✓ |  |  |
| nombre_oe_temp | VARCHAR | Sí |  |  |  |
| tipo_oe_temp | VARCHAR | Sí |  |  |  |
| importe_oe_temp | DECIMAL | Sí |  |  |  |
| id_impuesto | INT | Sí |  |  |  |
| id_impuesto_detalle | DOUBLE | Sí |  |  |  |
| id_gasto | INT | Sí |  |  |  |
| id_deuda | DOUBLE | Sí |  |  |  |
| id_deuda_abm | INT | Sí |  |  |  |
| detalle_oe | VARCHAR | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| id_percepcion | DOUBLE | Sí |  |  |  |
| importe_percepcion | DECIMAL | Sí |  |  |  |
| nombre_percepcion | VARCHAR | Sí |  |  |  |
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
| OrdenPago.frm | 9026 | SELECT | data_otro_egreso_temp.RecordSource = "SELECT * FROM otro_egr… |
| OrdenPago.frm | 9668 | SELECT | conn.Execute "DELETE FROM otro_egreso_temp WHERE id_oe_temp … |
| OrdenPago.frm | 9668 | DELETE | conn.Execute "DELETE FROM otro_egreso_temp WHERE id_oe_temp … |
| OrdenPago.frm | 9711 | SELECT | rs_detalle.Open "SELECT detalle_oe FROM otro_egreso_temp WHE… |
| OrdenPago.frm | 10326 | SELECT | data_otro_egreso_temp.RecordSource = "SELECT * FROM otro_egr… |
| OrdenPago.frm | 12551 | SELECT | conn.Execute "delete from otro_egreso_temp where id_usuario … |
| OrdenPago.frm | 12551 | DELETE | conn.Execute "delete from otro_egreso_temp where id_usuario … |
| OrdenPago.frm | 12681 | SELECT | rs_total_egreso.Open "SELECT SUM(importe_oe_temp) as importe… |
| OrdenPago.frm | 12695 | SELECT | data_otro_egreso_temp.RecordSource = "SELECT * FROM otro_egr… |
| OrdenPago.frm | 12796 | SELECT | rs_total_percepcion.Open "SELECT SUM(importe_percepcion) as … |
| OrdenPago.frm | 12806 | SELECT | data_otro_egreso_temp.RecordSource = "SELECT * FROM otro_egr… |
| trz_trazabilidadComp.frm | 4712 | SELECT | conn.Execute "delete from otro_egreso_temp where id_usuario … |
| trz_trazabilidadComp.frm | 4712 | DELETE | conn.Execute "delete from otro_egreso_temp where id_usuario … |
| trz_trazabilidadComp.frm | 5018 | SELECT | Visualiza_OrdenPago.data_otro_egreso_temp.RecordSource = "se… |
| trz_trazabilidadComp.frm | 5067 | SELECT | Visualiza_OrdenPago.data_otro_egreso_temp.RecordSource = "se… |
| Visualiza_OrdenPagoC.frm | 6448 | SELECT | data_otro_egreso_temp.RecordSource = "SELECT * FROM otro_egr… |
| Visualiza_OrdenPagoC.frm | 6855 | SELECT | conn.Execute "DELETE FROM otro_egreso_temp WHERE id_oe_temp … |
| Visualiza_OrdenPagoC.frm | 6855 | DELETE | conn.Execute "DELETE FROM otro_egreso_temp WHERE id_oe_temp … |
| Visualiza_OrdenPagoC.frm | 7370 | SELECT | data_otro_egreso_temp.RecordSource = "SELECT * FROM otro_egr… |
| Visualiza_OrdenPagoC.frm | 8760 | SELECT | conn.Execute "delete from otro_egreso_temp where id_usuario … |
| Visualiza_OrdenPagoC.frm | 8760 | DELETE | conn.Execute "delete from otro_egreso_temp where id_usuario … |
| Visualiza_OrdenPagoC.frm | 8889 | SELECT | rs_total_egreso.Open "SELECT SUM(importe_oe_temp) as importe… |
| Visualiza_OrdenPagoC.frm | 8903 | SELECT | data_otro_egreso_temp.RecordSource = "SELECT * FROM otro_egr… |
| Visualiza_OrdenPagoC.frm | 8982 | SELECT | rs_total_percepcion.Open "SELECT SUM(importe_percepcion) as … |
| Visualiza_OrdenPagoC.frm | 8992 | SELECT | data_otro_egreso_temp.RecordSource = "SELECT * FROM otro_egr… |
| imp_Gestion.frm | 1929 | SELECT | rs_validacion.Open "SELECT * FROM otro_egreso_temp WHERE " &… |
| Principal.frm | 6096 | SELECT | conn.Execute "delete from otro_egreso_temp where id_usuario … |
| Principal.frm | 6096 | DELETE | conn.Execute "delete from otro_egreso_temp where id_usuario … |
| Principal.frm | 6162 | SELECT | conn.Execute "delete from otro_egreso_temp where id_usuario … |
| Principal.frm | 6162 | DELETE | conn.Execute "delete from otro_egreso_temp where id_usuario … |
| Visualiza_OrdenPago.frm | 6712 | SELECT | data_otro_egreso_temp.RecordSource = "SELECT * FROM otro_egr… |
| Visualiza_OrdenPago.frm | 7143 | SELECT | conn.Execute "DELETE FROM otro_egreso_temp WHERE id_oe_temp … |
| Visualiza_OrdenPago.frm | 7143 | DELETE | conn.Execute "DELETE FROM otro_egreso_temp WHERE id_oe_temp … |
| Visualiza_OrdenPago.frm | 7662 | SELECT | data_otro_egreso_temp.RecordSource = "SELECT * FROM otro_egr… |
| Visualiza_OrdenPago.frm | 9141 | SELECT | conn.Execute "delete from otro_egreso_temp where id_usuario … |
| Visualiza_OrdenPago.frm | 9141 | DELETE | conn.Execute "delete from otro_egreso_temp where id_usuario … |
| Visualiza_OrdenPago.frm | 9270 | SELECT | rs_total_egreso.Open "SELECT SUM(importe_oe_temp) as importe… |
| Visualiza_OrdenPago.frm | 9284 | SELECT | data_otro_egreso_temp.RecordSource = "SELECT * FROM otro_egr… |
| Visualiza_OrdenPago.frm | 9363 | SELECT | rs_total_percepcion.Open "SELECT SUM(importe_percepcion) as … |
| Visualiza_OrdenPago.frm | 9373 | SELECT | data_otro_egreso_temp.RecordSource = "SELECT * FROM otro_egr… |
| Lista_Deuda.frm | 623 | SELECT | rs_validacion.Open "SELECT * FROM otro_egreso_temp WHERE " &… |
| Lista_Deuda.frm | 639 | SELECT | '    OrdenPago.data_otro_egreso_temp.RecordSource = "SELECT … |
| Visualiza.bas | 7374 | SELECT | conn.Execute "delete from otro_egreso_temp where id_usuario … |
| Visualiza.bas | 7374 | DELETE | conn.Execute "delete from otro_egreso_temp where id_usuario … |
| Visualiza.bas | 7771 | SELECT | Visualiza_OrdenPago.data_otro_egreso_temp.RecordSource = "se… |
| Visualiza.bas | 7820 | SELECT | Visualiza_OrdenPago.data_otro_egreso_temp.RecordSource = "se… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)