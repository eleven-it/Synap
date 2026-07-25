# Tabla `en_poe`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_poe | DOUBLE | No | ✓ |  |  |
| codigo_movimiento_poe | DOUBLE | Sí |  |  |  |
| codigo_movimiento_oe | DOUBLE | Sí |  |  |  |
| id_en_detalle_abm | DOUBLE | Sí |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| IDArtE | DOUBLE | Sí |  |  |  |
| id_proveedor | DOUBLE | Sí |  |  |  |
| id_en_abm | DOUBLE | Sí |  |  |  |
| cantidad | DOUBLE | Sí |  |  |  |
| nro_comp | VARCHAR | Sí |  |  |  |
| nro_comp_busq | INT | Sí |  |  |  |
| fecha_poe | DATE | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_en_detalle | DOUBLE | Sí |  |  |  |

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
| ConsultaComprobante.frm | 3304 | SELECT | "From en_poe " & _ |
| ConsultaComprobante.frm | 3322 | SELECT | "From en_poe " & _ |
| ConsultaComprobante.frm | 29506 | SELECT | rs_anul.Open "SELECT anulado FROM en_poe WHERE codigo_movimi… |
| ConsultaComprobante.frm | 29544 | JOIN | "LEFT JOIN en_poe ON (en_poe.codigo_movimiento_oe = stock.Co… |
| ConsultaComprobante.frm | 29549 | SELECT | "FROM en_poe WHERE en_poe.codigo_movimiento_poe = " & DataCo… |
| ConsultaComprobante.frm | 29740 | UPDATE | conn.Execute "UPDATE en_poe " & _ |
| ConsultaComprobante.frm | 29746 | JOIN | "LEFT JOIN en_poe ON (en_poe.codigo_movimiento_oe = en_detal… |
| En_GeneraPOE.frm | 1370 | SELECT | "FROM en_poe WHERE en_poe.codigo_movimiento_poe = " & CodMov… |
| En_GeneraPOE.frm | 1411 | SELECT | "FROM en_poe WHERE en_poe.codigo_movimiento_poe = " & CodMov… |
| En_GeneraPOE.frm | 1434 | SELECT | "FROM en_poe WHERE en_poe.codigo_movimiento_poe = " & CodMov… |
| En_GeneraPOE.frm | 1438 | INSERT | conn.Execute "INSERT INTO en_poe (codigo_movimiento_poe, id_… |
| En_GeneraPOE.frm | 1448 | SELECT | "FROM en_poe WHERE en_poe.codigo_movimiento_poe = " & CodMov… |
| En_GeneraPOE.frm | 1480 | UPDATE | conn.Execute "UPDATE en_poe  " & _ |
| En_GeneraPOE.frm | 1551 | JOIN | "RIGHT JOIN en_poe ON (en_poe.codigo_movimiento_oe = en_deta… |
| En_GeneraPOE.frm | 1584 | JOIN | "RIGHT JOIN en_poe ON (en_poe.codigo_movimiento_oe = en_deta… |
| En_GeneraPOE.frm | 1606 | SELECT | conn.Execute "DELETE FROM en_poe " & _ |
| En_GeneraPOE.frm | 1606 | DELETE | conn.Execute "DELETE FROM en_poe " & _ |
| En_GeneraPOE.frm | 1844 | INSERT | conn.Execute "INSERT INTO en_poe (codigo_movimiento_poe, id_… |
| En_GeneraPOE.frm | 2674 | SELECT | "From en_poe " & _ |
| Principal.frm | 11980 | SELECT | "FROM en_poe " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)