# Tabla `cuentaproveedor`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_cuentaproveedor | DOUBLE | No | ✓ |  |  |
| Fecha | DATE | Sí |  |  |  |
| FechaRegistro | DATE | Sí |  |  |  |
| TipoComprobante | VARCHAR | Sí |  |  |  |
| NroComprobante | VARCHAR | Sí |  |  |  |
| NroCompBusq | INT | Sí |  |  |  |
| Codigo | INT | Sí |  |  |  |
| CodBanco | INT | No |  |  |  |
| CodigoMovimiento | DECIMAL | Sí |  |  |  |
| codigo_movimiento_anul | DECIMAL | Sí |  |  |  |
| ImportePago | DECIMAL | Sí |  |  |  |
| ImporteCompra | DECIMAL | Sí |  |  |  |
| saldo | DECIMAL | Sí |  |  |  |
| ImporteCompraL | VARCHAR | Sí |  |  |  |
| ImpDesc1_1 | DECIMAL | Sí |  |  |  |
| TotalDesc | DECIMAL | No |  |  |  |
| Subtotal1 | DECIMAL | Sí |  |  |  |
| Subtotal2 | DECIMAL | No |  |  |  |
| Subtotal3 | DECIMAL | Sí |  |  |  |
| SubTotalGral | DECIMAL | No |  |  |  |
| SubtotalDesc | DECIMAL | Sí |  |  |  |
| SubTotalDesc1 | DECIMAL | No |  |  |  |
| SubTotalDesc2 | DECIMAL | No |  |  |  |
| SubTotalDesc3 | DECIMAL | Sí |  |  |  |
| IVA1 | DECIMAL | Sí |  |  |  |
| IVA2 | DECIMAL | Sí |  |  |  |
| IVA3 | DECIMAL | Sí |  |  |  |
| Alicuota1 | DECIMAL | Sí |  |  |  |
| Alicuota2 | DECIMAL | Sí |  |  |  |
| Alicuota3 | DECIMAL | Sí |  |  |  |
| IDAlicuota | INT | Sí |  |  |  |
| Exento | DECIMAL | Sí |  |  |  |
| Vencimiento | DATE | Sí |  |  |  |
| Vencido | VARCHAR | Sí |  |  |  |
| Detalle | MEDIUMTEXT | Sí |  |  |  |
| CondCompra | VARCHAR | Sí |  |  |  |
| id_condcompra | INT | Sí |  |  |  |
| Anulado | VARCHAR | Sí |  |  |  |
| Estado | VARCHAR | Sí |  |  |  |
| estado_remito | VARCHAR | Sí |  |  |  |
| OPMov | DOUBLE | Sí |  |  |  |
| OP | VARCHAR | Sí |  |  |  |
| NroFactRem | VARCHAR | Sí |  |  |  |
| NroFactura | VARCHAR | Sí |  |  |  |
| NroFacturaMov | VARCHAR | Sí |  |  |  |
| Moneda | VARCHAR | Sí |  |  |  |
| ValorPesos | DOUBLE | Sí |  |  |  |
| TipoPago | VARCHAR | Sí |  |  |  |
| OPPesos | DECIMAL | No |  |  |  |
| OPDolar | DECIMAL | No |  |  |  |
| CotiDolar | DECIMAL | No |  |  |  |
| TotalEfectivoP | DECIMAL | Sí |  |  |  |
| TotalEfectivoD | DOUBLE | Sí |  |  |  |
| TotalChequeT | DECIMAL | Sí |  |  |  |
| TotalChequeP | DECIMAL | Sí |  |  |  |
| TotalPago | DECIMAL | Sí |  |  |  |
| TotalImputacionOP | DECIMAL | Sí |  |  |  |
| NetoImputacionOP | DECIMAL | Sí |  |  |  |
| TotalPagoOP | DECIMAL | Sí |  |  |  |
| Total_MCT | DECIMAL | Sí |  |  |  |
| Total_medpag | DECIMAL | Sí |  |  |  |
| TotalOP | DECIMAL | Sí |  |  |  |
| NroCAI | VARCHAR | Sí |  |  |  |
| FechaCAI | DATE | Sí |  |  |  |
| PercepIB | DECIMAL | Sí |  |  |  |
| CodProv_PercepIB1 | INT | Sí |  |  |  |
| PercepIB_Prov | DECIMAL | Sí |  |  |  |
| CodProv_PercepIB2 | INT | Sí |  |  |  |
| PercepGan | DECIMAL | Sí |  |  |  |
| PercepIVA | DECIMAL | Sí |  |  |  |
| OtrosImp | DECIMAL | Sí |  |  |  |
| TotalDescOP | DECIMAL | No |  |  |  |
| TotalRetencion | DECIMAL | No |  |  |  |
| CodigoGasto | INT | No |  |  |  |
| TipoFactura | VARCHAR | No |  |  |  |
| TipoNC | VARCHAR | No |  |  |  |
| TipoOP | VARCHAR | Sí |  |  |  |
| FechaControl | TIMESTAMP | No |  |  |  |
| IdUsuario | INT | Sí |  |  |  |
| CodSucursal | INT | Sí |  |  |  |
| total_trans | DECIMAL | Sí |  |  |  |
| ctabanc_trans | INT | Sí |  |  |  |
| nroref_trans | DECIMAL | Sí |  |  |  |
| fecha_trans | DATE | Sí |  |  |  |
| motivo_nd | VARCHAR | Sí |  |  |  |
| id_chequerechazado_tercero | INT | Sí |  |  |  |
| id_chequerechazado_propio | INT | Sí |  |  |  |
| concepto_nd | VARCHAR | Sí |  |  |  |
| adjunto | VARCHAR | Sí |  |  |  |
| fecha_entrega_oc | DATE | Sí |  |  |  |
| tipo_devol_nc | VARCHAR | Sí |  |  |  |
| impuesto_interno | DOUBLE | Sí |  |  |  |
| id_proyecto | INT | Sí |  |  |  |
| total_ingreso | DECIMAL | Sí |  |  |  |
| total_percepcion | DECIMAL | Sí |  |  |  |
| sobretasa_iva | DECIMAL | Sí |  |  |  |
| remite_factura_art | VARCHAR | Sí |  |  |  |
| estado_fact_remito | VARCHAR | Sí |  |  |  |
| total_percep | DECIMAL | Sí |  |  |  |
| pre_autorizado | VARCHAR | Sí |  |  |  |
| id_autorizado_pre | INT | Sí |  |  |  |
| fact_vale | VARCHAR | Sí |  |  |  |
| id_plantilla | BIGINT | Sí |  |  |  |
| autorizacion_sistema | VARCHAR | Sí |  |  |  |
| fecha_recepcion | DATE | Sí |  |  |  |
| id_pv | INT | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| cuentaproveedor | otro_egreso | Info_Estadistica.frm | 2719 | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentaproveedor.`CodigoMovim… |
| cuentaproveedor | otro_egreso | Info_Estadistica.frm | 2725 | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentaproveedor.`CodigoMovim… |
| cuentaproveedor | otro_egreso | Info_Estadistica.frm | 2774 | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentaproveedor.`CodigoMovim… |
| cuentaproveedor | otro_egreso | Info_Estadistica.frm | 2791 | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentaproveedor.`CodigoMovim… |
| stock | cuentaproveedor | Info_Estadistica.frm | 3854 | '                                                                               … |
| stock | cuentaproveedor | Info_Estadistica.frm | 4097 | "From Stock LEFT JOIN cuentaproveedor ON (cuentaproveedor.CodigoMovimiento = sto… |
| stock | cuentaproveedor | Info_Banco.frm | 2944 | "From Stock LEFT JOIN cuentaproveedor ON (cuentaproveedor.CodigoMovimiento = sto… |
| cuentaproveedor | otro_egreso | Erp_Info.frm | 2851 | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentaproveedor.`CodigoMovim… |
| cuentaproveedor | otro_egreso | Erp_Info.frm | 2857 | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentaproveedor.`CodigoMovim… |
| cuentaproveedor | otro_egreso | Erp_Info.frm | 2872 | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentaproveedor.`CodigoMovim… |
| cuentaproveedor | otro_egreso | Erp_Info.frm | 2878 | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentaproveedor.`CodigoMovim… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| PNotaCred.frm | 2711 | SELECT | rs_consul_fact.Open "SELECT CodigoMovimiento,remite_factura_… |
| PNotaCred.frm | 2722 | SELECT | rs_consulta_remito2.Open "SELECT cuentaproveedor.CodigoMovim… |
| PNotaCred.frm | 2870 | SELECT | rs_cuentaproveedor.Open "SELECT * FROM cuentaproveedor WHERE… |
| PNotaCred.frm | 2901 | SELECT | rs_op_factura.Open "SELECT * FROM cuentaproveedor where Codi… |
| PNotaCred.frm | 3043 | SELECT | rs_tipo_factura.Open "SELECT id_cuentaproveedor,remite_factu… |
| PNotaCred.frm | 3477 | SELECT | rs_op_factura.Open "SELECT * FROM cuentaproveedor where Codi… |
| PNotaCred.frm | 3652 | SELECT | rs_op_factura.Open "SELECT * FROM cuentaproveedor where Codi… |
| PNotaCred.frm | 3667 | SELECT | '                rs_op_factura.Open "SELECT * FROM cuentapro… |
| PNotaCred.frm | 5718 | SELECT | rs_factura.Open "SELECT * FROM cuentaproveedor WHERE nrocomp… |
| PNotaCred.frm | 5722 | SELECT | rs_factura.Open "SELECT * FROM cuentaproveedor WHERE nrocomp… |
| PNotaCred.frm | 5743 | SELECT | rs_factura.Open "SELECT * FROM cuentaproveedor WHERE nrocomp… |
| PNotaCred.frm | 5747 | SELECT | rs_factura.Open "SELECT * FROM cuentaproveedor WHERE nrocomp… |
| PNotaCred.frm | 5967 | SELECT | rs_cuentacli.Open "SELECT * FROM cuentaproveedor WHERE Codig… |
| Info_Estadistica.frm | 2719 | SELECT | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentapr… |
| Info_Estadistica.frm | 2725 | SELECT | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentapr… |
| Info_Estadistica.frm | 2774 | SELECT | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentapr… |
| Info_Estadistica.frm | 2791 | SELECT | " FROM `cuentaproveedor` LEFT JOIN `otro_egreso` ON cuentapr… |
| Info_Estadistica.frm | 2949 | SELECT | " FROM `cuentaproveedor`  WHERE  `cuentaproveedor`.`Anulado`… |
| Info_Estadistica.frm | 2965 | SELECT | " FROM `cuentaproveedor` WHERE `cuentaproveedor`.`Anulado`='… |
| Info_Estadistica.frm | 3854 | JOIN | '                                                           … |
| Info_Estadistica.frm | 4097 | JOIN | "From Stock LEFT JOIN cuentaproveedor ON (cuentaproveedor.Co… |
| Visualiza_PNotaDeb.frm | 2645 | SELECT | rs_factura.Open "SELECT * FROM cuentaproveedor WHERE NroComp… |
| Visualiza_PNotaDeb.frm | 2660 | SELECT | rs_factura.Open "SELECT * FROM cuentaproveedor WHERE NroComp… |
| Visualiza_PNotaDeb.frm | 2899 | SELECT | rs_cuentacli.Open "SELECT * FROM cuentaproveedor WHERE Codig… |
| Visualiza_PNotaDeb.frm | 4252 | SELECT | rsCtaProv.Open "SELECT * FROM CuentaProveedor WHERE codigomo… |
| Info_Impositivo.frm | 2957 | SELECT | "From CuentaProveedor " & _ |
| Info_Impositivo.frm | 3010 | SELECT | "From cuentaproveedor " & _ |
| Cont_ProcAsientosM.frm | 2337 | SELECT | rsCtaProv.Open "SELECT * FROM CuentaProveedor WHERE codigomo… |
| Cont_ProcAsientosM.frm | 2357 | SELECT | rsCtaProv.Open "SELECT * FROM CuentaProveedor WHERE codigomo… |
| Cont_ProcAsientosM.frm | 2377 | SELECT | rsCtaProv.Open "SELECT * FROM CuentaProveedor WHERE codigomo… |
| Cont_ProcAsientosM.frm | 2518 | SELECT | rsCtaProv.Open "SELECT * FROM CuentaProveedor WHERE codigomo… |
| OrdenPago.frm | 6924 | SELECT | rs_cuentaproveedor.Open "SELECT * FROM cuentaproveedor WHERE… |
| OrdenPago.frm | 7320 | SELECT | rs_cuentaproveedor.Open "SELECT * FROM cuentaproveedor WHERE… |
| OrdenPago.frm | 10010 | JOIN | " LEFT JOIN cuentaproveedor ON (cuentaproveedor.codigomovimi… |
| OrdenPago.frm | 10036 | JOIN | " LEFT JOIN cuentaproveedor ON (cuentaproveedor.codigomovimi… |
| OrdenPago.frm | 11633 | JOIN | "INNER JOIN cuentaproveedor ON (cuentaproveedor.CodigoMovimi… |
| OrdenPago.frm | 11880 | JOIN | "INNER JOIN cuentaproveedor ON (cuentaproveedor.CodigoMovimi… |
| OrdenPago.frm | 12015 | JOIN | "INNER JOIN cuentaproveedor ON (cuentaproveedor.CodigoMovimi… |
| OrdenPago.frm | 12857 | SELECT | ''            rs_cuentaproveedor.Open "SELECT * FROM cuentap… |
| OrdenPago.frm | 15229 | SELECT | rs_fact.Open "SELECT * from cuentaproveedor where CodigoMovi… |
| OrdenPago.frm | 15563 | SELECT | rs_ND.Open "SELECT * from cuentaproveedor where CodigoMovimi… |
| OrdenPago.frm | 15673 | SELECT | rs_cuentaproveedor.Open "SELECT * FROM cuentaproveedor WHERE… |
| OrdenPago.frm | 16258 | SELECT | rs_calculo_iva.Open "SELECT SUM(iva1+iva2+iva3) as total_iva… |
| OrdenPago.frm | 16547 | JOIN | " LEFT JOIN cuentaproveedor ON (cuentaproveedor.codigomovimi… |
| OrdenPago.frm | 16573 | JOIN | " LEFT JOIN cuentaproveedor ON (cuentaproveedor.codigomovimi… |
| AsigPagoD.frm | 1025 | SELECT | rs_cuentaproveedor.Open "SELECT id_cuentaproveedor,CodigoMov… |
| AsigPagoD.frm | 1041 | SELECT | rs_cuentaproveedor.Open "SELECT id_cuentaproveedor,CodigoMov… |
| AsigPagoD.frm | 1070 | SELECT | rs_cuentaproveedor.Open "SELECT * FROM cuentaproveedor WHERE… |
| AsigPagoD.frm | 1156 | SELECT | rs_cuentaproveedor_acuenta.Open "SELECT * FROM cuentaproveed… |
| Visualiza_PNotaCred_Importe.frm | 2112 | SELECT | rs_cuentaproveedor.Open "SELECT * FROM cuentaproveedor WHERE… |
| Visualiza_PNotaCred_Importe.frm | 2294 | SELECT | rs_op_factura.Open "SELECT * FROM cuentaproveedor where Codi… |
| Visualiza_PNotaCred_Importe.frm | 2831 | SELECT | rs_factura.Open "SELECT * FROM cuentaproveedor WHERE NroComp… |
| Visualiza_PNotaCred_Importe.frm | 2846 | SELECT | rs_factura.Open "SELECT * FROM cuentaproveedor WHERE NroComp… |
| Visualiza_PNotaCred_Importe.frm | 2970 | SELECT | rs_cuentacli.Open "SELECT * FROM cuentaproveedor WHERE Codig… |
| Visualiza_PNotaCred_Importe.frm | 4275 | SELECT | rsCtaProv.Open "SELECT * FROM CuentaProveedor WHERE codigomo… |
| Visualiza_POrden_Compra.frm | 3505 | SELECT | rs_cuentaproveedor.Open "SELECT * FROM cuentaproveedor WHERE… |
| Visualiza_POrden_Compra.frm | 3719 | SELECT | rs_presupuesto.Open "SELECT * FROM cuentaproveedor WHERE Cod… |
| Visualiza_POrden_Compra.frm | 3788 | SELECT | rs_informe.Open "select * from cuentaproveedor WHERE CodigoM… |
| Visualiza_POrden_Compra.frm | 4824 | SELECT | .Source = "SELECT * FROM cuentaproveedor WHERE cuentaproveed… |
| Visualiza_POrden_Compra.frm | 4935 | SELECT | .Source = "SELECT * FROM cuentaproveedor WHERE " & _ |
| Visualiza_POrden_Compra.frm | 6036 | SELECT | .Source = "SELECT * FROM cuentaproveedor WHERE cuentaproveed… |
| Visualiza_POrden_Compra.frm | 6191 | SELECT | rs_comp_oc.Open "SELECT * FROM cuentaproveedor WHERE CodigoM… |
| Visualiza_POrden_Compra.frm | 6222 | SELECT | rs_cuentaproveedor.Open "SELECT * FROM cuentaproveedor WHERE… |
| Visualiza_POrden_Compra.frm | 6587 | SELECT | rsCtaProv.Open "SELECT * FROM CuentaProveedor WHERE codigomo… |
| Info_Banco.frm | 2944 | JOIN | "From Stock LEFT JOIN cuentaproveedor ON (cuentaproveedor.Co… |
| POrden_CompraCopia.frm | 2975 | SELECT | rs_cuentaproveedor.Open "SELECT * FROM cuentaproveedor WHERE… |
| POrden_CompraCopia.frm | 3284 | SELECT | rs_presupuesto.Open "SELECT * FROM cuentaproveedor WHERE Cod… |
| POrden_CompraCopia.frm | 3376 | SELECT | rs_informe.Open "select * from cuentaproveedor WHERE CodigoM… |
| POrden_CompraCopia.frm | 4333 | SELECT | .Source = "SELECT * FROM cuentaproveedor WHERE cuentaproveed… |
| POrden_CompraCopia.frm | 4450 | SELECT | .Source = "SELECT * FROM cuentaproveedor WHERE " & _ |
| POrden_CompraCopia.frm | 5629 | SELECT | .Source = "SELECT * FROM cuentaproveedor WHERE cuentaproveed… |
| POrden_CompraCopia.frm | 5809 | SELECT | rs_cuentaproveedor.Open "SELECT * FROM cuentaproveedor WHERE… |
| PRemito.frm | 3498 | SELECT | rs_cuentaproveedor.Open "SELECT * FROM cuentaproveedor WHERE… |
| PRemito.frm | 4054 | SELECT | '                    rs_oc_proveedor.Open "SELECT * FROM cue… |
| PRemito.frm | 4103 | SELECT | rs_pedido.Open "SELECT * FROM cuentaproveedor WHERE CodigoMo… |
| PRemito.frm | 4163 | SELECT | rs_factura.Open "SELECT * FROM cuentaproveedor WHERE CodigoM… |
| PRemito.frm | 4199 | SELECT | rs_remito.Open "SELECT cuentaProveedor.CodigoMovimiento,cuen… |
| PRemito.frm | 5018 | SELECT | .Source = "SELECT * FROM cuentaproveedor WHERE " & _ |
| PRemito.frm | 5075 | SELECT | .Source = "SELECT * FROM cuentaproveedor WHERE cuentaproveed… |
| PRemito.frm | 5115 | SELECT | .Source = "SELECT * FROM cuentaproveedor WHERE cuentaproveed… |
| … | … | … | *(444 referencias más)* |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| management/commands/investigar_factura_stock.py | 49 | SELECT | FROM cuentaproveedor |
| services/query_runner.py | 3162 | JOIN | INNER JOIN cuentaproveedor cp_oc ON cp_oc.CodigoMovimiento =… |
| services/query_runner.py | 3282 | JOIN | INNER JOIN cuentaproveedor cp ON cp.CodigoMovimiento = sp.Co… |
| services/reconciliation_saldo_pedido_proveedor.py | 173 | JOIN | INNER JOIN cuentaproveedor cp ON cp.CodigoMovimiento = sp.Co… |
| services/reconciliation_saldo_pedido_proveedor.py | 188 | JOIN | INNER JOIN cuentaproveedor cp_rem ON cp_rem.CodigoMovimiento… |
| services/reconciliation_saldo_pedido_proveedor.py | 213 | JOIN | INNER JOIN cuentaproveedor cp_fa ON cp_fa.CodigoMovimiento =… |
| services/reconciliation_saldo_pedido_proveedor.py | 233 | JOIN | INNER JOIN cuentaproveedor cp ON cp.CodigoMovimiento = sp.Co… |
| services/reconciliation_saldo_pedido_proveedor.py | 254 | JOIN | INNER JOIN cuentaproveedor cp ON cp.CodigoMovimiento = sp.Co… |
| services/reconciliation_saldo_pedido_proveedor.py | 419 | JOIN | INNER JOIN cuentaproveedor cp ON cp.CodigoMovimiento = sp.Co… |
| services/reconciliation_saldo_pedido_proveedor.py | 436 | JOIN | INNER JOIN cuentaproveedor cp_rem ON cp_rem.CodigoMovimiento… |
| services/reconciliation_saldo_pedido_proveedor.py | 463 | JOIN | INNER JOIN cuentaproveedor cp_fa ON cp_fa.CodigoMovimiento =… |
| services/reconciliation_saldo_pedido_proveedor.py | 484 | JOIN | INNER JOIN cuentaproveedor cp ON cp.CodigoMovimiento = sp.Co… |

[← Índice de tablas](../DB_INDICE_TABLAS.md)