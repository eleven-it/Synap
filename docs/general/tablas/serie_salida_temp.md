# Tabla `serie_salida_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_serie_salida_temp | DOUBLE | No | ✓ |  |  |
| id_serie_entrada | DOUBLE | Sí |  |  |  |
| id_articulo | FLOAT | Sí |  |  |  |
| nro_serie | VARCHAR | Sí |  |  |  |
| vto_serie | DATE | Sí |  |  |  |
| desc_serie | VARCHAR | Sí |  |  |  |
| tipo_comprobante | VARCHAR | Sí |  |  |  |
| codigo_mov_salida | DOUBLE | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| orden | DOUBLE | Sí |  |  |  |
| id_stock | DOUBLE | Sí |  |  |  |
| id_serie_mov | DOUBLE | Sí |  |  |  |
| cod_mov_entrada | DOUBLE | Sí |  |  |  |
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
| PNotaCred.frm | 2774 | SELECT | rs_cons_serie_dev.Open "SELECT id_serie_salida_temp,id_serie… |
| PNotaCred.frm | 3101 | UPDATE | conn.Execute "UPDATE serie_salida_temp " & _ |
| PNotaCred.frm | 4455 | SELECT | conn.Execute "DELETE serie_salida_temp.* FROM serie_salida_t… |
| PNotaCred.frm | 5790 | SELECT | conn.Execute "DELETE serie_salida_temp.* FROM serie_salida_t… |
| PNotaCred.frm | 7522 | SELECT | "cuerpostockp.Cantidad <> (SELECT count(*) FROM serie_salida… |
| PNotaCred.frm | 7715 | SELECT | "From serie_salida_temp " & _ |
| PNotaCred.frm | 7730 | SELECT | "FROM serie_salida_temp " & _ |
| PNotaCred.frm | 7742 | SELECT | "FROM serie_salida_temp " & _ |
| Visualiza_CargaMovStock.frm | 4697 | SELECT | conn.Execute "DELETE serie_salida_temp.* FROM serie_salida_t… |
| Visualiza_CargaMovStock.frm | 6003 | SELECT | "cuerpostock_mstock.Cantidad <> (SELECT count(*) FROM serie_… |
| Visualiza_CargaMovStock.frm | 6195 | JOIN | "LEFT JOIN serie_salida_temp b ON " & _ |
| Visualiza_CargaMovStock.frm | 6238 | SELECT | "FROM serie_salida_temp " & _ |
| Visualiza_CargaMovStock.frm | 6252 | SELECT | "FROM serie_salida_temp " & _ |
| FacturaB_COPIA.frm | 7995 | SELECT | conn.Execute "DELETE FROM serie_salida_temp " & _ |
| FacturaB_COPIA.frm | 7995 | DELETE | conn.Execute "DELETE FROM serie_salida_temp " & _ |
| FacturaB_COPIA.frm | 8330 | SELECT | conn.Execute "DELETE serie_salida_temp.* FROM serie_salida_t… |
| FacturaB_COPIA.frm | 16550 | SELECT | "cuerpostock.Cantidad <> (SELECT count(*) FROM serie_salida_… |
| FacturaB_COPIA.frm | 16686 | SELECT | "From serie_salida_temp " & _ |
| FacturaB_COPIA.frm | 16701 | SELECT | "From serie_salida_temp " & _ |
| Serie_salida.frm | 600 | INSERT | conn.Execute "INSERT INTO serie_salida_temp( " & _ |
| Serie_salida.frm | 629 | SELECT | conn.Execute "DELETE serie_salida_temp.* FROM serie_salida_t… |
| Serie_salida.frm | 635 | INSERT | conn.Execute "INSERT INTO serie_salida_temp( " & _ |
| Serie_salida.frm | 710 | SELECT | conn.Execute "DELETE serie_salida_temp.* FROM serie_salida_t… |
| Serie_salida.frm | 717 | INSERT | conn.Execute "INSERT INTO serie_salida_temp (desc_serie, id_… |
| Serie_salida.frm | 747 | JOIN | "LEFT JOIN serie_salida_temp ON (serie_salida_temp.orden = c… |
| Serie_salida.frm | 768 | SELECT | "From serie_salida_temp " & _ |
| Serie_salida.frm | 807 | JOIN | "LEFT JOIN serie_salida_temp ON (serie_salida_temp.orden = c… |
| Serie_salida.frm | 823 | SELECT | "From serie_salida_temp " & _ |
| Serie_salida.frm | 846 | JOIN | "LEFT JOIN serie_salida_temp ON (serie_salida_temp.orden = c… |
| Serie_salida.frm | 862 | SELECT | "From serie_salida_temp " & _ |
| Serie_salida.frm | 882 | SELECT | "From serie_salida_temp " & _ |
| Serie_salida.frm | 944 | SELECT | "From serie_salida_temp " & _ |
| Serie_salida.frm | 964 | SELECT | "FROM serie_salida_temp " & _ |
| Serie_salida.frm | 984 | SELECT | "From serie_salida_temp " & _ |
| Serie_salida.frm | 1004 | SELECT | "From serie_salida_temp " & _ |
| Serie_salida.frm | 1408 | SELECT | "From serie_salida_temp " & _ |
| Serie_salida.frm | 1524 | SELECT | "From serie_salida_temp " & _ |
| Serie_salida.frm | 1545 | SELECT | "FROM serie_salida_temp " & _ |
| Serie_salida.frm | 1564 | SELECT | "From serie_salida_temp " & _ |
| Serie_salida.frm | 1583 | SELECT | "From serie_salida_temp " & _ |
| Visualiza_TPV.frm | 6160 | SELECT | conn.Execute "DELETE FROM serie_salida_temp " & _ |
| Visualiza_TPV.frm | 6160 | DELETE | conn.Execute "DELETE FROM serie_salida_temp " & _ |
| TPV.frm | 12199 | SELECT | conn.Execute "DELETE serie_salida_temp.* FROM serie_salida_t… |
| TPV.frm | 12301 | SELECT | '                conn.Execute "DELETE serie_salida_temp.* FR… |
| TPV.frm | 12942 | SELECT | conn.Execute "DELETE FROM serie_salida_temp " & _ |
| TPV.frm | 12942 | DELETE | conn.Execute "DELETE FROM serie_salida_temp " & _ |
| TPV.frm | 33695 | SELECT | "cuerpostock.Cantidad <> (SELECT count(*) FROM serie_salida_… |
| TPV.frm | 33839 | SELECT | "From serie_salida_temp " & _ |
| TPV.frm | 33854 | SELECT | "From serie_salida_temp " & _ |
| Visualiza_FB_Copia.frm | 4403 | SELECT | conn.Execute "DELETE FROM serie_salida_temp " & _ |
| Visualiza_FB_Copia.frm | 4403 | DELETE | conn.Execute "DELETE FROM serie_salida_temp " & _ |
| Visualiza_FB_Copia.frm | 7832 | JOIN | "LEFT JOIN serie_salida_temp b ON " & _ |
| Visualiza_FB_Copia.frm | 7875 | SELECT | "FROM serie_salida_temp " & _ |
| Visualiza_FB_Copia.frm | 7889 | SELECT | "FROM serie_salida_temp " & _ |
| Visualiza_FB_Copia.frm | 7958 | SELECT | "cuerpostock.Cantidad <> (SELECT count(*) FROM serie_salida_… |
| Visualiza_PNotaCredDev.frm | 4564 | SELECT | conn.Execute "DELETE FROM serie_salida_temp " & _ |
| Visualiza_PNotaCredDev.frm | 4564 | DELETE | conn.Execute "DELETE FROM serie_salida_temp " & _ |
| Visualiza_PNotaCredDev.frm | 6297 | JOIN | "LEFT JOIN serie_salida_temp b ON " & _ |
| Visualiza_PNotaCredDev.frm | 6347 | SELECT | "FROM serie_salida_temp " & _ |
| Visualiza_PNotaCredDev.frm | 6364 | SELECT | "FROM serie_salida_temp " & _ |
| Visualiza_PNotaCredDev.frm | 6391 | SELECT | "From serie_salida_temp " & _ |
| Visualiza_PNotaCredDev.frm | 6434 | SELECT | "cuerpostockp.Cantidad <> (SELECT count(*) FROM serie_salida… |
| FacturaB.frm | 13085 | SELECT | conn.Execute "DELETE FROM serie_salida_temp " & _ |
| FacturaB.frm | 13085 | DELETE | conn.Execute "DELETE FROM serie_salida_temp " & _ |
| FacturaB.frm | 13484 | SELECT | conn.Execute "DELETE serie_salida_temp.* FROM serie_salida_t… |
| FacturaB.frm | 22624 | SELECT | "cuerpostock.Cantidad <> (SELECT count(*) FROM serie_salida_… |
| FacturaB.frm | 22760 | SELECT | "From serie_salida_temp " & _ |
| FacturaB.frm | 22775 | SELECT | "From serie_salida_temp " & _ |
| FacturaA.frm | 8643 | SELECT | conn.Execute "DELETE FROM serie_salida_temp " & _ |
| FacturaA.frm | 8643 | DELETE | conn.Execute "DELETE FROM serie_salida_temp " & _ |
| FacturaA.frm | 9038 | SELECT | conn.Execute "DELETE serie_salida_temp.* FROM serie_salida_t… |
| FacturaA.frm | 19237 | SELECT | "cuerpostock.Cantidad <> (SELECT count(*) FROM serie_salida_… |
| FacturaA.frm | 19373 | SELECT | "From serie_salida_temp " & _ |
| FacturaA.frm | 19387 | SELECT | "From serie_salida_temp " & _ |
| Serie_salida_visualiza.frm | 560 | SELECT | "From serie_salida_temp " & _ |
| Serie_salida_visualiza.frm | 594 | SELECT | "FROM serie_salida_temp " & _ |
| Serie_salida_visualiza.frm | 601 | INSERT | conn.Execute "INSERT INTO serie_salida_temp( " & _ |
| Serie_salida_visualiza.frm | 618 | UPDATE | conn.Execute "UPDATE serie_salida_temp " & _ |
| Serie_salida_visualiza.frm | 654 | UPDATE | conn.Execute "UPDATE serie_salida_temp " & _ |
| Serie_salida_visualiza.frm | 742 | SELECT | rs.Open "SELECT * FROM serie_salida_temp " & _ |
| … | … | … | *(78 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)