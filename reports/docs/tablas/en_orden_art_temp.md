# Tabla `en_orden_art_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_orden_art_temp | DOUBLE | No | ✓ |  |  |
| codigo_movimiento | DOUBLE | Sí |  |  |  |
| id_articulo | DOUBLE | Sí |  |  |  |
| cantidad | DECIMAL | Sí |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| NombreArticulo_temp | VARCHAR | Sí |  |  |  |
| id_articulo_manual_temp | VARCHAR | Sí |  |  |  |
| id_en_abm_temp | DOUBLE | Sí |  |  |  |
| cantidadFinal_temp | DECIMAL | Sí |  |  |  |
| cantidadMovParcial_temp | DECIMAL | Sí |  |  |  |
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
| En_GeneraOE.frm | 2528 | SELECT | conn.Execute "delete from en_orden_art_temp where id_usuario… |
| En_GeneraOE.frm | 2528 | DELETE | conn.Execute "delete from en_orden_art_temp where id_usuario… |
| En_GeneraOE.frm | 2531 | SELECT | '    conn.Execute "delete from en_orden_art_temp where id_us… |
| En_GeneraOE.frm | 2531 | DELETE | '    conn.Execute "delete from en_orden_art_temp where id_us… |
| En_GeneraOE.frm | 2643 | SELECT | conn.Execute "DELETE FROM en_orden_art_temp WHERE id_en_orde… |
| En_GeneraOE.frm | 2643 | DELETE | conn.Execute "DELETE FROM en_orden_art_temp WHERE id_en_orde… |
| En_GeneraOE.frm | 2798 | SELECT | conn.Execute "DELETE FROM en_orden_art_temp WHERE id_en_abm_… |
| En_GeneraOE.frm | 2798 | DELETE | conn.Execute "DELETE FROM en_orden_art_temp WHERE id_en_abm_… |
| En_GeneraOE.frm | 2910 | SELECT | '                                "From en_orden_art_temp " &… |
| En_GeneraOE.frm | 2927 | SELECT | "From en_orden_art_temp " & _ |
| En_GeneraOE.frm | 2993 | SELECT | "From en_orden_art_temp " & _ |
| En_GeneraOE.frm | 2996 | SELECT | "From en_orden_art_temp " & _ |
| En_GeneraOE.frm | 3004 | SELECT | "From en_orden_art_temp " & _ |
| En_GeneraOE.frm | 3111 | SELECT | rs_VerifLote.Open "SELECT * From en_orden_art_temp Where Lot… |
| En_GeneraOE.frm | 3362 | SELECT | "From en_orden_art_temp " & _ |
| En_GeneraOE.frm | 3391 | SELECT | rs_ArtTemp.Open "SELECT * from en_orden_art_temp WHERE id_us… |
| En_GeneraOE.frm | 3447 | SELECT | "From en_orden_art_temp " & _ |
| En_GeneraOE.frm | 3591 | SELECT | rs_imp.Open "SELECT * FROM en_orden_art_temp WHERE id_usuari… |
| En_GeneraOE.frm | 3625 | SELECT | rs_imp.Open "SELECT * FROM en_orden_art_temp WHERE id_usuari… |
| En_GeneraOE.frm | 3772 | SELECT | rs_ArtTemp.Open "SELECT * FROM en_orden_art_temp WHERE id_us… |
| En_GeneraOE.frm | 3775 | SELECT | rs_ArtTemp.Open "SELECT * FROM en_orden_art_temp WHERE id_us… |
| En_GeneraOE.frm | 4266 | SELECT | rs_articulo.Open "SELECT * From en_orden_art_temp WHERE ID_a… |
| En_GeneraOE.frm | 4476 | UPDATE | conn.Execute "UPDATE en_orden_art_temp SET cantidadMovParcia… |
| En_GeneraOE.frm | 4485 | JOIN | "RIGHT JOIN en_orden_art_temp ON (en_orden_art_temp.id_en_ab… |
| En_GeneraOE.frm | 4560 | UPDATE | conn.Execute "UPDATE en_orden_art_temp SET cod_lote = NULL, … |
| En_GeneraOE.frm | 4598 | UPDATE | conn.Execute "UPDATE en_orden_art_temp SET cod_lote = NULL, … |
| En_GeneraOE.frm | 4667 | SELECT | rs_msg.Open "SELECT * FROM en_orden_art_temp " & _ |
| En_GeneraOE.frm | 4671 | SELECT | '            rs_msg.Open "SELECT * FROM en_orden_art_temp " … |
| En_GeneraOE.frm | 4720 | SELECT | "FROM en_orden_art_temp " & _ |
| En_GeneraOE.frm | 4755 | SELECT | "From en_orden_art_temp " & _ |
| En_GestionOE.frm | 1483 | SELECT | conn.Execute "delete from en_orden_art_temp where id_usuario… |
| En_GestionOE.frm | 1483 | DELETE | conn.Execute "delete from en_orden_art_temp where id_usuario… |
| En_GestionOE.frm | 1487 | SELECT | '            conn.Execute "delete from en_orden_art_temp whe… |
| En_GestionOE.frm | 1487 | DELETE | '            conn.Execute "delete from en_orden_art_temp whe… |
| En_GestionOE.frm | 1653 | SELECT | Visualiza_En_GeneraOE.DataArt.RecordSource = "SELECT * FROM … |
| En_GestionOE.frm | 1714 | SELECT | Visualiza_En_GeneraOE.DataArt.RecordSource = "SELECT * FROM … |
| En_GestionOE.frm | 1716 | SELECT | '                 Visualiza_En_GeneraOE.DataArt.RecordSource… |
| En_CargaOE_ArtE.frm | 915 | INSERT | sqlFormulaEnsamb = "INSERT INTO en_orden_art_temp (NombreArt… |
| En_CargaOE_ArtE.frm | 948 | SELECT | '                            En_GeneraOE.DataArt.RecordSourc… |
| En_CargaOE_ArtE.frm | 982 | SELECT | En_GeneraOE.DataArt.RecordSource = "SELECT * FROM en_orden_a… |
| En_CargaOE_ArtE.frm | 1088 | SELECT | rs_cantF.Open "SELECT * FROM en_orden_art_temp WHERE id_usua… |
| En_CargaOE_ArtE.frm | 1138 | SELECT | En_GeneraOE.DataArt.RecordSource = "SELECT * FROM en_orden_a… |
| En_CargaOE_ArtE.frm | 1252 | SELECT | Visualiza_En_GeneraOE.DataArt.RecordSource = "SELECT * FROM … |
| En_CargaOE_ArtE.frm | 1285 | SELECT | Visualiza_En_GeneraOE.DataArt.RecordSource = "SELECT * FROM … |
| En_CargaOE_ArtE.frm | 1441 | SELECT | rs_cantF.Open "SELECT * FROM en_orden_art_temp WHERE id_usua… |
| En_CargaOE_ArtE.frm | 1494 | SELECT | Visualiza_En_GeneraOE.DataArt.RecordSource = "SELECT * FROM … |
| Visualiza_En_GeneraOE.frm | 2648 | SELECT | conn.Execute "delete from en_orden_art_temp where id_usuario… |
| Visualiza_En_GeneraOE.frm | 2648 | DELETE | conn.Execute "delete from en_orden_art_temp where id_usuario… |
| Visualiza_En_GeneraOE.frm | 2651 | SELECT | '    conn.Execute "delete from en_orden_art_temp where id_us… |
| Visualiza_En_GeneraOE.frm | 2651 | DELETE | '    conn.Execute "delete from en_orden_art_temp where id_us… |
| Visualiza_En_GeneraOE.frm | 2764 | SELECT | conn.Execute "DELETE FROM en_orden_art_temp WHERE id_en_orde… |
| Visualiza_En_GeneraOE.frm | 2764 | DELETE | conn.Execute "DELETE FROM en_orden_art_temp WHERE id_en_orde… |
| Visualiza_En_GeneraOE.frm | 2822 | SELECT | rs_movS.Open "SELECT * FROM en_orden_art_temp WHERE id_usuar… |
| Visualiza_En_GeneraOE.frm | 2962 | SELECT | conn.Execute "DELETE FROM en_orden_art_temp WHERE id_en_abm_… |
| Visualiza_En_GeneraOE.frm | 2962 | DELETE | conn.Execute "DELETE FROM en_orden_art_temp WHERE id_en_abm_… |
| Visualiza_En_GeneraOE.frm | 3108 | SELECT | "From en_orden_art_temp " & _ |
| Visualiza_En_GeneraOE.frm | 3190 | SELECT | '                            "From en_orden_art_temp " & _ |
| Visualiza_En_GeneraOE.frm | 3245 | SELECT | "From en_orden_art_temp " & _ |
| Visualiza_En_GeneraOE.frm | 3355 | SELECT | rs_VerifLote.Open "SELECT * From en_orden_art_temp Where Lot… |
| Visualiza_En_GeneraOE.frm | 3412 | JOIN | '                                    "INNER JOIN en_orden_ar… |
| Visualiza_En_GeneraOE.frm | 3596 | SELECT | rs_ArtTemp.Open "SELECT * FROM en_orden_art_temp WHERE id_us… |
| Visualiza_En_GeneraOE.frm | 3599 | SELECT | rs_ArtTemp.Open "SELECT * FROM en_orden_art_temp WHERE id_us… |
| Visualiza_En_GeneraOE.frm | 4103 | SELECT | rs_articulo.Open "SELECT * From en_orden_art_temp WHERE ID_a… |
| Visualiza_En_GeneraOE.frm | 4282 | UPDATE | conn.Execute "UPDATE en_orden_art_temp " & _ |
| Visualiza_En_GeneraOE.frm | 4493 | SELECT | "From en_orden_art_temp " & _ |
| Visualiza_En_GeneraOE.frm | 4525 | SELECT | rs_ArtTemp.Open "SELECT * FROM en_orden_art_temp WHERE id_us… |
| Visualiza_En_GeneraOE.frm | 4601 | SELECT | "From en_orden_art_temp " & _ |
| Visualiza_En_GeneraOE.frm | 4782 | SELECT | rs_imp.Open "SELECT * FROM en_orden_art_temp WHERE id_usuari… |
| Visualiza_En_GeneraOE.frm | 4816 | SELECT | rs_imp.Open "SELECT * FROM en_orden_art_temp WHERE id_usuari… |
| Visualiza_En_GeneraOE.frm | 5366 | SELECT | '        DataArt.RecordSource = "SELECT * FROM en_orden_art_… |
| Visualiza_En_GeneraOE.frm | 5504 | UPDATE | conn.Execute "UPDATE en_orden_art_temp SET cantidadMovParcia… |
| Visualiza_En_GeneraOE.frm | 5513 | JOIN | "RIGHT JOIN en_orden_art_temp ON (en_orden_art_temp.id_en_ab… |
| Visualiza_En_GeneraOE.frm | 5655 | SELECT | rs_msg.Open "SELECT * FROM en_orden_art_temp " & _ |
| Visualiza_En_GeneraOE.frm | 5729 | SELECT | "en_orden_art.id_articulo IN (SELECT en_orden_art_temp.id_ar… |
| Visualiza_En_GeneraOE.frm | 5770 | SELECT | "FROM en_orden_art_temp " & _ |
| Visualiza_En_GeneraOE.frm | 5872 | UPDATE | conn.Execute "UPDATE en_orden_art_temp SET cod_lote = NULL, … |
| Visualiza_En_GeneraOE.frm | 5910 | UPDATE | conn.Execute "UPDATE en_orden_art_temp SET cod_lote = NULL, … |
| En_GeneraPOE.frm | 3158 | SELECT | '                rs_articulo.Open "SELECT * From en_orden_ar… |
| Principal.frm | 6112 | SELECT | conn.Execute "delete from en_orden_art_temp where id_usuario… |
| Principal.frm | 6112 | DELETE | conn.Execute "delete from en_orden_art_temp where id_usuario… |
| … | … | … | *(15 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)