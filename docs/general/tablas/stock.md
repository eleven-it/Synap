# Tabla `stock`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_stock | BIGINT | No | ✓ |  |  |
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
| NroRemito | VARCHAR | Sí |  |  |  |
| NroPedido | VARCHAR | Sí |  |  |  |
| Orden | INT | Sí |  |  |  |
| CodViajante | INT | Sí |  |  |  |
| CodLaboratorio | INT | Sí |  |  |  |
| CodigoGasto | INT | Sí |  |  |  |
| codmov_remito | DOUBLE | Sí |  |  |  |
| codmov_pedido | DOUBLE | Sí |  |  |  |
| tipo_art | VARCHAR | Sí |  |  |  |
| detalle | MEDIUMTEXT | Sí |  |  |  |
| imp_alicuota_iva | DECIMAL | Sí |  |  |  |
| imp_alicuota_iibb | DECIMAL | Sí |  |  |  |
| id_manual | VARCHAR | Sí |  |  |  |
| codmov_presupuesto | DOUBLE | Sí |  |  |  |
| lista_precio | INT | Sí |  |  |  |
| NroPresupuesto | VARCHAR | Sí |  |  |  |
| promocion_tipo | VARCHAR | Sí |  |  |  |
| promocion | VARCHAR | Sí |  |  |  |
| nro_pedi | VARCHAR | Sí |  |  |  |
| promocion_cant | DECIMAL | Sí |  |  |  |
| promocion_por | DECIMAL | Sí |  |  |  |
| codmov_nro_pedi | DECIMAL | Sí |  |  |  |
| id_ref_movstock | INT | Sí |  |  |  |
| id_lote | INT | Sí |  |  |  |
| stock_lote_deposito | DECIMAL | Sí |  |  |  |
| impuesto_interno | DECIMAL | Sí |  |  |  |
| impuesto_interno_subtotal | DECIMAL | Sí |  |  |  |
| id_stock_nc | DOUBLE | Sí |  |  |  |
| impdesc_bonif | DECIMAL | Sí |  |  |  |
| pordesc_bonif | DECIMAL | Sí |  |  |  |
| no_entregado_fact | VARCHAR | Sí |  |  |  |
| entregado_fact_total | VARCHAR | Sí |  |  |  |
| cantidad_entregada_pend | DECIMAL | Sí |  |  |  |
| codmov_factura | DOUBLE | Sí |  |  |  |
| NroFactura | VARCHAR | Sí |  |  |  |
| id_stock_factura | DOUBLE | Sí |  |  |  |
| id_stockp | DOUBLE | Sí |  |  |  |
| remitido_facturado | VARCHAR | Sí |  |  |  |
| multiplicador_comp | DECIMAL | Sí |  |  |  |
| multiplicador_vta | DECIMAL | Sí |  |  |  |
| cantidad_uni | DECIMAL | Sí |  |  |  |
| id_unimed_vta | DOUBLE | Sí |  |  |  |
| id_unimed_comp | DOUBLE | Sí |  |  |  |
| id_presentacion_vta | DOUBLE | Sí |  |  |  |
| id_presentacion_comp | DOUBLE | Sí |  |  |  |
| nombre_unimed_vta | VARCHAR | Sí |  |  |  |
| nombre_unimed_comp | VARCHAR | Sí |  |  |  |
| nombre_presentacion_vta | VARCHAR | Sí |  |  |  |
| nombre_presentacion_comp | VARCHAR | Sí |  |  |  |
| fecha_elaboracion | DATE | Sí |  |  |  |
| cantidad_entregada_nc | DECIMAL | Sí |  |  |  |
| id_serie_entrada | DOUBLE | Sí |  |  |  |
| desc_serie | MEDIUMTEXT | Sí |  |  |  |
| serie | VARCHAR | Sí |  |  |  |
| visualiza_ensamble | VARCHAR | Sí |  |  |  |
| Ensamblado | VARCHAR | Sí |  |  |  |
| cantidad_en | DOUBLE | Sí |  |  |  |
| id_stock_en_abm | DOUBLE | Sí |  |  |  |
| unidad_art_peso | DOUBLE | Sí |  |  |  |
| NroDev | VARCHAR | Sí |  |  |  |
| nro_despacho | VARCHAR | Sí |  |  |  |
| coti_dolar | DOUBLE | Sí |  |  |  |
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
| stock | cuentaproveedor | Info_Estadistica.frm | 3854 | '                                                                               … |
| stock | cuentaproveedor | Info_Estadistica.frm | 4097 | "From Stock LEFT JOIN cuentaproveedor ON (cuentaproveedor.CodigoMovimiento = sto… |
| stock | cuentaproveedor | Info_Banco.frm | 2944 | "From Stock LEFT JOIN cuentaproveedor ON (cuentaproveedor.CodigoMovimiento = sto… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| PNotaCred.frm | 2741 | SELECT | rs_cons_lote.Open "SELECT stock.id_stock,stock.id_lote,stock… |
| PNotaCred.frm | 2745 | SELECT | rs_cons_lote_vend.Open "SELECT stock.TipoComp,stock.id_stock… |
| PNotaCred.frm | 3048 | SELECT | rs_stock.Open "SELECT * FROM stock where CodigoMovimiento = … |
| PNotaCred.frm | 3129 | SELECT | rs_stock_nc.Open "SELECT * FROM stock where CodigoMovimiento… |
| PNotaCred.frm | 3298 | SELECT | rs_stocklote.Open "SELECT * from stock where CodigoMovimient… |
| PNotaCred.frm | 5991 | SELECT | rs_item.Open "SELECT * FROM stock WHERE CodigoMovimiento = "… |
| PNotaCred.frm | 7716 | JOIN | "INNER JOIN stock ON (stock.codigoMovimiento = " & contador … |
| Stock_Control_Entrada.frm | 763 | JOIN | " LEFT JOIN stock ON (stock.CodigoMovimiento = cuentacliente… |
| Visualiza_ReciboCobro.frm | 10989 | SELECT | rs_stock.Open "SELECT * FROM stock WHERE stock.CodigoMovimie… |
| Visualiza_ReciboCobro.frm | 11113 | SELECT | rs_stock.Open "SELECT * FROM stock WHERE stock.CodigoMovimie… |
| Visualiza_ReciboCobro.frm | 11365 | SELECT | rs_stock.Open "SELECT * FROM stock WHERE stock.CodigoMovimie… |
| Visualiza_ReciboCobro.frm | 11456 | SELECT | rs_stock.Open "SELECT * FROM stock WHERE stock.CodigoMovimie… |
| Visualiza_ReciboCobro.frm | 11706 | SELECT | '        rs_stock.Open "SELECT * FROM stock WHERE stock.Codi… |
| Visualiza_ReciboCobro.frm | 12382 | SELECT | rs_stock.Open "SELECT * FROM stock WHERE stock.CodigoMovimie… |
| Visualiza_NotaCred.frm | 4716 | SELECT | 'rs_stock.Open "SELECT * FROM stock WHERE IDArt = " & , conn… |
| Visualiza_NotaCred.frm | 4922 | SELECT | rs_item.Open "SELECT * FROM stock WHERE CodigoMovimiento = "… |
| Info_Estadistica.frm | 3854 | SELECT | '                                                           … |
| Info_Estadistica.frm | 4097 | SELECT | "From Stock LEFT JOIN cuentaproveedor ON (cuentaproveedor.Co… |
| Info_Estadistica.frm | 7149 | JOIN | "LEFT JOIN stock on (stock.CodigoCP = cliente.Codigo) " & _ |
| Info_Estadistica.frm | 7175 | JOIN | "LEFT JOIN stock on (stock.CodigoCP = cliente.Codigo) " & _ |
| Info_Estadistica.frm | 7202 | JOIN | "LEFT JOIN stock on (stock.CodigoCP = cliente.Codigo) " & _ |
| Info_Estadistica.frm | 7604 | JOIN | "LEFT JOIN stock on (stock.CodigoCP = cliente.Codigo) " & _ |
| Info_Estadistica.frm | 7630 | JOIN | "LEFT JOIN stock on (stock.CodigoCP = cliente.Codigo) " & _ |
| Info_Estadistica.frm | 7657 | JOIN | "LEFT JOIN stock on (stock.CodigoCP = cliente.Codigo) " & _ |
| Info_Estadistica.frm | 8754 | SELECT | " FROM `stock` " & _ |
| Info_Estadistica.frm | 8773 | SELECT | " FROM `stock` " & _ |
| Info_Estadistica.frm | 8790 | SELECT | " FROM `stock` " & _ |
| Info_Estadistica.frm | 8934 | SELECT | " FROM `stock` " & _ |
| Info_Estadistica.frm | 8955 | SELECT | " FROM `stock` " & _ |
| Info_Estadistica.frm | 8974 | SELECT | " FROM `stock` " & _ |
| Visualiza_CargaMovStock.frm | 2955 | SELECT | rs_stock.Open "SELECT * FROM stock where CodigoMovimiento = … |
| Visualiza_CargaMovStock.frm | 5907 | SELECT | rs_item.Open "SELECT * FROM stock WHERE CodigoMovimiento = "… |
| FacturaB_COPIA.frm | 4465 | SELECT | rs_stock.Open "SELECT * FROM stock where CodigoMovimiento = … |
| FacturaB_COPIA.frm | 4912 | JOIN | '                                                    " LEFT … |
| FacturaB_COPIA.frm | 4996 | UPDATE | conn.Execute "UPDATE stock " & _ |
| FacturaB_COPIA.frm | 10937 | SELECT | rs_item.Open "SELECT * FROM stock WHERE CodigoMovimiento = "… |
| FacturaB_COPIA.frm | 16687 | JOIN | "INNER JOIN stock ON (stock.codigoMovimiento = " & contador … |
| FacturaB_COPIA.frm | 17332 | SELECT | rs_stock.Open "SELECT * FROM stock where CodigoMovimiento = … |
| FacturaB_COPIA.frm | 17641 | SELECT | rs_stock.Open "SELECT * FROM stock where CodigoMovimiento = … |
| NotaCred_COPIA.frm | 3386 | SELECT | rs_stock.Open "SELECT * FROM stock where CodigoMovimiento = … |
| NotaCred_COPIA.frm | 3475 | SELECT | rs_stock_nc.Open "SELECT * FROM stock WHERE CodigoMovimiento… |
| NotaCred_COPIA.frm | 3480 | SELECT | rs_stock_nc.Open "SELECT * FROM stock WHERE CodigoMovimiento… |
| NotaCred_COPIA.frm | 3485 | SELECT | rs_stock_nc.Open "SELECT * FROM stock WHERE CodigoMovimiento… |
| NotaCred_COPIA.frm | 3587 | SELECT | rs_stock_id.Open "SELECT stock.id_stockp FROM stock WHERE id… |
| NotaCred_COPIA.frm | 3656 | SELECT | rs_en.Open "SELECT ensamblado FROM stock " & _ |
| NotaCred_COPIA.frm | 3681 | UPDATE | conn.Execute "UPDATE stock " & _ |
| NotaCred_COPIA.frm | 7776 | SELECT | 'rs_stock.Open "SELECT * FROM stock WHERE IDArt = " & , conn… |
| NotaCred_COPIA.frm | 7998 | SELECT | rs_item.Open "SELECT * FROM stock WHERE CodigoMovimiento = "… |
| NotaCred_COPIA.frm | 12406 | JOIN | "INNER JOIN stock ON (stock.codigoMovimiento = " & contador … |
| NotaCred_COPIA.frm | 12459 | SELECT | 'rs_stock.Open "SELECT * FROM stock WHERE stock.CodigoMovimi… |
| NotaCred_COPIA.frm | 12462 | SELECT | rs_stock.Open "SELECT * FROM stock " & _ |
| NotaCred_COPIA.frm | 12470 | SELECT | rs_stock_anul.Open "SELECT * FROM stock WHERE CodigoMovimien… |
| NotaCred_COPIA.frm | 12563 | SELECT | '                        rs_anul_lote.Open "select * from st… |
| NotaCred_COPIA.frm | 12695 | SELECT | '                rs_stock.Open "SELECT * FROM stock " & _ |
| NotaCred_COPIA.frm | 12705 | SELECT | rs_stock.Open "SELECT * FROM stock " & _ |
| NotaCred_COPIA.frm | 12719 | SELECT | "From Stock " & _ |
| NotaCred_COPIA.frm | 12720 | JOIN | "LEFT JOIN stock as tab2 ON (tab2.id_stock = stock.id_stock … |
| NotaCred_COPIA.frm | 12728 | SELECT | "From Stock as tab2 " & _ |
| NotaCred_COPIA.frm | 12729 | JOIN | "LEFT JOIN stock ON (stock.id_stock = tab2.id_stock_en_abm) … |
| NotaCred_COPIA.frm | 12739 | SELECT | rs_stock_anul.Open "SELECT * FROM stock WHERE CodigoMovimien… |
| NotaCred_COPIA.frm | 12865 | SELECT | '                        rs_anul_lote.Open "select * from st… |
| TPV.frm | 6508 | SELECT | rs_stock.Open "SELECT * FROM stock where CodigoMovimiento = … |
| TPV.frm | 6578 | SELECT | rs_stock_nc.Open "SELECT * FROM stock where CodigoMovimiento… |
| TPV.frm | 6742 | SELECT | rs_en.Open "SELECT ensamblado FROM stock " & _ |
| TPV.frm | 6763 | UPDATE | conn.Execute "UPDATE stock " & _ |
| TPV.frm | 9462 | SELECT | rs_stock.Open "SELECT * FROM stock where CodigoMovimiento = … |
| TPV.frm | 33840 | JOIN | "INNER JOIN stock ON (stock.codigoMovimiento = " & contador … |
| TPV.frm | 33934 | JOIN | "INNER JOIN stock ON (stock.codigoMovimiento = " & contador … |
| TPV.frm | 35119 | SELECT | rs_stock.Open "SELECT * FROM stock where CodigoMovimiento = … |
| TPV.frm | 35431 | SELECT | rs_stock.Open "SELECT * FROM stock where CodigoMovimiento = … |
| TPV.frm | 35857 | SELECT | 'rs_stock.Open "SELECT * FROM stock WHERE stock.CodigoMovimi… |
| TPV.frm | 35860 | SELECT | rs_stock.Open "SELECT * FROM stock " & _ |
| TPV.frm | 35868 | SELECT | rs_stock_anul.Open "SELECT * FROM stock WHERE CodigoMovimien… |
| TPV.frm | 35961 | SELECT | '                        rs_anul_lote.Open "select * from st… |
| TPV.frm | 36097 | SELECT | '                rs_stock.Open "SELECT * FROM stock " & _ |
| TPV.frm | 36107 | SELECT | rs_stock.Open "SELECT * FROM stock " & _ |
| TPV.frm | 36121 | SELECT | "From Stock " & _ |
| TPV.frm | 36122 | JOIN | "LEFT JOIN stock as tab2 ON (tab2.id_stock = stock.id_stock … |
| TPV.frm | 36130 | SELECT | "From Stock as tab2 " & _ |
| TPV.frm | 36131 | JOIN | "LEFT JOIN stock ON (stock.id_stock = tab2.id_stock_en_abm) … |
| … | … | … | *(553 referencias más)* |

