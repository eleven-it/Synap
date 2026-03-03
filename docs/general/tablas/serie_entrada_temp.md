# Tabla `serie_entrada_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_serie_entrada_temp | DOUBLE | No | ✓ |  |  |
| id_articulo | FLOAT | Sí |  |  |  |
| nro_serie | VARCHAR | Sí |  |  |  |
| vto_serie | DATE | Sí |  |  |  |
| desc_serie | VARCHAR | Sí |  |  |  |
| tipo_comprobante | VARCHAR | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| id_serie_entrada | DOUBLE | Sí |  |  |  |
| cod_mov_entrada | DOUBLE | Sí |  |  |  |
| orden | DOUBLE | Sí |  |  |  |
| id_serie_salida | DOUBLE | Sí |  |  |  |
| codigo_mov_salida | DOUBLE | Sí |  |  |  |
| id_stock | DOUBLE | Sí |  |  |  |
| id_deposito | INT | Sí |  |  |  |

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
| Visualiza_NotaCred.frm | 4690 | SELECT | conn.Execute "DELETE FROM serie_entrada_temp " & _ |
| Visualiza_NotaCred.frm | 4690 | DELETE | conn.Execute "DELETE FROM serie_entrada_temp " & _ |
| Visualiza_NotaCred.frm | 6106 | JOIN | "LEFT JOIN serie_entrada_temp b ON " & _ |
| Visualiza_NotaCred.frm | 6156 | SELECT | "FROM serie_entrada_temp " & _ |
| Visualiza_NotaCred.frm | 6171 | SELECT | "FROM serie_entrada_temp " & _ |
| Visualiza_NotaCred.frm | 6196 | SELECT | "From serie_entrada_temp " & _ |
| Visualiza_NotaCred.frm | 6237 | SELECT | "cuerpostock.Cantidad <> (SELECT count(*) FROM serie_entrada… |
| Visualiza_CargaMovStock.frm | 4693 | SELECT | conn.Execute "DELETE FROM serie_entrada_temp " & _ |
| Visualiza_CargaMovStock.frm | 4693 | DELETE | conn.Execute "DELETE FROM serie_entrada_temp " & _ |
| Visualiza_CargaMovStock.frm | 6156 | JOIN | "INNER JOIN serie_entrada_temp b ON " & _ |
| Visualiza_CargaMovStock.frm | 6169 | JOIN | "INNER JOIN serie_entrada_temp b ON " & _ |
| Serie_salida.frm | 670 | SELECT | conn.Execute "DELETE serie_entrada_temp.* FROM serie_entrada… |
| Serie_salida.frm | 681 | INSERT | conn.Execute "INSERT INTO serie_entrada_temp (desc_serie, id… |
| Serie_salida.frm | 791 | SELECT | "From serie_entrada_temp " & _ |
| Serie_salida.frm | 1429 | SELECT | "FROM serie_entrada_temp " & _ |
| Serie_salida.frm | 1448 | SELECT | "From serie_entrada_temp " & _ |
| Serie_salida.frm | 1467 | SELECT | "From serie_entrada_temp " & _ |
| NotaCred_COPIA.frm | 3440 | UPDATE | conn.Execute "UPDATE serie_entrada_temp " & _ |
| NotaCred_COPIA.frm | 6695 | SELECT | conn.Execute "DELETE serie_entrada_temp.* FROM serie_entrada… |
| NotaCred_COPIA.frm | 7759 | SELECT | conn.Execute "DELETE serie_entrada_temp.* FROM serie_entrada… |
| NotaCred_COPIA.frm | 12139 | SELECT | "cuerpostock.Cantidad <> (SELECT count(*) FROM serie_entrada… |
| NotaCred_COPIA.frm | 12405 | SELECT | "From serie_entrada_temp " & _ |
| NotaCred_COPIA.frm | 12419 | SELECT | "FROM serie_entrada_temp " & _ |
| NotaCred_COPIA.frm | 12431 | SELECT | "FROM serie_entrada_temp " & _ |
| TPV.frm | 12948 | SELECT | conn.Execute "DELETE serie_entrada_temp.* FROM serie_entrada… |
| TPV.frm | 33933 | SELECT | "From serie_entrada_temp " & _ |
| TPV.frm | 33947 | SELECT | "FROM serie_entrada_temp " & _ |
| TPV.frm | 33958 | SELECT | "FROM serie_entrada_temp " & _ |
| PRemito.frm | 5260 | SELECT | conn.Execute "DELETE serie_entrada_temp.* FROM serie_entrada… |
| PRemito.frm | 6244 | SELECT | conn.Execute "DELETE FROM serie_entrada_temp " & _ |
| PRemito.frm | 6244 | DELETE | conn.Execute "DELETE FROM serie_entrada_temp " & _ |
| PRemito.frm | 6540 | SELECT | "cuerpostockp.Cantidad <> (SELECT count(*) FROM serie_entrad… |
| PRemito.frm | 6668 | SELECT | "From serie_entrada_temp " & _ |
| Serie_carga.frm | 614 | SELECT | rs_repite.Open "SELECT count(*) as CantIng FROM serie_entrad… |
| Serie_carga.frm | 652 | SELECT | rs_repite.Open "SELECT id_serie_entrada_temp FROM serie_entr… |
| Serie_carga.frm | 669 | INSERT | conn.Execute "INSERT INTO serie_entrada_temp (desc_serie, id… |
| Serie_carga.frm | 700 | SELECT | "From serie_entrada_temp " & _ |
| Serie_carga.frm | 733 | SELECT | "FROM serie_entrada_temp " & _ |
| Serie_carga.frm | 751 | SELECT | rs_repite.Open "SELECT id_serie_entrada_temp FROM serie_entr… |
| Serie_carga.frm | 768 | INSERT | conn.Execute "INSERT INTO serie_entrada_temp (desc_serie, id… |
| Serie_carga.frm | 799 | SELECT | "From serie_entrada_temp " & _ |
| Serie_carga.frm | 819 | SELECT | rs_repite.Open "SELECT id_serie_entrada_temp FROM serie_entr… |
| Serie_carga.frm | 866 | SELECT | "FROM serie_entrada_temp " & _ |
| Serie_carga.frm | 888 | SELECT | rs_f.Open "SELECT vto_serie FROM serie_entrada_temp " & _ |
| NotaCred_SinCompO.frm | 4314 | UPDATE | conn.Execute "UPDATE serie_entrada_temp " & _ |
| NotaCred_SinCompO.frm | 8218 | SELECT | conn.Execute "DELETE serie_entrada_temp.* FROM serie_entrada… |
| NotaCred_SinCompO.frm | 10061 | SELECT | conn.Execute "DELETE serie_entrada_temp.* FROM serie_entrada… |
| NotaCred_SinCompO.frm | 14449 | SELECT | "cuerpostock.Cantidad <> (SELECT count(*) FROM serie_entrada… |
| NotaCred_SinCompO.frm | 14716 | SELECT | "From serie_entrada_temp " & _ |
| NotaCred_SinCompO.frm | 14730 | SELECT | "FROM serie_entrada_temp " & _ |
| NotaCred_SinCompO.frm | 14742 | SELECT | "FROM serie_entrada_temp " & _ |
| Serie_salida_visualiza.frm | 1153 | SELECT | rs.Open "SELECT * FROM serie_entrada_temp " & _ |
| Serie_salida_visualiza.frm | 1162 | INSERT | conn.Execute "INSERT INTO serie_entrada_temp " & _ |
| Serie_salida_visualiza.frm | 1193 | SELECT | "From serie_entrada_temp " & _ |
| Serie_salida_visualiza.frm | 1212 | SELECT | "From serie_entrada_temp " & _ |
| Serie_salida_visualiza.frm | 1376 | SELECT | "From serie_entrada_temp " & _ |
| Serie_salida_visualiza.frm | 1415 | SELECT | "FROM serie_entrada_temp " & _ |
| Serie_salida_visualiza.frm | 1428 | INSERT | conn.Execute "INSERT INTO serie_entrada_temp " & _ |
| NotaCredCopia.frm | 3983 | UPDATE | conn.Execute "UPDATE serie_entrada_temp " & _ |
| NotaCredCopia.frm | 7263 | SELECT | conn.Execute "DELETE serie_entrada_temp.* FROM serie_entrada… |
| NotaCredCopia.frm | 8607 | SELECT | conn.Execute "DELETE serie_entrada_temp.* FROM serie_entrada… |
| NotaCredCopia.frm | 13314 | SELECT | "cuerpostock.Cantidad <> (SELECT count(*) FROM serie_entrada… |
| NotaCredCopia.frm | 13580 | SELECT | "From serie_entrada_temp " & _ |
| NotaCredCopia.frm | 13594 | SELECT | "FROM serie_entrada_temp " & _ |
| NotaCredCopia.frm | 13606 | SELECT | "FROM serie_entrada_temp " & _ |
| Serie_carga_visualiza.frm | 514 | SELECT | rs_repite.Open "SELECT id_serie_entrada_temp FROM serie_entr… |
| Serie_carga_visualiza.frm | 546 | JOIN | "INNER JOIN serie_entrada_temp b ON " & _ |
| Serie_abm.frm | 549 | SELECT | conn.Execute "DELETE FROM serie_entrada_temp " & _ |
| Serie_abm.frm | 549 | DELETE | conn.Execute "DELETE FROM serie_entrada_temp " & _ |
| Serie_abm.frm | 585 | SELECT | "FROM serie_entrada_temp " & _ |
| Serie_abm.frm | 719 | SELECT | "FROM serie_entrada_temp " & _ |
| PFactura.frm | 7073 | SELECT | conn.Execute "DELETE serie_entrada_temp.* FROM serie_entrada… |
| PFactura.frm | 8177 | SELECT | conn.Execute "DELETE FROM serie_entrada_temp " & _ |
| PFactura.frm | 8177 | DELETE | conn.Execute "DELETE FROM serie_entrada_temp " & _ |
| PFactura.frm | 10225 | SELECT | "cuerpostockp.Cantidad <> (SELECT count(*) as cantS FROM ser… |
| PFactura.frm | 10368 | SELECT | "From serie_entrada_temp " & _ |
| Visualiza_PFactura_Copia.frm | 5877 | SELECT | conn.Execute "DELETE FROM serie_entrada_temp " & _ |
| Visualiza_PFactura_Copia.frm | 5877 | DELETE | conn.Execute "DELETE FROM serie_entrada_temp " & _ |
| Visualiza_PFactura_Copia.frm | 7803 | JOIN | "INNER JOIN serie_entrada_temp b ON " & _ |
| Visualiza_PFactura_Copia.frm | 7816 | JOIN | "INNER JOIN serie_entrada_temp b ON " & _ |
| … | … | … | *(54 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)