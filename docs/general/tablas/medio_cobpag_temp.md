# Tabla `medio_cobpag_temp`

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
| Visualiza_ReciboCobro.frm | 7859 | SELECT | data_mc_temp.RecordSource = "SELECT * FROM medio_cobpag_temp… |
| Visualiza_ReciboCobro.frm | 7874 | SELECT | data_mc_temp.RecordSource = "SELECT * FROM medio_cobpag_temp… |
| Visualiza_ReciboCobro.frm | 7888 | SELECT | rs_total_mc.Open "SELECT SUM(importe_mcp_temp) as total_mc F… |
| Visualiza_ReciboCobro.frm | 8233 | SELECT | conn.Execute "DELETE FROM medio_cobpag_temp WHERE id_mcp_tem… |
| Visualiza_ReciboCobro.frm | 8233 | DELETE | conn.Execute "DELETE FROM medio_cobpag_temp WHERE id_mcp_tem… |
| Visualiza_ReciboCobro.frm | 8236 | SELECT | data_mc_temp.RecordSource = "SELECT * FROM medio_cobpag_temp… |
| Visualiza_ReciboCobro.frm | 8248 | SELECT | rs_total_mc.Open "SELECT SUM(importe_mcp_temp) as total_mc F… |
| Visualiza_ReciboCobro.frm | 10747 | SELECT | conn.Execute "delete from medio_cobpag_temp where id_usuario… |
| Visualiza_ReciboCobro.frm | 10747 | DELETE | conn.Execute "delete from medio_cobpag_temp where id_usuario… |
| CuentaCliente.frm | 2485 | SELECT | '                Visualiza_ReciboCobro.data_mc_temp.RecordSo… |
| CuentaCliente.frm | 2506 | SELECT | '                Visualiza_ReciboCobro.data_mc_temp.RecordSo… |
| trz_trazabilidad.frm | 7250 | SELECT | conn.Execute "delete from medio_cobpag_temp where id_usuario… |
| trz_trazabilidad.frm | 7250 | DELETE | conn.Execute "delete from medio_cobpag_temp where id_usuario… |
| trz_trazabilidad.frm | 7597 | SELECT | Visualiza_ReciboCobro.data_mc_temp.RecordSource = "SELECT * … |
| trz_trazabilidad.frm | 7618 | SELECT | Visualiza_ReciboCobro.data_mc_temp.RecordSource = "SELECT * … |
| ReciboCobro.frm | 8211 | SELECT | data_mc_temp.RecordSource = "SELECT * FROM medio_cobpag_temp… |
| ReciboCobro.frm | 8226 | SELECT | data_mc_temp.RecordSource = "SELECT * FROM medio_cobpag_temp… |
| ReciboCobro.frm | 8240 | SELECT | rs_total_mc.Open "SELECT SUM(importe_mcp_temp) as total_mc F… |
| ReciboCobro.frm | 8683 | SELECT | conn.Execute "DELETE FROM medio_cobpag_temp WHERE id_mcp_tem… |
| ReciboCobro.frm | 8683 | DELETE | conn.Execute "DELETE FROM medio_cobpag_temp WHERE id_mcp_tem… |
| ReciboCobro.frm | 8686 | SELECT | data_mc_temp.RecordSource = "SELECT * FROM medio_cobpag_temp… |
| ReciboCobro.frm | 8698 | SELECT | rs_total_mc.Open "SELECT SUM(importe_mcp_temp) as total_mc F… |
| ReciboCobro.frm | 11742 | SELECT | conn.Execute "delete from medio_cobpag_temp where id_usuario… |
| ReciboCobro.frm | 11742 | DELETE | conn.Execute "delete from medio_cobpag_temp where id_usuario… |
| Visualiza_ReciboCobroC.frm | 7625 | SELECT | data_mc_temp.RecordSource = "SELECT * FROM medio_cobpag_temp… |
| Visualiza_ReciboCobroC.frm | 7640 | SELECT | data_mc_temp.RecordSource = "SELECT * FROM medio_cobpag_temp… |
| Visualiza_ReciboCobroC.frm | 7654 | SELECT | rs_total_mc.Open "SELECT SUM(importe_mcp_temp) as total_mc F… |
| Visualiza_ReciboCobroC.frm | 7999 | SELECT | conn.Execute "DELETE FROM medio_cobpag_temp WHERE id_mcp_tem… |
| Visualiza_ReciboCobroC.frm | 7999 | DELETE | conn.Execute "DELETE FROM medio_cobpag_temp WHERE id_mcp_tem… |
| Visualiza_ReciboCobroC.frm | 8002 | SELECT | data_mc_temp.RecordSource = "SELECT * FROM medio_cobpag_temp… |
| Visualiza_ReciboCobroC.frm | 8014 | SELECT | rs_total_mc.Open "SELECT SUM(importe_mcp_temp) as total_mc F… |
| Visualiza_ReciboCobroC.frm | 10404 | SELECT | conn.Execute "delete from medio_cobpag_temp where id_usuario… |
| Visualiza_ReciboCobroC.frm | 10404 | DELETE | conn.Execute "delete from medio_cobpag_temp where id_usuario… |
| Principal.frm | 6095 | SELECT | conn.Execute "delete from medio_cobpag_temp where id_usuario… |
| Principal.frm | 6095 | DELETE | conn.Execute "delete from medio_cobpag_temp where id_usuario… |
| Principal.frm | 6161 | SELECT | conn.Execute "delete from medio_cobpag_temp where id_usuario… |
| Principal.frm | 6161 | DELETE | conn.Execute "delete from medio_cobpag_temp where id_usuario… |
| Visualiza.bas | 6146 | SELECT | conn.Execute "delete from medio_cobpag_temp where id_usuario… |
| Visualiza.bas | 6146 | DELETE | conn.Execute "delete from medio_cobpag_temp where id_usuario… |
| Visualiza.bas | 6545 | SELECT | Visualiza_ReciboCobro.data_mc_temp.RecordSource = "SELECT * … |
| Visualiza.bas | 6566 | SELECT | Visualiza_ReciboCobro.data_mc_temp.RecordSource = "SELECT * … |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)