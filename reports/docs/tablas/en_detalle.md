# Tabla `en_detalle`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_detalle | DOUBLE | No | ✓ |  |  |
| codigo_movimiento | DOUBLE | Sí |  |  |  |
| id_en_detalle_abm | DOUBLE | Sí |  |  |  |
| desc_detalle | MEDIUMTEXT | Sí |  |  |  |
| fecha_en_detalle | DATE | Sí |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| estado_en_detalle | VARCHAR | Sí |  |  |  |
| IDArtE | DOUBLE | Sí |  |  |  |
| id_proveedor | DOUBLE | Sí |  |  |  |
| id_gasto | DOUBLE | Sí |  |  |  |
| monto | DECIMAL | Sí |  |  |  |
| id_en_abm | DOUBLE | Sí |  |  |  |

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
| En_GeneraOE.frm | 3511 | SELECT | rs_Det.Open "SELECT * FROM en_detalle WHERE id_en_detalle = … |
| En_GestionOE.frm | 789 | JOIN | "LEFT JOIN en_detalle ON (en_detalle.codigo_movimiento = en_… |
| En_GestionOE.frm | 815 | JOIN | "LEFT JOIN en_detalle ON (en_detalle.codigo_movimiento = en_… |
| En_GestionOE.frm | 828 | SELECT | "From en_detalle " & _ |
| En_GestionOE.frm | 850 | JOIN | '                            "RIGHT JOIN en_detalle ON (en_d… |
| En_GestionOE.frm | 1734 | SELECT | rs_Det.Open "SELECT * FROM en_detalle " & _ |
| ConsultaComprobante.frm | 3305 | JOIN | "LEFT JOIN en_detalle ON (en_detalle.codigo_movimiento = en_… |
| ConsultaComprobante.frm | 3323 | JOIN | "LEFT JOIN en_detalle ON (en_detalle.codigo_movimiento = en_… |
| ConsultaComprobante.frm | 29745 | SELECT | conn.Execute "DELETE en_detalle.* FROM en_detalle " & _ |
| Visualiza_En_GeneraOE.frm | 4663 | SELECT | conn.Execute "DELETE FROM en_detalle WHERE codigo_movimiento… |
| Visualiza_En_GeneraOE.frm | 4663 | DELETE | conn.Execute "DELETE FROM en_detalle WHERE codigo_movimiento… |
| Visualiza_En_GeneraOE.frm | 4671 | SELECT | rs_Det.Open "SELECT * FROM en_detalle WHERE id_en_detalle = … |
| En_GeneraPOE.frm | 1365 | JOIN | "LEFT JOIN en_detalle ON (en_detalle.codigo_movimiento = en_… |
| En_GeneraPOE.frm | 1405 | JOIN | "LEFT JOIN en_detalle ON (en_detalle.codigo_movimiento = en_… |
| En_GeneraPOE.frm | 1424 | INSERT | conn.Execute "INSERT INTO en_detalle (codigo_movimiento, id_… |
| En_GeneraPOE.frm | 1431 | JOIN | "LEFT JOIN en_detalle ON (en_detalle.codigo_movimiento = en_… |
| En_GeneraPOE.frm | 1456 | UPDATE | conn.Execute "UPDATE en_detalle " & _ |
| En_GeneraPOE.frm | 1512 | SELECT | '        conn.Execute "DELETE FROM en_detalle " & _ |
| En_GeneraPOE.frm | 1512 | DELETE | '        conn.Execute "DELETE FROM en_detalle " & _ |
| En_GeneraPOE.frm | 1550 | SELECT | "FROM en_detalle " & _ |
| En_GeneraPOE.frm | 1555 | SELECT | "From en_detalle As a " & _ |
| En_GeneraPOE.frm | 1583 | SELECT | conn.Execute "DELETE en_detalle.* FROM en_detalle " & _ |
| En_GeneraPOE.frm | 1658 | SELECT | rs_Ref.Open "SELECT * FROM en_detalle " & _ |
| En_GeneraPOE.frm | 1834 | INSERT | conn.Execute "INSERT INTO en_detalle (codigo_movimiento, id_… |
| En_GeneraPOE.frm | 1949 | INSERT | conn.Execute "INSERT INTO en_detalle (codigo_movimiento, id_… |
| En_GeneraPOE.frm | 2075 | SELECT | rs_Ref.Open "SELECT * FROM en_detalle " & _ |
| En_GeneraPOE.frm | 2459 | JOIN | "LEFT JOIN en_detalle ON (en_detalle.codigo_movimiento = en_… |
| En_GeneraPOE.frm | 2481 | JOIN | "LEFT JOIN en_detalle ON (en_detalle.codigo_movimiento = en_… |
| En_GeneraPOE.frm | 2494 | SELECT | "From en_detalle " & _ |
| En_GeneraPOE.frm | 2676 | JOIN | "LEFT JOIN en_detalle ON (en_detalle.codigo_movimiento = en_… |
| En_GeneraPOE.frm | 3521 | SELECT | "FROM en_detalle " & _ |
| En_GeneraPOE.frm | 3550 | JOIN | "LEFT JOIN en_detalle ON (en_detalle.id_en_detalle_abm = en_… |
| Principal.frm | 11982 | JOIN | "LEFT JOIN en_detalle ON (en_detalle.codigo_movimiento = en_… |
| Visualiza.bas | 8311 | SELECT | rs_Det.Open "SELECT * FROM en_detalle " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)