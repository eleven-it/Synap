# Tabla `serie_movimiento`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_serie_mov | DOUBLE | No | ✓ |  |  |
| id_serie_entrada | DOUBLE | Sí |  |  |  |
| id_articulo | FLOAT | Sí |  |  |  |
| nro_serie | VARCHAR | Sí |  |  |  |
| vto_serie | DATE | Sí |  |  |  |
| desc_serie | VARCHAR | Sí |  |  |  |
| tipo_comprobante | VARCHAR | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
| codigo_mov_vta | DOUBLE | Sí |  |  |  |
| codigo_mov_compra | DOUBLE | Sí |  |  |  |
| codigo_mov_mstock | DOUBLE | Sí |  |  |  |
| codigo_mov_rem | DOUBLE | Sí |  |  |  |
| tipo_comp_desc | VARCHAR | Sí |  |  |  |
| id_cliente | DOUBLE | Sí |  |  |  |
| id_proveedor | DOUBLE | Sí |  |  |  |
| comprobante | VARCHAR | Sí |  |  |  |
| nro_comprobante | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| modificado | VARCHAR | Sí |  |  |  |
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
| PNotaCred.frm | 7656 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| PNotaCred.frm | 7670 | SELECT | "From serie_movimiento " & _ |
| PNotaCred.frm | 7685 | SELECT | "FROM serie_movimiento " & _ |
| PNotaCred.frm | 7689 | UPDATE | conn.Execute "UPDATE serie_movimiento " & _ |
| PNotaCred.frm | 7702 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| PNotaCred.frm | 7738 | UPDATE | conn.Execute "UPDATE serie_movimiento " & _ |
| Visualiza_NotaCred.frm | 6105 | SELECT | "FROM serie_movimiento a " & _ |
| Visualiza_NotaCred.frm | 6167 | UPDATE | conn.Execute "UPDATE serie_movimiento " & _ |
| Visualiza_NotaCred.frm | 6184 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| Visualiza_CargaMovStock.frm | 6168 | UPDATE | conn.Execute "UPDATE serie_movimiento a " & _ |
| Visualiza_CargaMovStock.frm | 6194 | SELECT | "FROM serie_movimiento a " & _ |
| Visualiza_CargaMovStock.frm | 6230 | UPDATE | conn.Execute "UPDATE serie_movimiento " & _ |
| Visualiza_CargaMovStock.frm | 6264 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| FacturaB_COPIA.frm | 16672 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| Serie_salida.frm | 692 | SELECT | "FROM serie_movimiento " & _ |
| Serie_salida.frm | 728 | SELECT | "FROM serie_movimiento " & _ |
| Serie_salida.frm | 1401 | SELECT | dataSerie.RecordSource = "SELECT * FROM serie_movimiento " &… |
| Serie_salida.frm | 1517 | SELECT | dataSerie.RecordSource = "SELECT * FROM serie_movimiento " &… |
| NotaCred_COPIA.frm | 12349 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| NotaCred_COPIA.frm | 12362 | SELECT | "From serie_movimiento " & _ |
| NotaCred_COPIA.frm | 12374 | SELECT | "FROM serie_movimiento " & _ |
| NotaCred_COPIA.frm | 12378 | UPDATE | conn.Execute "UPDATE serie_movimiento " & _ |
| NotaCred_COPIA.frm | 12392 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| NotaCred_COPIA.frm | 12427 | UPDATE | conn.Execute "UPDATE serie_movimiento " & _ |
| TPV.frm | 33825 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| TPV.frm | 33877 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| TPV.frm | 33890 | SELECT | "From serie_movimiento " & _ |
| TPV.frm | 33902 | SELECT | "FROM serie_movimiento " & _ |
| TPV.frm | 33906 | UPDATE | conn.Execute "UPDATE serie_movimiento " & _ |
| TPV.frm | 33920 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| TPV.frm | 33954 | UPDATE | conn.Execute "UPDATE serie_movimiento " & _ |
| Visualiza_FB_Copia.frm | 7831 | SELECT | "FROM serie_movimiento a " & _ |
| Visualiza_FB_Copia.frm | 7867 | UPDATE | conn.Execute "UPDATE serie_movimiento " & _ |
| Visualiza_FB_Copia.frm | 7901 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| PRemito.frm | 6675 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| Visualiza_PNotaCredDev.frm | 6296 | SELECT | "FROM serie_movimiento a " & _ |
| Visualiza_PNotaCredDev.frm | 6333 | UPDATE | conn.Execute "UPDATE serie_movimiento " & _ |
| Visualiza_PNotaCredDev.frm | 6379 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| FacturaB.frm | 22746 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| NotaCred_SinCompO.frm | 14660 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| NotaCred_SinCompO.frm | 14673 | SELECT | "From serie_movimiento " & _ |
| NotaCred_SinCompO.frm | 14685 | SELECT | "FROM serie_movimiento " & _ |
| NotaCred_SinCompO.frm | 14689 | UPDATE | conn.Execute "UPDATE serie_movimiento " & _ |
| NotaCred_SinCompO.frm | 14703 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| NotaCred_SinCompO.frm | 14738 | UPDATE | conn.Execute "UPDATE serie_movimiento " & _ |
| FacturaA.frm | 19359 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| Serie_salida_visualiza.frm | 619 | JOIN | "INNER JOIN serie_movimiento ON (Serie_movimiento.id_serie_e… |
| Serie_salida_visualiza.frm | 655 | JOIN | "INNER JOIN serie_movimiento ON (serie_movimiento.id_serie_e… |
| Serie_salida_visualiza.frm | 781 | SELECT | "FROM serie_movimiento " & _ |
| Serie_salida_visualiza.frm | 1124 | SELECT | dataSerie.RecordSource = "SELECT * FROM serie_movimiento " &… |
| Serie_salida_visualiza.frm | 1178 | SELECT | "FROM serie_movimiento " & _ |
| Serie_salida_visualiza.frm | 1250 | SELECT | dataSerie.RecordSource = "SELECT * FROM serie_movimiento " &… |
| Serie_salida_visualiza.frm | 1306 | SELECT | "FROM serie_movimiento " & _ |
| Visualiza_FA.frm | 7675 | SELECT | "FROM serie_movimiento a " & _ |
| Visualiza_FA.frm | 7711 | UPDATE | conn.Execute "UPDATE serie_movimiento " & _ |
| Visualiza_FA.frm | 7745 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| NotaCredCopia.frm | 13524 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| NotaCredCopia.frm | 13537 | SELECT | "From serie_movimiento " & _ |
| NotaCredCopia.frm | 13549 | SELECT | "FROM serie_movimiento " & _ |
| NotaCredCopia.frm | 13553 | UPDATE | conn.Execute "UPDATE serie_movimiento " & _ |
| NotaCredCopia.frm | 13567 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| NotaCredCopia.frm | 13602 | UPDATE | conn.Execute "UPDATE serie_movimiento " & _ |
| Remito.frm | 10821 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| Visualiza_FB.frm | 8366 | SELECT | "FROM serie_movimiento a " & _ |
| Visualiza_FB.frm | 8402 | UPDATE | conn.Execute "UPDATE serie_movimiento " & _ |
| Visualiza_FB.frm | 8436 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| PFactura.frm | 10376 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| Visualiza_RemitoCopia.frm | 6211 | SELECT | "FROM serie_movimiento a " & _ |
| Visualiza_RemitoCopia.frm | 6247 | UPDATE | conn.Execute "UPDATE serie_movimiento " & _ |
| Visualiza_RemitoCopia.frm | 6281 | INSERT | conn.Execute "INSERT INTO serie_movimiento " & _ |
| ConsultaComprobante.frm | 17276 | SELECT | "FROM serie_movimiento " & _ |
| ConsultaComprobante.frm | 18217 | SELECT | "FROM serie_movimiento " & _ |
| ConsultaComprobante.frm | 20857 | SELECT | '           rs_cons_serie.Open "SELECT id_serie_mov,codigo_m… |
| ConsultaComprobante.frm | 24515 | SELECT | "FROM serie_movimiento " & _ |
| ConsultaComprobante.frm | 27281 | SELECT | "FROM serie_movimiento " & _ |
| ConsultaComprobante.frm | 30955 | UPDATE | conn.Execute "UPDATE serie_movimiento " & _ |
| ConsultaComprobante.frm | 30972 | UPDATE | conn.Execute "UPDATE serie_movimiento " & _ |
| ConsultaComprobante.frm | 30985 | UPDATE | conn.Execute "UPDATE serie_movimiento " & _ |
| ConsultaComprobante.frm | 30998 | SELECT | "SELECT id_serie_entrada FROM serie_movimiento " & _ |
| ConsultaComprobante.frm | 31002 | UPDATE | conn.Execute "UPDATE serie_movimiento " & _ |
| … | … | … | *(80 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)