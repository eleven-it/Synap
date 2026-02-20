# Tabla `medio_cobpag_op_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_mcp_temp | DOUBLE | No | ✓ |  |  |
| id_mcp_abm | DOUBLE | Sí |  |  |  |
| fecha_mcp_temp | DATE | Sí |  |  |  |
| tipo_mcp_tipo_temp | VARCHAR | Sí |  |  |  |
| nombre_mcp_temp | VARCHAR | Sí |  |  |  |
| codigo_movimiento_rec | DOUBLE | Sí |  |  |  |
| fecha_emision_mcp_temp | DATE | Sí |  |  |  |
| fecha_vencimiento_mcp_temp | DATE | Sí |  |  |  |
| nro_mcp_temp | VARCHAR | Sí |  |  |  |
| importe_mcp_temp | DECIMAL | Sí |  |  |  |
| detalle_mcp_temp | VARCHAR | Sí |  |  |  |
| id_mcp_medio_cobpag | DOUBLE | Sí |  |  |  |
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
| OrdenPago.frm | 9812 | SELECT | conn.Execute "DELETE FROM medio_cobpag_op_temp WHERE id_mcp_… |
| OrdenPago.frm | 9812 | DELETE | conn.Execute "DELETE FROM medio_cobpag_op_temp WHERE id_mcp_… |
| OrdenPago.frm | 9815 | SELECT | data_mct_temp.RecordSource = "SELECT * FROM medio_cobpag_op_… |
| OrdenPago.frm | 9827 | SELECT | rs_total_mct.Open "SELECT SUM(importe_mcp_temp) as total_mct… |
| OrdenPago.frm | 12553 | SELECT | conn.Execute "delete from medio_cobpag_op_temp where id_usua… |
| OrdenPago.frm | 12553 | DELETE | conn.Execute "delete from medio_cobpag_op_temp where id_usua… |
| OrdenPago.frm | 12714 | SELECT | rs_total_mct.Open "SELECT SUM(importe_mcp_temp) as importe_m… |
| OrdenPago.frm | 12728 | SELECT | data_mct_temp.RecordSource = "SELECT * FROM medio_cobpag_op_… |
| Lista_MC.frm | 624 | SELECT | rs_validacion.Open "SELECT * FROM medio_cobpag_op_temp WHERE… |
| Lista_MC.frm | 640 | SELECT | OrdenPago.data_mct_temp.RecordSource = "SELECT * FROM medio_… |
| trz_trazabilidadComp.frm | 4714 | SELECT | conn.Execute "delete from medio_cobpag_op_temp where id_usua… |
| trz_trazabilidadComp.frm | 4714 | DELETE | conn.Execute "delete from medio_cobpag_op_temp where id_usua… |
| trz_trazabilidadComp.frm | 5100 | SELECT | Visualiza_OrdenPago.data_mct_temp.RecordSource = "SELECT * F… |
| trz_trazabilidadComp.frm | 5121 | SELECT | Visualiza_OrdenPago.data_mct_temp.RecordSource = "SELECT * F… |
| Visualiza_OrdenPagoC.frm | 6942 | SELECT | conn.Execute "DELETE FROM medio_cobpag_op_temp WHERE id_mcp_… |
| Visualiza_OrdenPagoC.frm | 6942 | DELETE | conn.Execute "DELETE FROM medio_cobpag_op_temp WHERE id_mcp_… |
| Visualiza_OrdenPagoC.frm | 6945 | SELECT | data_mct_temp.RecordSource = "SELECT * FROM medio_cobpag_op_… |
| Visualiza_OrdenPagoC.frm | 6957 | SELECT | rs_total_mct.Open "SELECT SUM(importe_mcp_temp) as total_mct… |
| Visualiza_OrdenPagoC.frm | 8762 | SELECT | conn.Execute "delete from medio_cobpag_op_temp where id_usua… |
| Visualiza_OrdenPagoC.frm | 8762 | DELETE | conn.Execute "delete from medio_cobpag_op_temp where id_usua… |
| Visualiza_OrdenPagoC.frm | 8920 | SELECT | rs_total_mct.Open "SELECT SUM(importe_mcp_temp) as importe_m… |
| Visualiza_OrdenPagoC.frm | 8934 | SELECT | data_mct_temp.RecordSource = "SELECT * FROM medio_cobpag_op_… |
| CuentaProveedor.frm | 1532 | SELECT | '                Visualiza_OrdenPago.data_mct_temp.RecordSou… |
| CuentaProveedor.frm | 1552 | SELECT | '                Visualiza_OrdenPago.data_mct_temp.RecordSou… |
| Principal.frm | 6094 | SELECT | conn.Execute "delete from medio_cobpag_op_temp where id_usua… |
| Principal.frm | 6094 | DELETE | conn.Execute "delete from medio_cobpag_op_temp where id_usua… |
| Principal.frm | 6160 | SELECT | conn.Execute "delete from medio_cobpag_op_temp where id_usua… |
| Principal.frm | 6160 | DELETE | conn.Execute "delete from medio_cobpag_op_temp where id_usua… |
| Visualiza_OrdenPago.frm | 7230 | SELECT | conn.Execute "DELETE FROM medio_cobpag_op_temp WHERE id_mcp_… |
| Visualiza_OrdenPago.frm | 7230 | DELETE | conn.Execute "DELETE FROM medio_cobpag_op_temp WHERE id_mcp_… |
| Visualiza_OrdenPago.frm | 7233 | SELECT | data_mct_temp.RecordSource = "SELECT * FROM medio_cobpag_op_… |
| Visualiza_OrdenPago.frm | 7245 | SELECT | rs_total_mct.Open "SELECT SUM(importe_mcp_temp) as total_mct… |
| Visualiza_OrdenPago.frm | 9143 | SELECT | conn.Execute "delete from medio_cobpag_op_temp where id_usua… |
| Visualiza_OrdenPago.frm | 9143 | DELETE | conn.Execute "delete from medio_cobpag_op_temp where id_usua… |
| Visualiza_OrdenPago.frm | 9301 | SELECT | rs_total_mct.Open "SELECT SUM(importe_mcp_temp) as importe_m… |
| Visualiza_OrdenPago.frm | 9315 | SELECT | data_mct_temp.RecordSource = "SELECT * FROM medio_cobpag_op_… |
| Visualiza.bas | 7376 | SELECT | conn.Execute "delete from medio_cobpag_op_temp where id_usua… |
| Visualiza.bas | 7376 | DELETE | conn.Execute "delete from medio_cobpag_op_temp where id_usua… |
| Visualiza.bas | 7853 | SELECT | Visualiza_OrdenPago.data_mct_temp.RecordSource = "SELECT * F… |
| Visualiza.bas | 7874 | SELECT | Visualiza_OrdenPago.data_mct_temp.RecordSource = "SELECT * F… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)