# Tabla `en_poe_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_poe_temp | DOUBLE | No | ✓ |  |  |
| codigo_movimiento | DOUBLE | Sí |  |  |  |
| id_en_detalle_abm_temp | DOUBLE | Sí |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| id_usuario_temp | DOUBLE | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| nombreReferencia_temp | VARCHAR | Sí |  |  |  |
| estado_en_detalle_temp | VARCHAR | Sí |  |  |  |
| IDArtE_temp | DOUBLE | Sí |  |  |  |
| id_en_abm_temp | DOUBLE | Sí |  |  |  |
| cantidad_temp | DOUBLE | Sí |  |  |  |
| nrocomp_oe_temp | VARCHAR | Sí |  |  |  |
| nombreArticulo_temp | VARCHAR | Sí |  |  |  |
| id_en_detalle_temp | DOUBLE | Sí |  |  |  |

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
| En_GeneraPOE.frm | 1363 | SELECT | "From en_poe_temp " & _ |
| En_GeneraPOE.frm | 1404 | JOIN | "LEFT JOIN en_poe_temp ON (en_poe_temp.codigo_movimiento = e… |
| En_GeneraPOE.frm | 1430 | SELECT | "From en_poe_temp " & _ |
| En_GeneraPOE.frm | 1445 | SELECT | "FROM en_poe_temp " & _ |
| En_GeneraPOE.frm | 1457 | JOIN | "INNER JOIN en_poe_temp ON " & _ |
| En_GeneraPOE.frm | 1481 | JOIN | "INNER JOIN en_poe_temp ON " & _ |
| En_GeneraPOE.frm | 1556 | JOIN | "Left Join en_poe_temp as b ON (a.codigo_movimiento = b.codi… |
| En_GeneraPOE.frm | 1659 | JOIN | "RIGHT JOIN en_poe_temp ON (en_poe_temp.codigo_movimiento = … |
| En_GeneraPOE.frm | 1777 | SELECT | "From en_poe_temp " & _ |
| En_GeneraPOE.frm | 1815 | JOIN | "LEFT JOIN en_poe_temp ON (en_poe_temp.codigo_movimiento = e… |
| En_GeneraPOE.frm | 1840 | SELECT | "FROM en_poe_temp " & _ |
| En_GeneraPOE.frm | 1851 | SELECT | "FROM en_poe_temp " & _ |
| En_GeneraPOE.frm | 1895 | SELECT | "From en_poe_temp " & _ |
| En_GeneraPOE.frm | 1933 | JOIN | "LEFT JOIN en_poe_temp ON (en_poe_temp.codigo_movimiento = e… |
| En_GeneraPOE.frm | 1955 | SELECT | "FROM en_poe_temp " & _ |
| En_GeneraPOE.frm | 2058 | SELECT | rs_existe.Open "SELECT codigo_movimiento, IDArtE_temp FROM e… |
| En_GeneraPOE.frm | 2104 | SELECT | DataComprobanteA.RecordSource = "SELECT * FROM en_poe_temp W… |
| En_GeneraPOE.frm | 2135 | SELECT | DataComprobanteA.RecordSource = "SELECT * From en_poe_temp W… |
| En_GeneraPOE.frm | 2184 | SELECT | rs_ultimo.Open "SELECT * FROM en_poe_temp WHERE id_usuario_t… |
| En_GeneraPOE.frm | 2199 | SELECT | conn.Execute "DELETE From en_poe_temp WHERE id_en_poe_temp =… |
| En_GeneraPOE.frm | 2199 | DELETE | conn.Execute "DELETE From en_poe_temp WHERE id_en_poe_temp =… |
| En_GeneraPOE.frm | 2213 | SELECT | conn.Execute "DELETE FROM en_poe_temp " & _ |
| En_GeneraPOE.frm | 2213 | DELETE | conn.Execute "DELETE FROM en_poe_temp " & _ |
| En_GeneraPOE.frm | 2219 | SELECT | DataComprobanteA.RecordSource = "SELECT * From en_poe_temp W… |
| En_GeneraPOE.frm | 2321 | INSERT | conn.Execute "INSERT INTO en_poe_temp (codigo_movimiento, ID… |
| En_GeneraPOE.frm | 2330 | SELECT | DataComprobanteA.RecordSource = "SELECT * From en_poe_temp W… |
| En_GeneraPOE.frm | 2669 | INSERT | conn.Execute "INSERT INTO en_poe_temp (codigo_movimiento, id… |
| En_GeneraPOE.frm | 2686 | SELECT | "FROM en_poe_temp WHERE id_usuario_temp = " & Principal.idUs… |
| En_GeneraPOE.frm | 2817 | SELECT | conn.Execute "delete from en_poe_temp where id_usuario_temp … |
| En_GeneraPOE.frm | 2817 | DELETE | conn.Execute "delete from en_poe_temp where id_usuario_temp … |
| Principal.frm | 6115 | SELECT | conn.Execute "delete from en_poe_temp where id_usuario = " &… |
| Principal.frm | 6115 | DELETE | conn.Execute "delete from en_poe_temp where id_usuario = " &… |
| Principal.frm | 6181 | SELECT | conn.Execute "delete from en_poe_temp where id_usuario = " &… |
| Principal.frm | 6181 | DELETE | conn.Execute "delete from en_poe_temp where id_usuario = " &… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)