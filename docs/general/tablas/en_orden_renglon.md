# Tabla `en_orden_renglon`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_orden_renglon | DOUBLE | No | ✓ |  |  |
| codigo_movimiento | DOUBLE | Sí |  |  |  |
| id_en_abm | DOUBLE | Sí |  |  |  |
| cantidad | DECIMAL | Sí |  |  |  |
| cantidadE | DECIMAL | Sí |  |  |  |
| id_lote | DOUBLE | Sí |  |  |  |
| cod_lote | VARCHAR | Sí |  |  |  |
| vto_lote | VARCHAR | Sí |  |  |  |
| Lote | VARCHAR | Sí |  |  |  |
| completo | VARCHAR | Sí |  |  |  |

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
| En_GeneraOE.frm | 3295 | SELECT | rs_EnOr.Open "SELECT * FROM en_orden_renglon WHERE id_en_ord… |
| En_GeneraOE.frm | 3823 | SELECT | rs_EnOrd.Open "SELECT * from en_orden_renglon " & _ |
| En_GestionOE.frm | 788 | SELECT | "FROM en_orden_renglon " & _ |
| En_GestionOE.frm | 814 | SELECT | "FROM en_orden_renglon " & _ |
| En_GestionOE.frm | 849 | SELECT | '                            "FROM en_orden_renglon " & _ |
| En_GestionOE.frm | 1559 | SELECT | rs_Orenglon.Open "SELECT en_orden_renglon.*, en_abm.nombre_e… |
| En_GestionOE.frm | 1643 | JOIN | "RIGHT OUTER JOIN en_orden_renglon ON (en_orden_renglon.codi… |
| En_CargaOE_ArtE.frm | 1367 | SELECT | rs_e.Open "SELECT * from en_orden_renglon WHERE codigo_movim… |
| Visualiza_En_GeneraOE.frm | 3526 | JOIN | "INNER JOIN en_orden_renglon ON(en_orden_renglon.codigo_movi… |
| Visualiza_En_GeneraOE.frm | 3629 | SELECT | rs_CantArtE.Open "SELECT cantidad from en_orden_renglon WHER… |
| Visualiza_En_GeneraOE.frm | 3662 | SELECT | rs_EnOrd.Open "SELECT * from en_orden_renglon " & _ |
| Visualiza_En_GeneraOE.frm | 4413 | SELECT | conn.Execute "DELETE FROM en_orden_renglon WHERE codigo_movi… |
| Visualiza_En_GeneraOE.frm | 4413 | DELETE | conn.Execute "DELETE FROM en_orden_renglon WHERE codigo_movi… |
| Visualiza_En_GeneraOE.frm | 4428 | SELECT | rs_EnOr.Open "SELECT * FROM en_orden_renglon WHERE id_en_ord… |
| Visualiza_En_GeneraOE.frm | 4560 | SELECT | rs_CantArtE.Open "SELECT cantidad FROM en_orden_renglon WHER… |
| Visualiza_En_GeneraOE.frm | 5304 | SELECT | rs_cantEP.Open "SELECT * From en_orden_renglon WHERE codigo_… |
| Visualiza_En_GeneraOE.frm | 5388 | SELECT | rs_CantERenglon.Open "SELECT * From en_orden_renglon WHERE c… |
| Visualiza_En_GeneraOE.frm | 5685 | SELECT | '            rs_msg.Open "SELECT en_orden_renglon.*, en_abm.… |
| Visualiza_En_GeneraOE.frm | 5691 | SELECT | rs_msg.Open "SELECT en_orden_renglon.*, en_abm.nombre_en_abm… |
| Visualiza_En_GeneraOE.frm | 5727 | JOIN | "RIGHT JOIN en_orden_renglon ON (en_orden_renglon.codigo_mov… |
| Visualiza_En_GeneraOE.frm | 5829 | SELECT | "From en_orden_renglon, en_orden_renglon_temp " & _ |
| VisualizarFichaArt.frm | 2883 | SELECT | "From en_orden_renglon " & _ |
| VisualizarFichaArt.frm | 3324 | JOIN | '        "LEFT JOIN en_orden_renglon ON (en_orden_renglon.co… |
| En_GeneraPOE.frm | 2312 | SELECT | varfrom = Split(DataArticulos.Recordset.Source, "From en_ord… |
| En_GeneraPOE.frm | 2325 | SELECT | "FROM en_orden_renglon " & varfrom2(0) & " ORDER BY En_detal… |
| En_GeneraPOE.frm | 2458 | SELECT | "From en_orden_renglon " & _ |
| En_GeneraPOE.frm | 2480 | SELECT | "From en_orden_renglon " & _ |
| Visualiza.bas | 8131 | SELECT | rs_Orenglon.Open "SELECT en_orden_renglon.*, en_abm.nombre_e… |
| Visualiza.bas | 8215 | JOIN | "RIGHT OUTER JOIN en_orden_renglon ON (en_orden_renglon.codi… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)