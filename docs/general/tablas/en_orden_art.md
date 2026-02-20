# Tabla `en_orden_art`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_orden_art | DOUBLE | No | ✓ |  |  |
| codigo_movimiento | DOUBLE | Sí |  |  |  |
| id_articulo | DOUBLE | Sí |  |  |  |
| cantidad | DECIMAL | Sí |  |  |  |
| id_en_abm | DOUBLE | Sí |  |  |  |
| cantidadFinal | DECIMAL | Sí |  |  |  |
| id_lote | DOUBLE | Sí |  |  |  |
| cod_lote | VARCHAR | Sí |  |  |  |
| vto_lote | DATE | Sí |  |  |  |
| Lote | VARCHAR | Sí |  |  |  |
| desc_stock | VARCHAR | Sí |  |  |  |

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
| En_GeneraOE.frm | 3403 | SELECT | rs_Art.Open "SELECT * FROM en_orden_art WHERE id_en_orden_ar… |
| En_GestionOE.frm | 1258 | SELECT | rs_imp.Open "SELECT * FROM en_orden_art WHERE codigo_movimie… |
| En_GestionOE.frm | 1297 | SELECT | rs_imp.Open "SELECT * FROM en_orden_art WHERE codigo_movimie… |
| En_GestionOE.frm | 1641 | SELECT | rs_Oart.Open "SELECT en_orden_art.*, articulo.NombreArticulo… |
| Visualiza_En_GeneraOE.frm | 4275 | UPDATE | '            conn.Execute "UPDATE en_orden_art " & _ |
| Visualiza_En_GeneraOE.frm | 4523 | SELECT | conn.Execute "DELETE FROM en_orden_art WHERE codigo_movimien… |
| Visualiza_En_GeneraOE.frm | 4523 | DELETE | conn.Execute "DELETE FROM en_orden_art WHERE codigo_movimien… |
| Visualiza_En_GeneraOE.frm | 4537 | SELECT | rs_Art.Open "SELECT * FROM en_orden_art WHERE id_en_orden_ar… |
| Visualiza_En_GeneraOE.frm | 5333 | SELECT | rs_cantArtP.Open "SELECT * From en_orden_art WHERE codigo_mo… |
| Visualiza_En_GeneraOE.frm | 5724 | SELECT | "FROM en_orden_art " & _ |
| En_GeneraPOE.frm | 1364 | JOIN | "LEFT JOIN en_orden_art ON (en_orden_art.codigo_movimiento =… |
| En_GeneraPOE.frm | 1403 | UPDATE | conn.Execute "UPDATE en_orden_art " & _ |
| En_GeneraPOE.frm | 1567 | UPDATE | conn.Execute "UPDATE en_orden_art " & _ |
| En_GeneraPOE.frm | 1778 | JOIN | "LEFT JOIN en_orden_art ON (en_orden_art.codigo_movimiento =… |
| En_GeneraPOE.frm | 1814 | UPDATE | conn.Execute "UPDATE en_orden_art " & _ |
| En_GeneraPOE.frm | 1896 | JOIN | "LEFT JOIN en_orden_art ON (en_orden_art.codigo_movimiento =… |
| En_GeneraPOE.frm | 1932 | UPDATE | conn.Execute "UPDATE en_orden_art " & _ |
| En_GeneraPOE.frm | 1980 | SELECT | rs_imp.Open "SELECT * FROM en_orden_art WHERE codigo_movimie… |
| Visualiza.bas | 8213 | SELECT | rs_Oart.Open "SELECT en_orden_art.*, articulo.NombreArticulo… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)