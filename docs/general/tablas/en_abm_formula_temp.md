# Tabla `en_abm_formula_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_abm_formula_temp | DOUBLE | No | ✓ |  |  |
| id_en_abm_temp | DOUBLE | Sí |  |  |  |
| id_articulo_temp | DOUBLE | Sí |  |  |  |
| cantidad_articulo_temp | DECIMAL | Sí |  |  |  |
| anulado_temp | VARCHAR | Sí |  |  |  |
| NombreArticulo_temp | VARCHAR | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| id_articulo_manual_temp | VARCHAR | Sí |  |  |  |
| tipo_unidad | VARCHAR | Sí |  |  |  |
| cantidad_unidad_display | DOUBLE | Sí |  |  |  |
| cantidad_dividir | DOUBLE | Sí |  |  |  |

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
| En_abm.frm | 1116 | INSERT | sqlFormulaEnsamb = "INSERT INTO en_abm_formula_temp(NombreAr… |
| En_abm.frm | 1154 | SELECT | '                    rs_temp.Open "SELECT * FROM en_abm_form… |
| En_abm.frm | 1192 | SELECT | '                    En_abmDef.DataGrid.RecordSource = "SELE… |
| En_abm.frm | 1197 | SELECT | " FROM en_abm_formula_temp " & _ |
| En_abmDef.frm | 863 | SELECT | rs_en_abm_formula_temp.Open "SELECT * FROM en_abm_formula_te… |
| En_abmDef.frm | 1093 | SELECT | DataGrid.RecordSource = "SELECT * FROM en_abm_formula_temp W… |
| En_abmDef.frm | 1126 | SELECT | " FROM en_abm_formula_temp " & _ |
| En_abmDef.frm | 1174 | SELECT | " FROM en_abm_formula_temp " & _ |
| En_abmDef.frm | 1233 | SELECT | conn.Execute "DELETE FROM en_abm_formula_temp WHERE id_en_ab… |
| En_abmDef.frm | 1233 | DELETE | conn.Execute "DELETE FROM en_abm_formula_temp WHERE id_en_ab… |
| En_abmDef.frm | 1448 | SELECT | conn.Execute "delete from en_abm_formula_temp where id_usuar… |
| En_abmDef.frm | 1448 | DELETE | conn.Execute "delete from en_abm_formula_temp where id_usuar… |
| En_abmDef.frm | 1565 | SELECT | rs_en_abm_formula_temp.Open "SELECT * FROM en_abm_formula_te… |
| En_abm2.frm | 796 | SELECT | rs_temp.Open "SELECT * FROM en_abm_formula_temp WHERE id_en_… |
| En_abm2.frm | 829 | SELECT | En_abmDef.DataGrid.RecordSource = "SELECT * from en_abm_form… |
| Principal.frm | 6108 | SELECT | conn.Execute "delete from en_abm_formula_temp where id_usuar… |
| Principal.frm | 6108 | DELETE | conn.Execute "delete from en_abm_formula_temp where id_usuar… |
| Principal.frm | 6174 | SELECT | conn.Execute "delete from en_abm_formula_temp where id_usuar… |
| Principal.frm | 6174 | DELETE | conn.Execute "delete from en_abm_formula_temp where id_usuar… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)