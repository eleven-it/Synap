# Tabla `cont_pa_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_pa_temp | DOUBLE | No | ✓ |  |  |
| desc_pa_temp | VARCHAR | Sí |  |  |  |
| id_concepto_asiento_temp | DOUBLE | Sí |  |  |  |
| id_pc_temp | DOUBLE | Sí |  |  |  |
| debe_asiento_temp | VARCHAR | Sí |  |  |  |
| haber_asiento_temp | VARCHAR | Sí |  |  |  |
| anulado_temp | VARCHAR | Sí |  |  |  |
| id_usuario_temp | DOUBLE | Sí |  |  |  |
| cod_pc_temp | VARCHAR | Sí |  |  |  |
| codjer_pc_temp | VARCHAR | Sí |  |  |  |
| descripcion_pc_temp | VARCHAR | Sí |  |  |  |

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
| Cont_ListaCtaCont.frm | 1099 | SELECT | rs_renglonPA.Open "SELECT * FROM cont_pa_temp where id_pa_te… |
| Cont_ListaCtaCont.frm | 1149 | SELECT | Cont_PA.DataPa.RecordSource = "select cont_pa_temp.* , SUBST… |
| Cont_ListaPA.frm | 671 | SELECT | rs_ContPaTemp.Open "SELECT * from cont_pa_temp where id_pa_t… |
| Cont_ListaPA.frm | 713 | SELECT | Cont_PA.DataPa.RecordSource = "select cont_pa_temp.* , SUBST… |
| Cont_PA.frm | 671 | SELECT | rs_balanceo.Open " SELECT COUNT(cont_pa_temp.debe_asiento_te… |
| Cont_PA.frm | 684 | SELECT | rs_balanceo.Open " SELECT COUNT(cont_pa_temp.haber_asiento_t… |
| Cont_PA.frm | 835 | SELECT | rs_balanceo.Open " SELECT COUNT(cont_pa_temp.debe_asiento_te… |
| Cont_PA.frm | 848 | SELECT | rs_balanceo.Open " SELECT COUNT(cont_pa_temp.haber_asiento_t… |
| Cont_PA.frm | 1009 | SELECT | DataPa.RecordSource = "select * from cont_pa_temp where " & … |
| Cont_PA.frm | 1025 | SELECT | DataPa.RecordSource = "select cont_pa_temp.* , SUBSTRING_IND… |
| Cont_PA.frm | 1128 | SELECT | DataPa.RecordSource = "select cont_pa_temp.* , SUBSTRING_IND… |
| Cont_PA.frm | 1224 | SELECT | conn.Execute "DELETE FROM cont_pa_temp WHERE id_usuario_temp… |
| Cont_PA.frm | 1224 | DELETE | conn.Execute "DELETE FROM cont_pa_temp WHERE id_usuario_temp… |
| Principal.frm | 6074 | SELECT | conn.Execute "delete from cont_pa_temp where id_usuario_temp… |
| Principal.frm | 6074 | DELETE | conn.Execute "delete from cont_pa_temp where id_usuario_temp… |
| Principal.frm | 6140 | SELECT | conn.Execute "delete from cont_pa_temp where id_usuario_temp… |
| Principal.frm | 6140 | DELETE | conn.Execute "delete from cont_pa_temp where id_usuario_temp… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)