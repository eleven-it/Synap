# Tabla `serie_entrada`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_serie_entrada | DOUBLE | No | ✓ |  |  |
| id_articulo | FLOAT | Sí |  |  |  |
| nro_serie | VARCHAR | Sí |  |  |  |
| vto_serie | DATE | Sí |  |  |  |
| desc_serie | VARCHAR | Sí |  |  |  |
| tipo_comprobante | VARCHAR | Sí |  |  |  |
| codigo_mov_entrada | DOUBLE | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| disponible | VARCHAR | Sí |  |  |  |
| id_serie_salida | DOUBLE | Sí |  |  |  |
| id_deposito | INT | Sí |  |  |  |
| codigo_mov_compra | DOUBLE | Sí |  |  |  |

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
| Info_Stock.frm | 11628 | SELECT | "FROM serie_entrada ORDER BY nro_serie " |
| Info_Stock.frm | 15378 | SELECT | "FROM serie_entrada " & _ |
| Info_Stock.frm | 15390 | SELECT | "FROM serie_entrada ORDER BY nro_serie " |
| PNotaCred.frm | 2759 | SELECT | rs_cons_serie.Open "SELECT id_serie_entrada,codigo_mov_entra… |
| PNotaCred.frm | 2777 | SELECT | rs_cons_serie.Open "SELECT id_serie_entrada,codigo_mov_entra… |
| PNotaCred.frm | 7679 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| PNotaCred.frm | 7725 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| Visualiza_NotaCred.frm | 6133 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| Visualiza_CargaMovStock.frm | 5899 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| Visualiza_CargaMovStock.frm | 6155 | UPDATE | conn.Execute "UPDATE serie_entrada a " & _ |
| Visualiza_CargaMovStock.frm | 6225 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| Visualiza_CargaMovStock.frm | 6248 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| FacturaB_COPIA.frm | 16697 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| Serie_salida.frm | 612 | SELECT | "From serie_entrada " & _ |
| Serie_salida.frm | 647 | SELECT | "From serie_entrada " & _ |
| Serie_salida.frm | 938 | SELECT | dataSerie.RecordSource = "SELECT * FROM serie_entrada " & _ |
| NotaCred_COPIA.frm | 12369 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| NotaCred_COPIA.frm | 12415 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| TPV.frm | 33850 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| TPV.frm | 33897 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| TPV.frm | 33943 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| Visualiza_FB_Copia.frm | 7862 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| Visualiza_FB_Copia.frm | 7885 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| PRemito.frm | 6658 | INSERT | conn.Execute "INSERT INTO serie_entrada " & _ |
| PRemito.frm | 6687 | SELECT | "From serie_entrada " & _ |
| Visualiza_PNotaCredDev.frm | 6324 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| Visualiza_PNotaCredDev.frm | 6360 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| Serie_carga.frm | 547 | SELECT | rs_repite.Open "SELECT id_serie_entrada FROM serie_entrada "… |
| Serie_carga.frm | 566 | SELECT | "From serie_entrada " & _ |
| FacturaB.frm | 22771 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| NotaCred_SinCompO.frm | 14680 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| NotaCred_SinCompO.frm | 14726 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| FacturaA.frm | 19383 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| Serie_salida_visualiza.frm | 613 | SELECT | "FROM serie_entrada " & _ |
| Serie_salida_visualiza.frm | 710 | SELECT | dataSerie.RecordSource = "SELECT * FROM serie_entrada " & _ |
| Serie_salida_visualiza.frm | 1442 | SELECT | "FROM serie_entrada " & _ |
| Serie_salida_visualiza.frm | 1526 | SELECT | "FROM serie_entrada " & _ |
| Visualiza_FA.frm | 7706 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| Visualiza_FA.frm | 7729 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| NotaCredCopia.frm | 13544 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| NotaCredCopia.frm | 13590 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| Remito.frm | 10844 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| Sup_importacion_tablas.frm | 11742 | SELECT | rs_serie_entrada.Open "SELECT * FROM serie_entrada WHERE nro… |
| Sup_importacion_tablas.frm | 11747 | SELECT | rs_serie_entrada.Open "SELECT * FROM serie_entrada WHERE id_… |
| Serie_carga_visualiza.frm | 467 | SELECT | rs_repite.Open "SELECT id_serie_entrada FROM serie_entrada "… |
| Serie_carga_visualiza.frm | 487 | SELECT | '                       "From serie_entrada " & _ |
| Serie_carga_visualiza.frm | 545 | UPDATE | '        conn.Execute "UPDATE serie_entrada a " & _ |
| Visualiza_FB.frm | 8397 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| Visualiza_FB.frm | 8420 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| PFactura.frm | 10359 | INSERT | conn.Execute "INSERT INTO serie_entrada " & _ |
| PFactura.frm | 10388 | SELECT | "From serie_entrada " & _ |
| Visualiza_RemitoCopia.frm | 6242 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| Visualiza_RemitoCopia.frm | 6265 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| ConsultaComprobante.frm | 21702 | SELECT | rs_cons_serie.Open "SELECT id_serie_entrada,codigo_mov_entra… |
| ConsultaComprobante.frm | 29976 | SELECT | rs_cons_serie.Open "SELECT id_serie_entrada,codigo_mov_entra… |
| ConsultaComprobante.frm | 30950 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| ConsultaComprobante.frm | 30967 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| ConsultaComprobante.frm | 30980 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| ConsultaComprobante.frm | 30993 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| ConsultaComprobante.frm | 31024 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| ConsultaComprobante.frm | 31049 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| ConsultaComprobante.frm | 31066 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| ConsultaComprobante.frm | 31083 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| NotaDeb.frm | 11448 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| Visualiza_PFactura_Copia.frm | 6069 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| Visualiza_PFactura_Copia.frm | 7802 | UPDATE | conn.Execute "UPDATE serie_entrada a " & _ |
| Visualiza_NotaCredCopia.frm | 5823 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| NotaCred.frm | 14137 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| NotaCred.frm | 14183 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| PNotaCredCopia.frm | 2661 | SELECT | rs_cons_serie.Open "SELECT id_serie_entrada,codigo_mov_entra… |
| PNotaCredCopia.frm | 2679 | SELECT | rs_cons_serie.Open "SELECT id_serie_entrada,codigo_mov_entra… |
| PNotaCredCopia.frm | 7383 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| PNotaCredCopia.frm | 7429 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| NotaDebCopia.frm | 11090 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| Visualiza_Remito.frm | 6361 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| Visualiza_Remito.frm | 6384 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| CargaMovStock.frm | 8459 | INSERT | conn.Execute "INSERT INTO serie_entrada " & _ |
| CargaMovStock.frm | 8487 | SELECT | "From serie_entrada " & _ |
| CargaMovStock.frm | 8528 | UPDATE | conn.Execute "UPDATE serie_entrada " & _ |
| CargaMovStock.frm | 8564 | INSERT | conn.Execute "INSERT INTO serie_entrada " & _ |
| … | … | … | *(21 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)