# Tabla `en_orden_renglon_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_orden_renglon_temp | DOUBLE | No | ✓ |  |  |
| codigo_movimiento | DOUBLE | Sí |  |  |  |
| id_en_abm_temp | DOUBLE | Sí |  |  |  |
| cantidad | DECIMAL | Sí |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| nombre_en_abm_temp | VARCHAR | Sí |  |  |  |
| IDArt | DOUBLE | Sí |  |  |  |
| cantidadE_temp | DECIMAL | Sí |  |  |  |
| cantidadMovParcial_temp | DECIMAL | Sí |  |  |  |
| id_lote | DOUBLE | Sí |  |  |  |
| cod_lote | VARCHAR | Sí |  |  |  |
| vto_lote | DATE | Sí |  |  |  |
| Lote | VARCHAR | Sí |  |  |  |
| completo_temp | VARCHAR | Sí |  |  |  |
| id_manual | VARCHAR | Sí |  |  |  |

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
| FacturaB_COPIA.frm | 17436 | SELECT | '                rs_articulo.Open "SELECT * From en_orden_re… |
| TPV.frm | 35223 | SELECT | '                rs_articulo.Open "SELECT * From en_orden_re… |
| FacturaB.frm | 24090 | SELECT | '                rs_articulo.Open "SELECT * From en_orden_re… |
| FacturaA.frm | 20703 | SELECT | '                rs_articulo.Open "SELECT * From en_orden_re… |
| En_GeneraOE.frm | 2529 | SELECT | conn.Execute "delete from en_orden_renglon_temp where id_usu… |
| En_GeneraOE.frm | 2529 | DELETE | conn.Execute "delete from en_orden_renglon_temp where id_usu… |
| En_GeneraOE.frm | 2532 | SELECT | '    conn.Execute "delete from en_orden_renglon_temp where i… |
| En_GeneraOE.frm | 2532 | DELETE | '    conn.Execute "delete from en_orden_renglon_temp where i… |
| En_GeneraOE.frm | 2792 | SELECT | conn.Execute "DELETE FROM en_orden_renglon_temp WHERE id_en_… |
| En_GeneraOE.frm | 2792 | DELETE | conn.Execute "DELETE FROM en_orden_renglon_temp WHERE id_en_… |
| En_GeneraOE.frm | 3038 | SELECT | "(SELECT Count(cantidadE_temp) FROM en_orden_renglon_temp " … |
| En_GeneraOE.frm | 3041 | SELECT | "From en_orden_renglon_temp " & _ |
| En_GeneraOE.frm | 3085 | SELECT | rs_VerifLote.Open "SELECT * From en_orden_renglon_temp Where… |
| En_GeneraOE.frm | 3281 | SELECT | rs_EnORTemp.Open "SELECT * from en_orden_renglon_temp WHERE … |
| En_GeneraOE.frm | 3363 | JOIN | "LEFT JOIN en_orden_renglon_temp ON (en_orden_renglon_temp.i… |
| En_GeneraOE.frm | 3448 | JOIN | "LEFT JOIN en_orden_renglon_temp ON (en_orden_renglon_temp.i… |
| En_GeneraOE.frm | 3722 | SELECT | rs_artE.Open "SELECT * from en_orden_renglon_temp WHERE id_u… |
| En_GeneraOE.frm | 3726 | SELECT | rs_artE.Open "SELECT * FROM en_orden_renglon_temp WHERE id_u… |
| En_GeneraOE.frm | 3970 | SELECT | rs_articulo.Open "SELECT * From en_orden_renglon_temp WHERE … |
| En_GeneraOE.frm | 4450 | SELECT | rs_EsCantECero.Open "SELECT * FROM en_orden_renglon_temp WHE… |
| En_GeneraOE.frm | 4472 | UPDATE | conn.Execute "UPDATE en_orden_renglon_temp SET cantidadE_tem… |
| En_GeneraOE.frm | 4484 | SELECT | "FROM en_orden_renglon_temp " & _ |
| En_GeneraOE.frm | 4509 | SELECT | "From en_orden_renglon_temp " & _ |
| En_GeneraOE.frm | 4554 | UPDATE | conn.Execute "UPDATE en_orden_renglon_temp SET cod_lote = NU… |
| En_GeneraOE.frm | 4592 | UPDATE | conn.Execute "UPDATE en_orden_renglon_temp SET cod_lote = NU… |
| En_GeneraOE.frm | 4642 | SELECT | rs_msg.Open "SELECT * FROM en_orden_renglon_temp " & _ |
| En_GeneraOE.frm | 4646 | SELECT | '               rs_msg.Open "SELECT * FROM en_orden_renglon_… |
| En_GeneraOE.frm | 4698 | SELECT | rs_msg.Open "SELECT en_orden_renglon_temp.* FROM en_orden_re… |
| En_GeneraOE.frm | 4756 | JOIN | "LEFT JOIN en_orden_renglon_temp ON (en_orden_renglon_temp.i… |
| En_GestionOE.frm | 1484 | SELECT | conn.Execute "delete from en_orden_renglon_temp where id_usu… |
| En_GestionOE.frm | 1484 | DELETE | conn.Execute "delete from en_orden_renglon_temp where id_usu… |
| En_GestionOE.frm | 1488 | SELECT | '            conn.Execute "delete from en_orden_renglon_temp… |
| En_GestionOE.frm | 1488 | DELETE | '            conn.Execute "delete from en_orden_renglon_temp… |
| En_GestionOE.frm | 1572 | SELECT | Visualiza_En_GeneraOE.DataArtE.RecordSource = "SELECT * FROM… |
| En_GestionOE.frm | 1625 | SELECT | Visualiza_En_GeneraOE.DataArtE.RecordSource = "SELECT * FROM… |
| En_GestionOE.frm | 1627 | SELECT | '                    Visualiza_En_GeneraOE.DataArtE.RecordSo… |
| Remito.frm | 12158 | SELECT | '                rs_articulo.Open "SELECT * From en_orden_re… |
| En_CargaOE_ArtE.frm | 823 | SELECT | rs_Rep.Open "SELECT id_en_abm_temp FROM en_orden_renglon_tem… |
| En_CargaOE_ArtE.frm | 839 | SELECT | En_GeneraOE.DataArtE.RecordSource = "SELECT * FROM en_orden_… |
| En_CargaOE_ArtE.frm | 896 | SELECT | En_GeneraOE.DataArtE.RecordSource = "SELECT * FROM en_orden_… |
| En_CargaOE_ArtE.frm | 994 | SELECT | conn.Execute "DELETE FROM en_orden_renglon_temp WHERE id_en_… |
| En_CargaOE_ArtE.frm | 994 | DELETE | conn.Execute "DELETE FROM en_orden_renglon_temp WHERE id_en_… |
| En_CargaOE_ArtE.frm | 997 | SELECT | En_GeneraOE.DataArtE.RecordSource = "SELECT * FROM en_orden_… |
| En_CargaOE_ArtE.frm | 1133 | SELECT | En_GeneraOE.DataArtE.RecordSource = "SELECT * FROM en_orden_… |
| En_CargaOE_ArtE.frm | 1156 | SELECT | rs_Rep.Open "SELECT id_en_abm_temp FROM en_orden_renglon_tem… |
| En_CargaOE_ArtE.frm | 1172 | SELECT | Visualiza_En_GeneraOE.DataArtE.RecordSource = "SELECT * FROM… |
| En_CargaOE_ArtE.frm | 1228 | SELECT | Visualiza_En_GeneraOE.DataArtE.RecordSource = "SELECT * FROM… |
| En_CargaOE_ArtE.frm | 1297 | SELECT | conn.Execute "DELETE FROM en_orden_renglon_temp WHERE id_en_… |
| En_CargaOE_ArtE.frm | 1297 | DELETE | conn.Execute "DELETE FROM en_orden_renglon_temp WHERE id_en_… |
| En_CargaOE_ArtE.frm | 1300 | SELECT | Visualiza_En_GeneraOE.DataArtE.RecordSource = "SELECT * FROM… |
| En_CargaOE_ArtE.frm | 1488 | SELECT | Visualiza_En_GeneraOE.DataArtE.RecordSource = "SELECT * FROM… |
| Visualiza_En_GeneraOE.frm | 2649 | SELECT | conn.Execute "delete from en_orden_renglon_temp where id_usu… |
| Visualiza_En_GeneraOE.frm | 2649 | DELETE | conn.Execute "delete from en_orden_renglon_temp where id_usu… |
| Visualiza_En_GeneraOE.frm | 2652 | SELECT | '    conn.Execute "delete from en_orden_renglon_temp where i… |
| Visualiza_En_GeneraOE.frm | 2652 | DELETE | '    conn.Execute "delete from en_orden_renglon_temp where i… |
| Visualiza_En_GeneraOE.frm | 2956 | SELECT | conn.Execute "DELETE FROM en_orden_renglon_temp WHERE id_en_… |
| Visualiza_En_GeneraOE.frm | 2956 | DELETE | conn.Execute "DELETE FROM en_orden_renglon_temp WHERE id_en_… |
| Visualiza_En_GeneraOE.frm | 3281 | SELECT | "(SELECT Count(cantidadE_temp) FROM en_orden_renglon_temp " … |
| Visualiza_En_GeneraOE.frm | 3284 | SELECT | "From en_orden_renglon_temp " & _ |
| Visualiza_En_GeneraOE.frm | 3329 | SELECT | rs_VerifLote.Open "SELECT * From en_orden_renglon_temp Where… |
| Visualiza_En_GeneraOE.frm | 3411 | SELECT | '                conn.Execute "DELETE en_orden_renglon_temp.… |
| Visualiza_En_GeneraOE.frm | 3513 | SELECT | rs_artE.Open "SELECT * FROM en_orden_renglon_temp WHERE id_u… |
| Visualiza_En_GeneraOE.frm | 3518 | SELECT | rs_artE.Open "SELECT * FROM en_orden_renglon_temp WHERE id_u… |
| Visualiza_En_GeneraOE.frm | 3525 | SELECT | '                    rs_artE.Open "SELECT * FROM en_orden_re… |
| Visualiza_En_GeneraOE.frm | 3809 | SELECT | rs_articulo.Open "SELECT * From en_orden_renglon_temp WHERE … |
| Visualiza_En_GeneraOE.frm | 4415 | SELECT | rs_EnORTemp.Open "SELECT * from en_orden_renglon_temp WHERE … |
| Visualiza_En_GeneraOE.frm | 4494 | JOIN | "LEFT JOIN en_orden_renglon_temp ON (en_orden_renglon_temp.i… |
| Visualiza_En_GeneraOE.frm | 4602 | JOIN | "LEFT JOIN en_orden_renglon_temp ON (en_orden_renglon_temp.i… |
| Visualiza_En_GeneraOE.frm | 5362 | SELECT | '        DataArtE.RecordSource = "SELECT * FROM en_orden_ren… |
| Visualiza_En_GeneraOE.frm | 5478 | SELECT | rs_EsCantECero.Open "SELECT * FROM en_orden_renglon_temp WHE… |
| Visualiza_En_GeneraOE.frm | 5500 | UPDATE | conn.Execute "UPDATE en_orden_renglon_temp SET cantidadE_tem… |
| Visualiza_En_GeneraOE.frm | 5512 | SELECT | "FROM en_orden_renglon_temp " & _ |
| Visualiza_En_GeneraOE.frm | 5537 | SELECT | "From en_orden_renglon_temp " & _ |
| Visualiza_En_GeneraOE.frm | 5635 | SELECT | rs_msg.Open "SELECT * FROM en_orden_renglon_temp " & _ |
| Visualiza_En_GeneraOE.frm | 5771 | JOIN | "LEFT JOIN en_orden_renglon_temp ON (en_orden_renglon_temp.i… |
| Visualiza_En_GeneraOE.frm | 5866 | UPDATE | conn.Execute "UPDATE en_orden_renglon_temp SET cod_lote = NU… |
| Visualiza_En_GeneraOE.frm | 5904 | UPDATE | conn.Execute "UPDATE en_orden_renglon_temp SET cod_lote = NU… |
| En_CargaOE_Ref.frm | 1535 | SELECT | "FROM en_orden_renglon_temp WHERE visualiza = 'No' AND id_us… |
| En_CargaOE_Ref.frm | 1834 | SELECT | "FROM en_orden_renglon_temp WHERE visualiza = 'Si' AND id_us… |
| TPV_2.frm | 32673 | SELECT | '                rs_articulo.Open "SELECT * From en_orden_re… |
| … | … | … | *(11 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)