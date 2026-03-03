# Tabla `en_detalle_abm_art_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_detalle_abm_art_temp | DOUBLE | No | ✓ |  |  |
| id_en_detalle_abm | DOUBLE | Sí |  |  |  |
| IDArt | DOUBLE | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |

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
| En_abm.frm | 1349 | SELECT | rs.Open "SELECT * FROM en_detalle_abm_art_temp WHERE IDArt I… |
| En_abm.frm | 1389 | INSERT | conn.Execute "INSERT INTO en_detalle_abm_art_temp (id_en_det… |
| En_CargaRef.frm | 918 | SELECT | "FROM en_detalle_abm_art_temp " & _ |
| En_CargaRef.frm | 930 | INSERT | conn.Execute "INSERT INTO en_detalle_abm_art_temp (id_en_det… |
| En_CargaRef.frm | 940 | SELECT | "FROM en_detalle_abm_art_temp " & _ |
| En_CargaRef.frm | 1038 | INSERT | conn.Execute "INSERT INTO en_detalle_abm_art_temp (idArt, id… |
| En_CargaRef.frm | 1112 | SELECT | rs.Open "SELECT * FROM en_detalle_abm_art_temp WHERE IDArt =… |
| En_CargaRef.frm | 1141 | INSERT | conn.Execute "INSERT INTO en_detalle_abm_art_temp (id_en_det… |
| En_CargaRef.frm | 1163 | SELECT | conn.Execute "DELETE FROM en_detalle_abm_art_temp WHERE id_e… |
| En_CargaRef.frm | 1163 | DELETE | conn.Execute "DELETE FROM en_detalle_abm_art_temp WHERE id_e… |
| En_CargaRef.frm | 1273 | SELECT | "SELECT " & rs_Ref.Fields!id_en_detalle_abm & ", IDArt FROM … |
| En_CargaRef.frm | 1346 | SELECT | "FROM en_detalle_abm_art_temp " & _ |
| En_CargaRef.frm | 1447 | SELECT | conn.Execute "delete from en_detalle_abm_art_temp where id_u… |
| En_CargaRef.frm | 1447 | DELETE | conn.Execute "delete from en_detalle_abm_art_temp where id_u… |
| Principal.frm | 6110 | SELECT | conn.Execute "delete from en_detalle_abm_art_temp where id_u… |
| Principal.frm | 6110 | DELETE | conn.Execute "delete from en_detalle_abm_art_temp where id_u… |
| Principal.frm | 6176 | SELECT | conn.Execute "delete from en_detalle_abm_art_temp where id_u… |
| Principal.frm | 6176 | DELETE | conn.Execute "delete from en_detalle_abm_art_temp where id_u… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)