# Tabla `deposito`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| CodDeposito | INT | No | ✓ |  |  |
| NombreDeposito | VARCHAR | No |  |  |  |
| Descripcion | TEXT | No |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |

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
| Info_Stock.frm | 11673 | SELECT | DataDeposito.RecordSource = "SELECT * FROM deposito WHERE de… |
| PNotaCred.frm | 4666 | SELECT | Data_Deposito.RecordSource = "SELECT * FROM deposito " & _ |
| PNotaCred.frm | 4670 | SELECT | Data_Deposito.RecordSource = "SELECT * FROM deposito Where A… |
| PNotaCred.frm | 4682 | SELECT | Data_Deposito.RecordSource = "SELECT * FROM deposito where C… |
| CargaUsuario.frm | 2108 | SELECT | data_deposito.RecordSource = "SELECT * FROM deposito WHERE  … |
| Visualiza_CargaMovStock.frm | 2722 | SELECT | DataDepositoO.RecordSource = "SELECT * FROM Deposito WHERE  … |
| Visualiza_CargaMovStock.frm | 2729 | SELECT | DataDepositoO.RecordSource = "SELECT * FROM deposito where C… |
| Visualiza_CargaMovStock.frm | 3979 | SELECT | DataDepositoD.RecordSource = "SELECT * FROM Deposito WHERE  … |
| Visualiza_CargaMovStock.frm | 4024 | SELECT | DataDepositoD.RecordSource = "SELECT * FROM Deposito WHERE  … |
| Visualiza_CargaMovStock.frm | 4492 | SELECT | DataDepositoD.RecordSource = "SELECT * FROM Deposito WHERE  … |
| NotaCred_COPIA.frm | 6979 | SELECT | data_deposito.RecordSource = "SELECT * FROM deposito " & _ |
| NotaCred_COPIA.frm | 6983 | SELECT | data_deposito.RecordSource = "SELECT * FROM deposito Where A… |
| NotaCred_COPIA.frm | 6995 | SELECT | data_deposito.RecordSource = "SELECT * FROM deposito where C… |
| Visualiza_Pedido.frm | 3947 | JOIN | " LEFT JOIN deposito ON (deposito.coddeposito = stock_deposi… |
| Visualiza_Pedido.frm | 10728 | JOIN | "LEFT JOIN deposito ON (deposito.CodDeposito = cliente_datos… |
| Visualiza_Pedido.frm | 11079 | JOIN | '            " LEFT JOIN deposito ON (deposito.coddeposito =… |
| Visualiza_Pedido.frm | 11108 | JOIN | '            " LEFT JOIN deposito ON (deposito.coddeposito =… |
| Visualiza_Pedido.frm | 11126 | JOIN | '            " LEFT JOIN deposito ON (deposito.coddeposito =… |
| Visualiza_Pedido.frm | 12801 | JOIN | '            " LEFT JOIN deposito ON (deposito.coddeposito =… |
| AsigUsrDeposito.frm | 616 | SELECT | DataDeposito.RecordSource = "SELECT * FROM Deposito WHERE  a… |
| AsigUsrDeposito.frm | 630 | JOIN | "LEFT JOIN deposito ON (deposito.codDeposito = deposito_usr.… |
| AsigUsrDeposito.frm | 772 | SELECT | "FROM Deposito WHERE anulado = 'No' " |
| Logi_Info.frm | 1341 | SELECT | data_deposito.RecordSource = "SELECT * FROM deposito  " & _ |
| Configuracion2.frm | 5427 | JOIN | '                                     "LEFT JOIN deposito ON… |
| Configuracion.frm | 5526 | JOIN | '                                     "LEFT JOIN deposito ON… |
| CargaArticulo_Original.frm | 7111 | JOIN | "INNER JOIN deposito ON (deposito_reposicion.id_deposito = d… |
| CargaArticulo_Original.frm | 7142 | JOIN | "INNER JOIN deposito ON (deposito_reposicion.id_deposito = d… |
| CargaArticulo_Original.frm | 7201 | JOIN | "INNER JOIN deposito ON (deposito_reposicion.id_deposito = d… |
| CargaArticulo_Original.frm | 7232 | JOIN | "INNER JOIN deposito ON (deposito_reposicion.id_deposito = d… |
| CargaArticulo_Original.frm | 8687 | SELECT | rs_deposito_combo.Open "SELECT * FROM deposito WHERE anulado… |
| CargaArticulo_Original.frm | 9547 | SELECT | rs_deposito.Open "SELECT * FROM deposito", conn, adOpenDynam… |
| CargaArticulo_Original.frm | 9898 | SELECT | rs_deposito.Open "SELECT * FROM deposito WHERE  anulado = 'N… |
| CargaArticulo_Original.frm | 13481 | JOIN | "INNER JOIN deposito ON (deposito_reposicion.id_deposito = d… |
| CargaArticulo_Original.frm | 13500 | JOIN | "INNER JOIN deposito ON (deposito_reposicion.id_deposito = d… |
| CargaArticulo_Original.frm | 13521 | JOIN | "INNER JOIN deposito ON (deposito_reposicion.id_deposito = d… |
| Carga_DatosAdicionales.frm | 1655 | SELECT | DataDepositoO.RecordSource = "SELECT * FROM Deposito WHERE  … |
| Carga_DatosAdicionales.frm | 1662 | SELECT | DataDepositoO.RecordSource = "SELECT * FROM deposito where C… |
| Carga_DatosAdicionales.frm | 2846 | JOIN | ''                  "LEFT JOIN deposito ON (deposito.codDepo… |
| ABMArticulo_seleccion.frm | 3459 | JOIN | " LEFT JOIN deposito ON (deposito.coddeposito = stock_deposi… |
| ABMArticulo_seleccion.frm | 3483 | JOIN | " LEFT JOIN deposito ON (deposito.coddeposito = stock_deposi… |
| ABMArticulo_seleccion.frm | 4714 | SELECT | Data_Stock.RecordSource = "SELECT * FROM Deposito WHERE  anu… |
| ABMArticulo_seleccion.frm | 4721 | SELECT | Data_Stock.RecordSource = "SELECT * FROM deposito where CodD… |
| Articulo.frm | 7223 | SELECT | DataDeposito.RecordSource = "SELECT * FROM deposito " & _ |
| Articulo.frm | 7227 | SELECT | DataDeposito.RecordSource = "SELECT * FROM Deposito WHERE an… |
| Articulo.frm | 7242 | SELECT | DataDeposito.RecordSource = "SELECT * FROM deposito where an… |
| Articulo.frm | 8509 | JOIN | " LEFT JOIN deposito ON (deposito.coddeposito = stock_deposi… |
| En_Carga_Config_Produccion.frm | 1346 | SELECT | cargo_data_dep_abm = "SELECT * FROM deposito WHERE deposito.… |
| Stock_Control.frm | 1911 | JOIN | '        " LEFT JOIN deposito ON (deposito.coddeposito = sto… |
| Stock_Control.frm | 2090 | JOIN | " LEFT JOIN deposito ON (deposito.coddeposito = stock_deposi… |
| Info_Venta_respaldo_bruno.frm | 10186 | SELECT | DataDeposito.RecordSource = "select * from Deposito WHERE an… |
| PRemito.frm | 5352 | SELECT | Data_Deposito.RecordSource = "SELECT * FROM deposito " & _ |
| PRemito.frm | 5356 | SELECT | Data_Deposito.RecordSource = "SELECT * FROM deposito Where A… |
| PRemito.frm | 5368 | SELECT | Data_Deposito.RecordSource = "SELECT * FROM deposito where C… |
| PRemito.frm | 6960 | JOIN | '            " LEFT JOIN deposito ON (deposito.coddeposito =… |
| Lista_Confeccion_OC_Gral.frm | 751 | SELECT | data_deposito.RecordSource = "SELECT * FROM deposito WHERE d… |
| Lista_Confeccion_OC_Gral.frm | 1097 | JOIN | " LEFT JOIN deposito ON (deposito.coddeposito = stock_deposi… |
| Info_Venta.frm | 10045 | SELECT | rs_deposito_combo.Open "SELECT * FROM deposito WHERE anulado… |
| Info_Venta.frm | 10275 | SELECT | '    DataDeposito.RecordSource = "select * from Deposito WHE… |
| FacturaB.frm | 27024 | JOIN | '            " LEFT JOIN deposito ON (deposito.coddeposito =… |
| NotaCred_SinCompO.frm | 8613 | SELECT | Data_Deposito.RecordSource = "SELECT * FROM deposito " & _ |
| NotaCred_SinCompO.frm | 8617 | SELECT | Data_Deposito.RecordSource = "SELECT * FROM deposito Where A… |
| NotaCred_SinCompO.frm | 8629 | SELECT | Data_Deposito.RecordSource = "SELECT * FROM deposito where C… |
| FacturaA.frm | 22785 | JOIN | '            " LEFT JOIN deposito ON (deposito.coddeposito =… |
| CargaDeposito.frm | 248 | SELECT | rs_deposito.Open "SELECT * FROM deposito WHERE CodDeposito=0… |
| CargaDeposito.frm | 299 | SELECT | ABMDeposito.DataDeposito.RecordSource = "SELECT * FROM depos… |
| CargaDeposito.frm | 312 | SELECT | rs_deposito.Open "SELECT * FROM deposito WHERE CodDeposito="… |
| En_GeneraOE.frm | 2209 | SELECT | DataDepositoO.RecordSource = "SELECT * FROM Deposito WHERE  … |
| En_GeneraOE.frm | 2216 | SELECT | DataDepositoO.RecordSource = "SELECT * FROM deposito where C… |
| En_GeneraOE.frm | 2237 | SELECT | DataDepositoD.RecordSource = "SELECT * FROM Deposito WHERE  … |
| En_GeneraOE.frm | 2244 | SELECT | DataDepositoD.RecordSource = "SELECT * FROM deposito where C… |
| En_GeneraOE.frm | 2262 | SELECT | '        Data_Stock.RecordSource = "SELECT * FROM Deposito O… |
| En_GeneraOE.frm | 2269 | SELECT | '        Data_Stock.RecordSource = "SELECT * FROM deposito w… |
| En_GeneraOE.frm | 4854 | JOIN | "LEFT JOIN Deposito ON (deposito.codDeposito = en_orden.id_d… |
| En_GeneraOE.frm | 5120 | JOIN | " LEFT JOIN deposito ON deposito.CodDeposito=stock_deposito.… |
| stock_consulta_avanzada.frm | 2064 | JOIN | " LEFT JOIN deposito ON (deposito.coddeposito = stock_deposi… |
| stock_consulta_avanzada.frm | 2169 | SELECT | Data_Deposito.RecordSource = "SELECT * FROM deposito WHERE d… |
| VariacionPrecio.frm | 7178 | SELECT | rs_deposito.Open "select * from deposito", conn, adOpenDynam… |
| Exportacion.frm | 2257 | SELECT | Data_Deposito.RecordSource = "SELECT * FROM deposito WHERE d… |
| Exportacion.frm | 7659 | JOIN | " LEFT JOIN deposito ON (deposito.coddeposito = stock_deposi… |
| Inventario.frm | 1777 | SELECT | DataDepositoO.RecordSource = "SELECT * FROM Deposito ORDER B… |
| … | … | … | *(164 referencias más)* |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| api_views.py | 686 | SELECT | FROM deposito |
| management/commands/verify_reservado_por_deposito.py | 62 | JOIN | LEFT JOIN deposito d ON d.CodDeposito = sd.id_deposito |
| management/commands/verify_reservado_por_deposito.py | 130 | JOIN | LEFT JOIN deposito d ON d.CodDeposito = sp.CodDeposito |
| services/query_runner.py | 3438 | SELECT | FROM deposito d |
| services/query_runner.py | 3596 | SELECT | SELECT COUNT(*) FROM deposito WHERE (anulado IS NULL OR anul… |

[← Índice de tablas](../DB_INDICE_TABLAS.md)