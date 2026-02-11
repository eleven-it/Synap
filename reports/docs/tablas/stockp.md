# Tabla `stockp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_stock | DOUBLE | No | ✓ |  |  |
| IDArt | INT | Sí |  |  |  |
| Fecha | DATE | Sí |  |  |  |
| CodigoArticulo | VARCHAR | Sí |  |  |  |
| CodigoMovimiento | DECIMAL | Sí |  |  |  |
| codigo_movimiento_anul | DECIMAL | Sí |  |  |  |
| Descripcion | VARCHAR | Sí |  |  |  |
| Entrada | DECIMAL | Sí |  |  |  |
| Salida | DECIMAL | Sí |  |  |  |
| saldo | DECIMAL | Sí |  |  |  |
| DescRenglon | DECIMAL | Sí |  |  |  |
| ImpDesc | DECIMAL | Sí |  |  |  |
| PorDesc | DECIMAL | Sí |  |  |  |
| PrecioCostoxU | DECIMAL | Sí |  |  |  |
| PrecioVentaxU | DECIMAL | Sí |  |  |  |
| PrecioBrutoxU | DECIMAL | Sí |  |  |  |
| PrecioIVAxU | DECIMAL | Sí |  |  |  |
| PrecioNetoxU | DECIMAL | Sí |  |  |  |
| PrecioCostoxR | DECIMAL | Sí |  |  |  |
| PrecioVentaxR | DECIMAL | Sí |  |  |  |
| PrecioBrutoxR | DECIMAL | Sí |  |  |  |
| PrecioNetoxR | DECIMAL | Sí |  |  |  |
| PrecioIVAxR | DECIMAL | Sí |  |  |  |
| ImpIB | DECIMAL | Sí |  |  |  |
| NetoIB | DECIMAL | Sí |  |  |  |
| Alicuota | DECIMAL | Sí |  |  |  |
| AlicuotaIB | DECIMAL | Sí |  |  |  |
| Cantidad | DECIMAL | Sí |  |  |  |
| CantNC | DECIMAL | Sí |  |  |  |
| CodigoCP | INT | Sí |  |  |  |
| Tipo | VARCHAR | Sí |  |  |  |
| Comprobante | VARCHAR | Sí |  |  |  |
| TipoComp | VARCHAR | Sí |  |  |  |
| NroComprobante | VARCHAR | Sí |  |  |  |
| Anulado | VARCHAR | Sí |  |  |  |
| TipoIVA | VARCHAR | Sí |  |  |  |
| CodDeposito | INT | Sí |  |  |  |
| FechaControl | TIMESTAMP | No |  |  |  |
| IdUsuario | INT | Sí |  |  |  |
| CodSucursal | INT | Sí |  |  |  |
| NroPresupuesto | VARCHAR | Sí |  |  |  |
| NroPedido | VARCHAR | Sí |  |  |  |
| Orden | INT | Sí |  |  |  |
| CodViajante | INT | Sí |  |  |  |
| CodLaboratorio | INT | Sí |  |  |  |
| id_lote | INT | Sí |  |  |  |
| codmov_presupuesto | INT | Sí |  |  |  |
| codmov_pedido | INT | Sí |  |  |  |
| tipo_art | VARCHAR | Sí |  |  |  |
| detalle | MEDIUMTEXT | Sí |  |  |  |
| imp_alicuota_iva | DECIMAL | Sí |  |  |  |
| imp_alicuota_iibb | DECIMAL | Sí |  |  |  |
| id_manual | VARCHAR | Sí |  |  |  |
| lista_precio | INT | Sí |  |  |  |
| promocion | VARCHAR | Sí |  |  |  |
| promocion_por | DECIMAL | Sí |  |  |  |
| promocion_tipo | VARCHAR | Sí |  |  |  |
| promocion_cant | DECIMAL | Sí |  |  |  |
| remitido_facturado | VARCHAR | Sí |  |  |  |
| seleccionado | INT | Sí |  |  |  |
| impuesto_interno | DECIMAL | Sí |  |  |  |
| impuesto_interno_subtotal | DECIMAL | Sí |  |  |  |
| CodigoGasto | INT | Sí |  |  |  |
| impdesc_bonif | DECIMAL | Sí |  |  |  |
| pordesc_bonif | DECIMAL | Sí |  |  |  |
| multiplicador_comp | DECIMAL | Sí |  |  |  |
| multiplicador_vta | DECIMAL | Sí |  |  |  |
| cantidad_uni | DECIMAL | Sí |  |  |  |
| cantidad_entregada | DOUBLE | Sí |  |  |  |
| id_unimed | DOUBLE | Sí |  |  |  |
| id_presentacion | DOUBLE | Sí |  |  |  |
| id_unimed_vta | DOUBLE | Sí |  |  |  |
| id_unimed_comp | DOUBLE | Sí |  |  |  |
| id_presentacion_vta | DOUBLE | Sí |  |  |  |
| id_presentacion_comp | DOUBLE | Sí |  |  |  |
| nombre_unimed_vta | VARCHAR | Sí |  |  |  |
| nombre_unimed_comp | VARCHAR | Sí |  |  |  |
| nombre_presentacion_vta | VARCHAR | Sí |  |  |  |
| nombre_presentacion_comp | VARCHAR | Sí |  |  |  |
| cantidad_pendiente | DECIMAL | Sí |  |  |  |
| unidad_art_peso | DOUBLE | Sí |  |  |  |
| ped_eco | BIGINT | Sí |  |  |  |
| nro_despacho | VARCHAR | Sí |  |  |  |
| coti_dolar | DOUBLE | Sí |  |  |  |
| serie | VARCHAR | Sí |  |  |  |
| id_cotizacion | INT | Sí |  |  |  |
| tipo_unidad | VARCHAR | Sí |  |  |  |
| cantidad_unidad_display | DOUBLE | Sí |  |  |  |
| cantidad_dividir | DOUBLE | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| crm_articulo | stockp | Crm_Presupuesto_Llamada.frm | 681 | 'SELECT * FROM crm_articulo INNER JOIN articulo ON (crm_articulo.id_articulo = a… |
| crm_articulo | stockp | Crm_Presupuesto_Llamada.frm | 692 | rs_stock.Open "SELECT * FROM crm_articulo INNER JOIN articulo ON (crm_articulo.i… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| Erp_Carga_Parte_Diario.frm | 3396 | JOIN | '                                        "LEFT JOIN stockp A… |
| Erp_Carga_Parte_Diario.frm | 4322 | JOIN | '                       "LEFT JOIN stockp AS st ON (rec.`id_… |
| FacturaB_COPIA.frm | 4517 | SELECT | rs_consulta_pedido_cliente.Open "SELECT stockp.CodigoMovimie… |
| FacturaB_COPIA.frm | 4905 | SELECT | rs_stockp.Open "SELECT * FROM stockp WHERE stockp.id_stock =… |
| FacturaB_COPIA.frm | 4911 | SELECT | '                                                    " FROM … |
| FacturaB_COPIA.frm | 5084 | SELECT | rs_stock_facturado.Open "SELECT stockp.IDArt FROM stockp WHE… |
| Pedido_prep_consulta.frm | 1635 | JOIN | '                                        "LEFT JOIN stockp O… |
| Pedido_prep_consulta.frm | 1641 | JOIN | "LEFT JOIN stockp ON (stockp.CodigoMovimiento = comp_ped.Cod… |
| Pedido_prep_consulta.frm | 2020 | SELECT | "FROM stockp " & _ |
| Pedido_prep_consulta.frm | 2217 | SELECT | " FROM stockp " & _ |
| Pedido_prep_consulta.frm | 2224 | SELECT | Data_Renglon.RecordSource = "SELECT * FROM stockp WHERE Codi… |
| NotaCred_COPIA.frm | 3593 | SELECT | rs_mod_stockp.Open "SELECT stockp.cantidad_pendiente,stockp.… |
| TPV.frm | 6723 | SELECT | '                    rs_stockp.Open "SELECT * FROM stockp WH… |
| TPV.frm | 9509 | SELECT | rs_consulta_pedido_cliente.Open "SELECT stockp.CodigoMovimie… |
| TPV.frm | 9853 | SELECT | rs_stockp.Open "SELECT * FROM stockp WHERE stockp.id_stock =… |
| TPV.frm | 10176 | SELECT | rs_stock_facturado.Open "SELECT stockp.IDArt FROM stockp WHE… |
| TPV.frm | 40230 | SELECT | '            rs_stockp.Open "SELECT * FROM stockp WHERE stoc… |
| Logi_Gestion2.frm | 6884 | SELECT | " FROM stockp " & _ |
| Logi_Gestion2.frm | 6891 | SELECT | Data_Renglon.RecordSource = "SELECT * FROM stockp WHERE Codi… |
| Logi_Gestion2.frm | 6953 | SELECT | " FROM stockp " & _ |
| Logi_Gestion2.frm | 6986 | SELECT | " FROM stockp " & _ |
| Logi_Gestion2.frm | 9381 | SELECT | "From stockp " & _ |
| Logi_Gestion2.frm | 9403 | SELECT | "From stockp " & _ |
| Logi_Gestion2.frm | 9518 | SELECT | '    rs_cant.Open "SELECT GROUP_CONCAT(CAST(id_stock AS CHAR… |
| Logi_Gestion2.frm | 9553 | SELECT | "From stockp " & _ |
| Logi_Gestion2.frm | 9581 | SELECT | "From stockp " & _ |
| Logi_Gestion2.frm | 9590 | SELECT | VarMySql1 = "SELECT id_stock FROM stockp WHERE id_stock = 0 … |
| Logi_Gestion2.frm | 9605 | SELECT | '    rs_cant.Open "SELECT GROUP_CONCAT(CAST(id_stock AS CHAR… |
| Logi_Gestion2.frm | 9663 | SELECT | "From stockp " & _ |
| Logi_Gestion2.frm | 9670 | SELECT | VarMySql2 = "SELECT id_stock FROM stockp WHERE id_stock = 0 … |
| Logi_Gestion2.frm | 10205 | SELECT | VarMySql3 = "SELECT id_stock FROM stockp WHERE id_stock = 0 … |
| Logi_Gestion2.frm | 10233 | SELECT | "From stockp " & _ |
| Logi_Gestion2.frm | 10925 | SELECT | '    rs_cant.Open "SELECT GROUP_CONCAT(CAST(id_stock AS CHAR… |
| Logi_Gestion2.frm | 10930 | SELECT | '    rs_cant.Open "SELECT GROUP_CONCAT(CAST(id_stock AS CHAR… |
| Logi_Gestion2.frm | 10946 | SELECT | "FROM stockp " & _ |
| Facturacion_Ciclica.frm | 3873 | SELECT | VarMySql3 = "SELECT id_stock FROM stockp WHERE id_stock = 0 … |
| Visualiza_Pedido.frm | 3944 | JOIN | " LEFT JOIN stockp ON (stockp.CodigoMovimiento = comp_ped.Co… |
| Visualiza_Pedido.frm | 3962 | JOIN | " LEFT JOIN stockp ON (stockp.CodigoMovimiento = comp_ped.Co… |
| Visualiza_Pedido.frm | 3966 | SELECT | '            " FROM stockp WHERE stockp.CodigoMovimiento = "… |
| Visualiza_Pedido.frm | 6993 | SELECT | rs_deposito.Open "SELECT stockp.CodigoMovimiento,stockp.CodD… |
| Visualiza_Pedido.frm | 9668 | SELECT | rs_item.Open "SELECT * FROM stockp WHERE CodigoMovimiento = … |
| Visualiza_Pedido.frm | 9949 | SELECT | '            rs_stock.Open "SELECT * FROM stockp where Codig… |
| Visualiza_Pedido.frm | 9953 | SELECT | rs_consulta_stock.Open "SELECT stockp.id_stock,stockp.Codigo… |
| Visualiza_Pedido.frm | 9962 | SELECT | conn.Execute "DELETE FROM stockp WHERE id_stock = " & rs_con… |
| Visualiza_Pedido.frm | 9962 | DELETE | conn.Execute "DELETE FROM stockp WHERE id_stock = " & rs_con… |
| Visualiza_Pedido.frm | 9980 | SELECT | rs_consulta_stock.Open "SELECT stockp.idart,stockp.id_stock,… |
| Visualiza_Pedido.frm | 10003 | UPDATE | '                                    conn.Execute "UPDATE st… |
| Visualiza_Pedido.frm | 10005 | SELECT | conn.Execute "DELETE FROM stockp WHERE id_stock = " & rs_con… |
| Visualiza_Pedido.frm | 10005 | DELETE | conn.Execute "DELETE FROM stockp WHERE id_stock = " & rs_con… |
| Visualiza_Pedido.frm | 10024 | SELECT | rs_consulta_stock.Open "SELECT stockp.id_stock,stockp.Codigo… |
| Visualiza_Pedido.frm | 10033 | SELECT | conn.Execute "DELETE FROM stockp WHERE id_stock = " & rs_con… |
| Visualiza_Pedido.frm | 10033 | DELETE | conn.Execute "DELETE FROM stockp WHERE id_stock = " & rs_con… |
| Visualiza_Pedido.frm | 10083 | SELECT | '                            rs_stock.Open "SELECT * FROM st… |
| Visualiza_Pedido.frm | 10088 | INSERT | sentencia_tabla = "INSERT INTO stockp " |
| Visualiza_Pedido.frm | 10095 | SELECT | '                            rs_stock.Open "SELECT * FROM st… |
| Visualiza_Pedido.frm | 10098 | UPDATE | sentencia_tabla = "UPDATE stockp " |
| Visualiza_Pedido.frm | 11064 | JOIN | '        " LEFT JOIN stockp ON (stockp.CodigoMovimiento = co… |
| Visualiza_Pedido.frm | 11076 | JOIN | '            " LEFT JOIN stockp ON (stockp.CodigoMovimiento … |
| Visualiza_Pedido.frm | 11091 | JOIN | " LEFT JOIN stockp ON (stockp.CodigoMovimiento = comp_ped.Co… |
| Visualiza_Pedido.frm | 11105 | JOIN | '            " LEFT JOIN stockp ON (stockp.CodigoMovimiento … |
| Visualiza_Pedido.frm | 11123 | JOIN | '            " LEFT JOIN stockp ON (stockp.CodigoMovimiento … |
| Visualiza_Pedido.frm | 11135 | SELECT | rs_stock.Open "SELECT * FROM stockp WHERE CodigoMovimiento =… |
| Visualiza_Pedido.frm | 12762 | JOIN | '        " LEFT JOIN stockp ON (stockp.CodigoMovimiento = co… |
| Visualiza_Pedido.frm | 12789 | JOIN | " LEFT JOIN stockp ON (stockp.CodigoMovimiento = comp_ped.Co… |
| Visualiza_Pedido.frm | 13944 | JOIN | '            " LEFT JOIN stockp ON (stockp.CodigoMovimiento … |
| Visualiza_Pedido.frm | 14334 | SELECT | '            rs_stock.Open "SELECT * FROM stockp where Codig… |
| Visualiza_Pedido.frm | 14732 | SELECT | rs_stock.Open "SELECT * FROM stockp WHERE id_stock = " & id_… |
| Logi_Gestion.frm | 8385 | SELECT | " FROM stockp " & _ |
| Logi_Gestion.frm | 8392 | SELECT | Data_Renglon.RecordSource = "SELECT * FROM stockp WHERE Codi… |
| Logi_Gestion.frm | 8448 | SELECT | " FROM stockp " & _ |
| Logi_Gestion.frm | 8458 | SELECT | "FROM stockp WHERE stockp.CodigoMovimiento = " & DataComprob… |
| Logi_Gestion.frm | 8498 | SELECT | " FROM stockp " & _ |
| Logi_Gestion.frm | 8508 | SELECT | "FROM stockp WHERE stockp.CodigoMovimiento = " & DataComprob… |
| Logi_Gestion.frm | 11037 | SELECT | "From stockp " & _ |
| Logi_Gestion.frm | 11059 | SELECT | "From stockp " & _ |
| Logi_Gestion.frm | 11172 | SELECT | rs_cant.Open "SELECT GROUP_CONCAT(CAST(id_stock AS CHAR) SEP… |
| Logi_Gestion.frm | 11206 | SELECT | "From stockp " & _ |
| Logi_Gestion.frm | 11234 | SELECT | "From stockp " & _ |
| Logi_Gestion.frm | 11243 | SELECT | VarMySql1 = "SELECT id_stock FROM stockp WHERE id_stock = 0 … |
| Logi_Gestion.frm | 11256 | SELECT | rs_cant.Open "SELECT GROUP_CONCAT(CAST(id_stock AS CHAR) SEP… |
| … | … | … | *(265 referencias más)* |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| management/commands/verify_reservado_por_deposito.py | 96 | SELECT | FROM stockp sp |
| management/commands/verify_reservado_por_deposito.py | 111 | SELECT | FROM stockp sp |
| management/commands/verify_reservado_por_deposito.py | 128 | SELECT | FROM stockp sp |
| services/query_runner.py | 3149 | SELECT | FROM stockp sp |
| services/query_runner.py | 3161 | SELECT | FROM stockp sp_oc |
| services/query_runner.py | 3174 | SELECT | FROM stockp sp_res |
| services/query_runner.py | 3281 | SELECT | FROM stockp sp |
| services/query_runner.py | 3332 | SELECT | FROM stockp sp |
| services/query_runner.py | 3385 | SELECT | FROM stockp sp_res |
| services/query_runner.py | 3555 | JOIN | INNER JOIN stockp spr ON spr.CodigoMovimiento = cp.CodigoMov… |
| services/reconciliation_saldo_pedido_proveedor.py | 172 | SELECT | FROM stockp sp |
| services/reconciliation_saldo_pedido_proveedor.py | 194 | JOIN | INNER JOIN stockp sp ON sp.CodigoMovimiento = ocrem.codigo_m… |
| services/reconciliation_saldo_pedido_proveedor.py | 216 | JOIN | INNER JOIN stockp sp ON sp.CodigoMovimiento = ocf.codigo_mov… |
| services/reconciliation_saldo_pedido_proveedor.py | 232 | SELECT | FROM stockp sp |
| services/reconciliation_saldo_pedido_proveedor.py | 253 | SELECT | FROM stockp sp |
| services/reconciliation_saldo_pedido_proveedor.py | 418 | SELECT | FROM stockp sp |
| services/reconciliation_saldo_pedido_proveedor.py | 442 | JOIN | INNER JOIN stockp sp ON sp.CodigoMovimiento = ocrem.codigo_m… |
| services/reconciliation_saldo_pedido_proveedor.py | 466 | JOIN | INNER JOIN stockp sp ON sp.CodigoMovimiento = ocf.codigo_mov… |
| services/reconciliation_saldo_pedido_proveedor.py | 483 | SELECT | FROM stockp sp |

[← Índice de tablas](../DB_INDICE_TABLAS.md)