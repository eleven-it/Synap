# Tabla `cont_asiento_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_asiento_temp | DOUBLE | No | ✓ |  |  |
| nro_asiento_temp | DOUBLE | Sí |  |  |  |
| fecha_asiento_temp | DATE | Sí |  |  |  |
| id_ejercicio_temp | DOUBLE | Sí |  |  |  |
| id_periodo_temp | DOUBLE | Sí |  |  |  |
| codigo_movimiento_temp | DOUBLE | Sí |  |  |  |
| debe_asiento_temp | DECIMAL | Sí |  |  |  |
| haber_asiento_temp | DECIMAL | Sí |  |  |  |
| saldo_asiento_temp | DECIMAL | Sí |  |  |  |
| id_pc_temp | DOUBLE | Sí |  |  |  |
| desc_asiento_renglon_temp | VARCHAR | Sí |  |  |  |
| desc_asiento_concepto_temp | VARCHAR | Sí |  |  |  |
| id_concepto_asiento_temp | DOUBLE | Sí |  |  |  |
| balanceado_asiento_temp | VARCHAR | Sí |  |  |  |
| id_usuario_temp | DOUBLE | Sí |  |  |  |
| cod_pc_temp | VARCHAR | Sí |  |  |  |
| codjer_pc_temp | VARCHAR | Sí |  |  |  |
| descripcion_pc_temp | VARCHAR | Sí |  |  |  |
| saldo_pc_temp | VARCHAR | Sí |  |  |  |
| dh_pa_temp | VARCHAR | Sí |  |  |  |
| id_pa_temp | DOUBLE | Sí |  |  |  |
| asig_cc_temp | VARCHAR | Sí |  |  |  |
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
| Cont_ListaCtaCont.frm | 746 | SELECT | rs_recupero.Open "SELECT * from cont_asiento_temp where id_u… |
| Cont_ListaCtaCont.frm | 899 | SELECT | rs_renglon.Open "SELECT * FROM cont_asiento_temp ", conn, ad… |
| Cont_ListaCtaCont.frm | 985 | SELECT | Cont_CargaAsientoM.DataAsientoCont.RecordSource = "select co… |
| Cont_ListaCtaCont.frm | 1001 | SELECT | rs_renglon.Open "SELECT * FROM cont_asiento_temp WHERE id_as… |
| Cont_ListaCtaCont.frm | 1190 | SELECT | rs_calculosaldo.Open "SELECT SUM(debe_asiento_temp) as total… |
| Cont_ListaPA.frm | 749 | SELECT | 'conn.Execute "DELETE FROM cont_asiento_temp WHERE id_usuari… |
| Cont_ListaPA.frm | 749 | DELETE | 'conn.Execute "DELETE FROM cont_asiento_temp WHERE id_usuari… |
| Cont_ListaPA.frm | 770 | SELECT | rs_ContAsientoTemp.Open "SELECT * from cont_asiento_temp whe… |
| Cont_ListaPA.frm | 831 | SELECT | Cont_CargaAsientoM.DataAsientoCont.RecordSource = "select co… |
| Visualiza_Cont_CargaAsientoM.frm | 2441 | SELECT | DataAsientoCont.RecordSource = "select cont_asiento_temp.* ,… |
| Visualiza_Cont_CargaAsientoM.frm | 2591 | SELECT | DataAsientoCont.RecordSource = "select * from cont_asiento_t… |
| Visualiza_Cont_CargaAsientoM.frm | 2654 | SELECT | DataAsientoCont.RecordSource = "select cont_asiento_temp.* ,… |
| Visualiza_Cont_CargaAsientoM.frm | 2680 | SELECT | conn.Execute "DELETE FROM cont_asiento_temp WHERE id_usuario… |
| Visualiza_Cont_CargaAsientoM.frm | 2680 | DELETE | conn.Execute "DELETE FROM cont_asiento_temp WHERE id_usuario… |
| Visualiza_Cont_CargaAsientoM.frm | 2707 | SELECT | rs_calculosaldo.Open "SELECT SUM(debe_asiento_temp) as total… |
| Visualiza_Cont_CargaAsientoM.frm | 2831 | SELECT | DataAsientoCont.RecordSource = "select * from cont_asiento_t… |
| Visualiza_Cont_CargaAsientoM.frm | 2905 | SELECT | DataAsientoCont.RecordSource = "select cont_asiento_temp.*, … |
| Cont_CargaAsientoM.frm | 1439 | SELECT | rs_valid.Open "SELECT * FROM cont_asiento_temp " & _ |
| Cont_CargaAsientoM.frm | 2093 | UPDATE | conn.Execute "UPDATE cont_asiento_temp " & _ |
| Cont_CargaAsientoM.frm | 2944 | SELECT | DataAsientoCont.RecordSource = "select cont_asiento_temp.* ,… |
| Cont_CargaAsientoM.frm | 3106 | SELECT | DataAsientoCont.RecordSource = "select * from cont_asiento_t… |
| Cont_CargaAsientoM.frm | 3169 | SELECT | DataAsientoCont.RecordSource = "select cont_asiento_temp.* ,… |
| Cont_CargaAsientoM.frm | 3194 | SELECT | conn.Execute "DELETE FROM cont_asiento_temp WHERE id_usuario… |
| Cont_CargaAsientoM.frm | 3194 | DELETE | conn.Execute "DELETE FROM cont_asiento_temp WHERE id_usuario… |
| Cont_CargaAsientoM.frm | 3224 | SELECT | rs_calculosaldo.Open "SELECT SUM(debe_asiento_temp) as total… |
| Cont_CargaAsientoM.frm | 3345 | SELECT | DataAsientoCont.RecordSource = "select * from cont_asiento_t… |
| Cont_CargaAsientoM.frm | 3424 | SELECT | DataAsientoCont.RecordSource = "select cont_asiento_temp.*, … |
| Principal.frm | 6072 | SELECT | conn.Execute "delete from cont_asiento_temp where id_usuario… |
| Principal.frm | 6072 | DELETE | conn.Execute "delete from cont_asiento_temp where id_usuario… |
| Principal.frm | 6138 | SELECT | conn.Execute "delete from cont_asiento_temp where id_usuario… |
| Principal.frm | 6138 | DELETE | conn.Execute "delete from cont_asiento_temp where id_usuario… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)