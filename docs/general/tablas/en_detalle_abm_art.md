# Tabla `en_detalle_abm_art`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_detalle_abm_art | DOUBLE | No | ✓ |  |  |
| id_en_detalle_abm | DOUBLE | Sí |  |  |  |
| IDArt | DOUBLE | Sí |  |  |  |
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
| En_GeneraOE.frm | 3366 | JOIN | "INNER JOIN en_detalle_abm_art ON (en_detalle_abm_art.id_en_… |
| En_GeneraOE.frm | 3451 | JOIN | "INNER JOIN en_detalle_abm_art ON (en_detalle_abm_art.id_en_… |
| En_GeneraOE.frm | 4759 | JOIN | "INNER JOIN en_detalle_abm_art ON (en_detalle_abm_art.id_en_… |
| En_abm.frm | 1364 | SELECT | rs.Open "SELECT * FROM en_detalle_abm_art WHERE IDArt IN (" … |
| Visualiza_En_GeneraOE.frm | 4276 | JOIN | "LEFT JOIN en_detalle_abm_art ON (en_detalle_abm_art.IDArt =… |
| Visualiza_En_GeneraOE.frm | 4283 | JOIN | "LEFT JOIN en_detalle_abm_art ON (en_detalle_abm_art.IDArt =… |
| Visualiza_En_GeneraOE.frm | 4497 | JOIN | "INNER JOIN en_detalle_abm_art ON (en_detalle_abm_art.id_en_… |
| Visualiza_En_GeneraOE.frm | 4605 | JOIN | "INNER JOIN en_detalle_abm_art ON (en_detalle_abm_art.id_en_… |
| Visualiza_En_GeneraOE.frm | 4891 | SELECT | '                                        "From en_detalle_ab… |
| Visualiza_En_GeneraOE.frm | 4911 | SELECT | "From en_detalle_abm_art " & _ |
| Visualiza_En_GeneraOE.frm | 5774 | JOIN | "INNER JOIN en_detalle_abm_art ON (en_detalle_abm_art.id_en_… |
| En_GeneraPOE.frm | 1351 | JOIN | "LEFT JOIN en_detalle_abm_art ON (en_detalle_abm_art.id_en_d… |
| En_GeneraPOE.frm | 1539 | JOIN | '                            "LEFT JOIN en_detalle_abm_art O… |
| En_GeneraPOE.frm | 1568 | JOIN | "LEFT JOIN en_detalle_abm_art ON (en_detalle_abm_art.IDArt =… |
| En_GeneraPOE.frm | 1765 | JOIN | "LEFT JOIN en_detalle_abm_art ON (en_detalle_abm_art.id_en_d… |
| En_GeneraPOE.frm | 1883 | JOIN | "LEFT JOIN en_detalle_abm_art ON (en_detalle_abm_art.id_en_d… |
| En_GeneraPOE.frm | 3272 | SELECT | "From en_detalle_abm_art " & _ |
| En_CargaRef.frm | 932 | SELECT | "FROM en_detalle_abm_art " & _ |
| En_CargaRef.frm | 1041 | SELECT | "NOT IN(SELECT en_detalle_abm_art.IDArt FROM en_detalle_abm_… |
| En_CargaRef.frm | 1128 | SELECT | rs.Open "SELECT * FROM en_detalle_abm_art WHERE IDArt = " & … |
| En_CargaRef.frm | 1269 | INSERT | '                conn.Execute "INSERT INTO en_detalle_abm_ar… |
| En_CargaRef.frm | 1272 | INSERT | conn.Execute "INSERT INTO en_detalle_abm_art (id_en_detalle_… |
| En_CargaRef.frm | 1341 | SELECT | conn.Execute "delete from en_detalle_abm_art where id_en_det… |
| En_CargaRef.frm | 1341 | DELETE | conn.Execute "delete from en_detalle_abm_art where id_en_det… |
| En_CargaRef.frm | 1344 | INSERT | conn.Execute "INSERT INTO en_detalle_abm_art (id_en_detalle_… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)