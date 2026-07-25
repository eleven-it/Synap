# Tabla `comp_ped`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_comp_ped | DOUBLE | No | ✓ |  |  |
| Fecha | DATE | Sí |  |  |  |
| TipoComprobante | VARCHAR | Sí |  |  |  |
| NroComprobante | VARCHAR | Sí |  |  |  |
| NroCompBusq | INT | Sí |  |  |  |
| Codigo | INT | Sí |  |  |  |
| CodigoMovimiento | DECIMAL | No |  |  |  |
| ImporteVenta | DECIMAL | Sí |  |  |  |
| ImporteVentaL | VARCHAR | Sí |  |  |  |
| ImpDesc1 | DECIMAL | Sí |  |  |  |
| ImpDesc2 | DECIMAL | No |  |  |  |
| PorDesc1 | DECIMAL | Sí |  |  |  |
| PorDesc2 | DECIMAL | No |  |  |  |
| SubTotal1 | DECIMAL | No |  |  |  |
| SubTotal2 | DECIMAL | No |  |  |  |
| SubTotalGral | DECIMAL | Sí |  |  |  |
| SubTotalDesc1 | DECIMAL | No |  |  |  |
| SubTotalDesc2 | DECIMAL | No |  |  |  |
| SubtotalDesc | DECIMAL | Sí |  |  |  |
| IVA2 | DECIMAL | Sí |  |  |  |
| IVA1 | DECIMAL | Sí |  |  |  |
| Alicuota2 | DECIMAL | Sí |  |  |  |
| Alicuota1 | DECIMAL | Sí |  |  |  |
| Exento | DECIMAL | Sí |  |  |  |
| Vencimiento | DATE | Sí |  |  |  |
| Vencido | VARCHAR | Sí |  |  |  |
| Detalle | MEDIUMTEXT | Sí |  |  |  |
| CondVenta | VARCHAR | Sí |  |  |  |
| id_condventa | INT | Sí |  |  |  |
| Anulado | VARCHAR | Sí |  |  |  |
| Estado | VARCHAR | Sí |  |  |  |
| CodViajante | INT | Sí |  |  |  |
| Tipo | VARCHAR | Sí |  |  |  |
| NroPresup | VARCHAR | Sí |  |  |  |
| TipoPedido | VARCHAR | Sí |  |  |  |
| CodSucursal | INT | Sí |  |  |  |
| IdUsuario | INT | Sí |  |  |  |
| id_pv | INT | Sí |  |  |  |
| tipo_pedido_interno | VARCHAR | Sí |  |  |  |
| FechaEntrega | DATE | Sí |  |  |  |
| FormaEntrega | VARCHAR | Sí |  |  |  |
| id_transporte | INT | Sí |  |  |  |
| id_repartidor | INT | Sí |  |  |  |
| autorizacion_web | VARCHAR | Sí |  |  |  |
| autorizacion_sistema | VARCHAR | Sí |  |  |  |
| impuesto_interno | DECIMAL | Sí |  |  |  |
| impuesto_interno_total | DECIMAL | Sí |  |  |  |
| idUsuarioAut | INT | Sí |  |  |  |
| fecha_control | VARCHAR | No |  |  |  |
| id_proyecto | INT | Sí |  |  |  |
| erp_estado_pre | VARCHAR | Sí |  |  |  |
| id_deposito_despacho | DOUBLE | Sí |  |  |  |
| total_percep | DECIMAL | Sí |  |  |  |
| comp_supervisor | VARCHAR | Sí |  |  |  |
| id_plantilla | DOUBLE | Sí |  |  |  |
| geo_latitud | VARCHAR | Sí |  |  |  |
| geo_longitud | VARCHAR | Sí |  |  |  |
| estado_pago_ecom | VARCHAR | Sí |  |  |  |
| ped_eco | BIGINT | Sí |  |  |  |
| CotiDolar | DECIMAL | Sí |  |  |  |
| codmov_cot | BIGINT | Sí |  |  |  |
| interes | DOUBLE | Sí |  |  |  |
| interes_porcentaje | DOUBLE | Sí |  |  |  |
| exento_interes | DOUBLE | Sí |  |  |  |
| impuesto_interno_interes | DOUBLE | Sí |  |  |  |
| info_ped_eco | TEXT | Sí |  |  |  |
| operador_logistico | VARCHAR | Sí |  |  |  |
| tpv_nombre_ocasional | VARCHAR | Sí |  |  |  |
| tpv_domicilio_ocasional | VARCHAR | Sí |  |  |  |
| tpv_nro_identif_ocasional | VARCHAR | Sí |  |  |  |
| tpv_mail_ocasional | VARCHAR | Sí |  |  |  |
| tpv_cel_wp_ocasional | VARCHAR | Sí |  |  |  |
| tpv_doc_cliente_ocasional | VARCHAR | Sí |  |  |  |
| id_usuario_preparacion | INT | Sí |  |  |  |
| fecha_hora_preparacion | VARCHAR | Sí |  |  |  |
| fecha_hora_fin_preparacion | VARCHAR | Sí |  |  |  |
| fecha_hora_entrega | VARCHAR | Sí |  |  |  |
| motivo_no_entrega | VARCHAR | Sí |  |  |  |
| detalle_no_entrega | MEDIUMTEXT | Sí |  |  |  |
| id_usuario_no_entrega | INT | Sí |  |  |  |
| entregado | VARCHAR | Sí |  |  |  |
| nrocai_rem | VARCHAR | Sí |  |  |  |
| fechacai_rem | DATE | Sí |  |  |  |
| observacion_interna | MEDIUMTEXT | Sí |  |  |  |
| cod_mov_ped_orginal | BIGINT | Sí |  |  |  |
| Nro_Comp_PED_orginal | VARCHAR | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| comp_ped | crm_pre_llamada | Funciones.bas | 8279 | sql_ped = "SELECT * FROM comp_ped INNER JOIN crm_pre_llamada  ON (crm_pre_llamad… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| Cliente.frm | 3104 | SELECT | rs_cliente.Open "SELECT * FROM comp_ped " & _ |
| Erp_Carga_Parte_Diario.frm | 3397 | JOIN | '                                        "LEFT JOIN comp_ped… |
| Visualiza_CargaMovStock.frm | 3424 | SELECT | rs_pedi.Open "SELECT * FROM comp_ped WHERE CodigoMovimiento … |
| Visualiza_CargaMovStock.frm | 3923 | SELECT | .Source = "SELECT comp_ped.Anulado,comp_ped.TipoComprobante,… |
| FacturaB_COPIA.frm | 5082 | SELECT | rs_pedido.Open "SELECT * FROM comp_ped WHERE CodigoMovimient… |
| FacturaB_COPIA.frm | 5165 | SELECT | rs_remito.Open "SELECT * FROM comp_ped WHERE CodigoMovimient… |
| FacturaB_COPIA.frm | 8989 | SELECT | .Source = "SELECT * FROM comp_ped WHERE comp_ped.Anulado = '… |
| FacturaB_COPIA.frm | 9037 | SELECT | .Source = "SELECT * FROM comp_ped WHERE comp_ped.Anulado = '… |
| Pedido_prep_consulta.frm | 1452 | JOIN | ''                                    "LEFT JOIN comp_ped ON… |
| Pedido_prep_consulta.frm | 1634 | SELECT | '                                        "FROM comp_ped " & … |
| Pedido_prep_consulta.frm | 1640 | JOIN | "LEFT JOIN comp_ped ON (comp_ped.CodigoMovimiento = ped_prep… |
| Pedido_prep_consulta.frm | 2027 | UPDATE | conn.Execute "UPDATE comp_Ped " & _ |
| Pedido_prep_consulta.frm | 2035 | UPDATE | conn.Execute "UPDATE comp_Ped " & _ |
| NotaCred_COPIA.frm | 4056 | SELECT | rs_pedido.Open "SELECT * FROM comp_ped where CodigoMovimient… |
| NotaCred_COPIA.frm | 4057 | SELECT | '                rs_pedido.Open "SELECT * FROM comp_ped wher… |
| NotaCred_COPIA.frm | 4086 | SELECT | rs_remito.Open "select * from comp_ped where CodigoMovimient… |
| NotaCred_COPIA.frm | 4087 | SELECT | '                rs_remito.Open "select * from comp_ped wher… |
| TPV.frm | 10174 | SELECT | rs_pedido.Open "SELECT * FROM comp_ped WHERE CodigoMovimient… |
| CorreoEnvio2.frm | 2246 | SELECT | rs_consulta.Open "SELECT id_comp_ped,codigomovimiento,import… |
| Logi_Gestion2.frm | 3604 | SELECT | "SELECT codigo FROM comp_ped WHERE CodigoMovimiento = " & Da… |
| Logi_Gestion2.frm | 3608 | SELECT | "SELECT codigo FROM comp_ped WHERE CodigoMovimiento = " & Li… |
| Logi_Gestion2.frm | 6229 | SELECT | "From comp_ped " & _ |
| Logi_Gestion2.frm | 6462 | SELECT | "From comp_ped " & _ |
| Logi_Gestion2.frm | 6531 | SELECT | "From comp_ped " & _ |
| Logi_Gestion2.frm | 6560 | SELECT | "From comp_ped " & _ |
| Logi_Gestion2.frm | 7172 | SELECT | rs.Open "SELECT * FROM comp_ped WHERE CodigoMovimiento = " &… |
| Logi_Gestion2.frm | 7921 | SELECT | '    rs.Open "SELECT * FROM comp_ped WHERE CodigoMovimiento … |
| Logi_Gestion2.frm | 7924 | SELECT | rs.Open "SELECT * FROM comp_ped WHERE CodigoMovimiento = " &… |
| Logi_Gestion2.frm | 8400 | SELECT | "SELECT codigo FROM comp_ped WHERE CodigoMovimiento = " & Li… |
| Logi_Gestion2.frm | 8728 | SELECT | "SELECT codigo FROM comp_ped WHERE CodigoMovimiento = " & Da… |
| Logi_Gestion2.frm | 8732 | SELECT | "SELECT codigo FROM comp_ped WHERE CodigoMovimiento = " & Li… |
| Logi_Gestion2.frm | 9323 | SELECT | rs_fecha.Open "SELECT comp_ped.vencimiento FROM comp_ped WHE… |
| Logi_Gestion2.frm | 9345 | SELECT | rs.Open "SELECT * FROM comp_ped WHERE CodigoMovimiento = " &… |
| Logi_Gestion2.frm | 10141 | SELECT | rs_consulta.Open "SELECT * FROM cond_venta WHERE cond_venta.… |
| Logi_Gestion2.frm | 10597 | SELECT | rs_pordesc.Open "SELECT PorDesc1 FROM comp_ped WHERE CodigoM… |
| Logi_Gestion2.frm | 10624 | SELECT | rs_pordesc.Open "SELECT PorDesc1 FROM comp_ped WHERE CodigoM… |
| Facturacion_Ciclica.frm | 2322 | SELECT | '                          rs_pordesc.Open "SELECT PorDesc1 … |
| Facturacion_Ciclica.frm | 2356 | SELECT | '                          rs_pordesc.Open "SELECT PorDesc1 … |
| Facturacion_Ciclica.frm | 3817 | SELECT | '        rs_consulta.Open "SELECT * FROM cond_venta WHERE co… |
| Visualiza_Pedido.frm | 3925 | SELECT | " FROM comp_ped " & _ |
| Visualiza_Pedido.frm | 3943 | SELECT | " FROM comp_ped " & _ |
| Visualiza_Pedido.frm | 3961 | SELECT | " FROM comp_ped " & _ |
| Visualiza_Pedido.frm | 6852 | SELECT | .Source = "SELECT * FROM comp_ped WHERE " & _ |
| Visualiza_Pedido.frm | 6909 | SELECT | .Source = "SELECT * FROM comp_ped WHERE comp_ped.Anulado = '… |
| Visualiza_Pedido.frm | 6994 | JOIN | "LEFT JOIN comp_ped ON comp_ped.CodigoMovimiento = stockp.Co… |
| Visualiza_Pedido.frm | 8697 | SELECT | rs_factura.Open "SELECT * FROM comp_ped WHERE NroComprobante… |
| Visualiza_Pedido.frm | 8715 | SELECT | rs_factura.Open "SELECT * FROM comp_ped WHERE NroComprobante… |
| Visualiza_Pedido.frm | 9618 | SELECT | rs_consulta.Open "SELECT id_comp_ped,estado,codigomovimiento… |
| Visualiza_Pedido.frm | 9633 | SELECT | rs_consulta.Open "SELECT id_comp_ped,estado,codigomovimiento… |
| Visualiza_Pedido.frm | 9695 | SELECT | rs_ComPed.Open "SELECT * from comp_ped where CodigoMovimient… |
| Visualiza_Pedido.frm | 9852 | SELECT | rs_comp_ped.Open "SELECT * FROM comp_ped WHERE CodigoMovimie… |
| Visualiza_Pedido.frm | 10604 | SELECT | rs_comp_ped.Open "SELECT * FROM comp_ped WHERE CodigoMovimie… |
| Visualiza_Pedido.frm | 10635 | SELECT | rs_informe.Open "select * from comp_ped where CodigoMovimien… |
| Visualiza_Pedido.frm | 11063 | SELECT | '        " FROM comp_ped " & _ |
| Visualiza_Pedido.frm | 11075 | SELECT | '        " FROM comp_ped " & _ |
| Visualiza_Pedido.frm | 11090 | SELECT | " FROM comp_ped " & _ |
| Visualiza_Pedido.frm | 11104 | SELECT | '            " FROM comp_ped " & _ |
| Visualiza_Pedido.frm | 11122 | SELECT | '            " FROM comp_ped " & _ |
| Visualiza_Pedido.frm | 11410 | SELECT | rs_consulta_pedido.Open "SELECT codigomovimiento,Nro_Comp_PE… |
| Visualiza_Pedido.frm | 12761 | SELECT | '        " FROM comp_ped " & _ |
| Visualiza_Pedido.frm | 12788 | SELECT | " FROM comp_ped " & _ |
| Visualiza_Pedido.frm | 13943 | SELECT | '            " FROM comp_ped " & _ |
| Visualiza_Pedido.frm | 14145 | SELECT | '            rs_comp_ped.Open "SELECT * FROM comp_ped WHERE … |
| Visualiza_Pedido.frm | 14564 | SELECT | '                            rs_presupuesto.Open "SELECT * F… |
| Visualiza_Pedido.frm | 14667 | SELECT | ''                                rs_presupuesto.Open "SELEC… |
| Logi_Gestion.frm | 4101 | SELECT | rs_pordesc.Open "SELECT PorDesc1 FROM comp_ped WHERE CodigoM… |
| Logi_Gestion.frm | 4128 | SELECT | rs_pordesc.Open "SELECT PorDesc1 FROM comp_ped WHERE CodigoM… |
| Logi_Gestion.frm | 4625 | SELECT | "SELECT codigo FROM comp_ped WHERE CodigoMovimiento = " & Da… |
| Logi_Gestion.frm | 4629 | SELECT | "SELECT codigo FROM comp_ped WHERE CodigoMovimiento = " & Li… |
| Logi_Gestion.frm | 7575 | SELECT | "From comp_ped " & _ |
| Logi_Gestion.frm | 7855 | SELECT | "From comp_ped " & _ |
| Logi_Gestion.frm | 7877 | SELECT | '                    "From comp_ped " & _ |
| Logi_Gestion.frm | 8010 | SELECT | "From comp_ped " & _ |
| Logi_Gestion.frm | 8060 | SELECT | "From comp_ped " & _ |
| Logi_Gestion.frm | 8688 | SELECT | rs.Open "SELECT * FROM comp_ped WHERE CodigoMovimiento = " &… |
| Logi_Gestion.frm | 8691 | SELECT | '    rs.Open "SELECT * FROM comp_ped WHERE CodigoMovimiento … |
| Logi_Gestion.frm | 9440 | SELECT | rs.Open "SELECT * FROM comp_ped WHERE CodigoMovimiento = " &… |
| Logi_Gestion.frm | 9943 | SELECT | "SELECT codigo FROM comp_ped WHERE CodigoMovimiento = " & Da… |
| Logi_Gestion.frm | 9947 | SELECT | "SELECT codigo FROM comp_ped WHERE CodigoMovimiento = " & Li… |
| Logi_Gestion.frm | 10312 | SELECT | "SELECT codigo FROM comp_ped WHERE CodigoMovimiento = " & Da… |
| … | … | … | *(353 referencias más)* |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| management/commands/verify_reservado_por_deposito.py | 97 | JOIN | INNER JOIN comp_ped cp ON cp.CodigoMovimiento = sp.CodigoMov… |
| management/commands/verify_reservado_por_deposito.py | 112 | JOIN | INNER JOIN comp_ped cp ON cp.CodigoMovimiento = sp.CodigoMov… |
| management/commands/verify_reservado_por_deposito.py | 129 | JOIN | INNER JOIN comp_ped cp ON cp.CodigoMovimiento = sp.CodigoMov… |
| services/query_runner.py | 2239 | SELECT | FROM comp_ped cp |
| services/query_runner.py | 2393 | SELECT | FROM comp_ped cp |
| services/query_runner.py | 2592 | SELECT | FROM comp_ped cp |
| services/query_runner.py | 2634 | SELECT | FROM comp_ped cp |
| services/query_runner.py | 2864 | JOIN | Tabla viajantes, join comp_ped.CodViajante = viajantes.CodVi… |
| services/query_runner.py | 3077 | SELECT | FROM comp_ped cp |
| services/query_runner.py | 3095 | SELECT | FROM comp_ped cp |
| services/query_runner.py | 3150 | JOIN | INNER JOIN comp_ped cp ON cp.CodigoMovimiento = sp.CodigoMov… |
| services/query_runner.py | 3175 | JOIN | INNER JOIN comp_ped cp_res ON cp_res.CodigoMovimiento = sp_r… |
| services/query_runner.py | 3333 | JOIN | INNER JOIN comp_ped cp ON cp.CodigoMovimiento = sp.CodigoMov… |
| services/query_runner.py | 3386 | JOIN | INNER JOIN comp_ped cp_res ON cp_res.CodigoMovimiento = sp_r… |
| services/query_runner.py | 3554 | SELECT | FROM comp_ped cp |

[← Índice de tablas](../DB_INDICE_TABLAS.md)