---

## 4. Campos opcionales para trazabilidad MPR (Synap)

En bases donde la tabla `stock` incluye las columnas siguientes, el módulo MPR de Synap las rellena en las escrituras de movimientos de stock asociados a OPT/OPP/OPA:

| Campo             | Tipo  | Descripción |
|-------------------|-------|-------------|
| **codigo_mov_opt** | INT   | Código de movimiento del comprobante MSTOCK de la OPT (liberación). Vincula el renglón de stock a la orden de producción. |
| **id_en_abm**      | INT   | ID del conjunto de armado (BOM / lista de materiales). Vincula el renglón al armado cuando aplica (liberación OPT por pack, OPP por componente, OPA). |

- **Liberación OPT:** se guarda el `codigo_mov` del movimiento creado y el `id_en_abm` del pack (primera línea de la distribución).
- **OPP (parte de producción):** se guarda `codigo_mov_opt` (obtenido de la OPT) e `id_en_abm` del pack del componente.
- **OPA (armado):** se guarda `codigo_mov_opt` (si existe `id_lista_produccion`) e `id_en_abm` del conjunto armado.
- **Reclasificación:** se escriben como NULL (no asociado a OPT/BOM).

Si las columnas no existen en la base, los INSERT se realizan sin ellas (fallback ante error MySQL 1054). Ver `mpr/services.py`: `ejecutar_liberar_opt`, `ejecutar_opp`, `ejecutar_armado`, `ejecutar_reclasificacion`.

---

## 5. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| management/commands/investigar_factura_stock.py | 85 | SELECT | SELECT COUNT(*) FROM stock |
| management/commands/investigar_factura_stock.py | 98 | SELECT | FROM stock s |
| services/reconciliation_saldo_stock.py | 72 | SELECT | FROM stock s |
| services/reconciliation_saldo_stock.py | 88 | SELECT | FROM stock s |
| services/reconciliation_saldo_stock.py | 102 | SELECT | FROM stock s |
| services/reconciliation_saldo_pedido_proveedor.py | 187 | SELECT | FROM stock s |
| services/reconciliation_saldo_pedido_proveedor.py | 210 | SELECT | FROM stock s |
| services/reconciliation_saldo_pedido_proveedor.py | 435 | SELECT | FROM stock s |
| services/reconciliation_saldo_pedido_proveedor.py | 460 | SELECT | FROM stock s |

[← Índice de tablas](../DB_INDICE_TABLAS.md)