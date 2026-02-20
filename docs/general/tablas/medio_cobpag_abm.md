# Tabla `medio_cobpag_abm`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_mcp_abm | DOUBLE | No | ✓ |  |  |
| id_mcp_tipo | DOUBLE | Sí |  |  |  |
| nombre_mcp_abm | VARCHAR | Sí |  |  |  |
| detalle_mcp_abm | VARCHAR | Sí |  |  |  |
| tipo_cp | VARCHAR | Sí |  |  |  |
| id_caja_ingreso | INT | Sí |  |  |  |
| id_caja_acum | INT | Sí |  |  |  |
| id_pc | INT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |

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
| Visualiza_ReciboCobro.frm | 7147 | SELECT | rs_caja_mc.Open "SELECT * FROM medio_cobpag_abm WHERE id_mcp… |
| Visualiza_ReciboCobro.frm | 7394 | SELECT | rs_caja_mc.Open "SELECT * FROM medio_cobpag_abm WHERE id_mcp… |
| Visualiza_ReciboCobro.frm | 9442 | SELECT | data_mc.RecordSource = "SELECT * FROM medio_cobpag_abm WHERE… |
| Visualiza_ReciboCobro.frm | 9480 | SELECT | data_medio_cobro.RecordSource = "SELECT * FROM medio_cobpag_… |
| Visualiza_ReciboCobro.frm | 9814 | SELECT | rs_consulta_mc.Open "SELECT medio_cobpag_abm.*,medio_cobpag_… |
| Visualiza_ReciboCobro.frm | 13901 | SELECT | rs_vect.Open "SELECT * from medio_cobpag_abm where id_mcp_ab… |
| Visualiza_ReciboCobro.frm | 14904 | SELECT | rs_vect.Open "SELECT * from medio_cobpag_abm where id_mcp_ab… |
| Visualiza_ReciboCobro.frm | 15069 | SELECT | rs_vect.Open "SELECT * from medio_cobpag_abm where id_mcp_ab… |
| OrdenPago.frm | 8053 | SELECT | rs_caja_consulta.Open "SELECT * FROM medio_cobpag_abm WHERE … |
| OrdenPago.frm | 13951 | SELECT | rs_vect.Open "SELECT * from medio_cobpag_abm where id_mcp_ab… |
| Carga_ABM_medio_cobpag.frm | 562 | SELECT | rs_medio_cobpag_abm.Open "SELECT * FROM medio_cobpag_abm WHE… |
| Carga_ABM_medio_cobpag.frm | 578 | SELECT | rs_medio_cobpag_abm.Open "SELECT * FROM medio_cobpag_abm WHE… |
| Carga_ABM_medio_cobpag.frm | 612 | SELECT | rs_medio_cobpag_abm.Open "SELECT * FROM medio_cobpag_abm WHE… |
| Lista_MC.frm | 859 | SELECT | data_mc_combo.RecordSource = "SELECT * FROM medio_cobpag_abm… |
| Visualiza_OrdenPagoC.frm | 9898 | SELECT | rs_vect.Open "SELECT * from medio_cobpag_abm where id_mcp_ab… |
| ReciboCobro.frm | 7644 | SELECT | rs_caja_mc.Open "SELECT * FROM medio_cobpag_abm WHERE id_mcp… |
| ReciboCobro.frm | 7892 | SELECT | rs_caja_mc.Open "SELECT * FROM medio_cobpag_abm WHERE id_mcp… |
| ReciboCobro.frm | 10132 | SELECT | data_mc.RecordSource = "SELECT * FROM medio_cobpag_abm WHERE… |
| ReciboCobro.frm | 10161 | SELECT | data_medio_cobro.RecordSource = "SELECT * FROM medio_cobpag_… |
| ReciboCobro.frm | 10668 | SELECT | rs_consulta_mc.Open "SELECT medio_cobpag_abm.*,medio_cobpag_… |
| ReciboCobro.frm | 14935 | SELECT | rs_vect.Open "SELECT * from medio_cobpag_abm where id_mcp_ab… |
| ReciboCobro.frm | 15952 | SELECT | rs_vect.Open "SELECT * from medio_cobpag_abm where id_mcp_ab… |
| ReciboCobro.frm | 16117 | SELECT | rs_vect.Open "SELECT * from medio_cobpag_abm where id_mcp_ab… |
| Visualiza_ReciboCobroC.frm | 6913 | SELECT | rs_caja_mc.Open "SELECT * FROM medio_cobpag_abm WHERE id_mcp… |
| Visualiza_ReciboCobroC.frm | 7160 | SELECT | rs_caja_mc.Open "SELECT * FROM medio_cobpag_abm WHERE id_mcp… |
| Visualiza_ReciboCobroC.frm | 9100 | SELECT | data_mc.RecordSource = "SELECT * FROM medio_cobpag_abm WHERE… |
| Visualiza_ReciboCobroC.frm | 9129 | SELECT | data_medio_cobro.RecordSource = "SELECT * FROM medio_cobpag_… |
| Visualiza_ReciboCobroC.frm | 9449 | SELECT | rs_consulta_mc.Open "SELECT medio_cobpag_abm.*,medio_cobpag_… |
| Visualiza_ReciboCobroC.frm | 13518 | SELECT | rs_vect.Open "SELECT * from medio_cobpag_abm where id_mcp_ab… |
| Visualiza_ReciboCobroC.frm | 14521 | SELECT | rs_vect.Open "SELECT * from medio_cobpag_abm where id_mcp_ab… |
| Visualiza_ReciboCobroC.frm | 14686 | SELECT | rs_vect.Open "SELECT * from medio_cobpag_abm where id_mcp_ab… |
| Visualiza_OrdenPago.frm | 10300 | SELECT | rs_vect.Open "SELECT * from medio_cobpag_abm where id_mcp_ab… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)