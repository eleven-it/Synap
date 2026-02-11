# Tabla `cuentacliente`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_cuentacliente | DOUBLE | No | ✓ |  |  |
| Fecha | DATE | Sí |  |  |  |
| TipoComprobante | VARCHAR | Sí |  |  |  |
| NroComprobante | VARCHAR | Sí |  |  |  |
| NroCompBusq | INT | Sí |  |  |  |
| Codigo | INT | Sí |  |  |  |
| CodigoMovimiento | DECIMAL | No |  |  |  |
| codigo_movimiento_anul | DECIMAL | Sí |  |  |  |
| ImporteCobro | DECIMAL | Sí |  |  |  |
| ImporteVenta | DECIMAL | Sí |  |  |  |
| saldo | DECIMAL | Sí |  |  |  |
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
| IG1 | DECIMAL | Sí |  |  |  |
| IG2 | DECIMAL | Sí |  |  |  |
| AlicuotaIB1 | DECIMAL | Sí |  |  |  |
| AlicuotaIB2 | DECIMAL | Sí |  |  |  |
| NetoIG1 | DECIMAL | Sí |  |  |  |
| NetoIG2 | DECIMAL | Sí |  |  |  |
| Vencimiento | DATE | Sí |  |  |  |
| Vencido | VARCHAR | Sí |  |  |  |
| Detalle | MEDIUMTEXT | Sí |  |  |  |
| CondVenta | VARCHAR | Sí |  |  |  |
| id_condventa | INT | Sí |  |  |  |
| Anulado | VARCHAR | Sí |  |  |  |
| Estado | VARCHAR | Sí |  |  |  |
| ReciboMov | DOUBLE | Sí |  |  |  |
| Recibo | VARCHAR | Sí |  |  |  |
| ReciboBusq | VARCHAR | No |  |  |  |
| NroFactura | VARCHAR | Sí |  |  |  |
| NroFacturaMov | VARCHAR | Sí |  |  |  |
| CodViajante | INT | Sí |  |  |  |
| Liquidado | VARCHAR | Sí |  |  |  |
| TipoRecibo | VARCHAR | Sí |  |  |  |
| TipoNC | VARCHAR | No |  |  |  |
| ReciboPesos | DECIMAL | Sí |  |  |  |
| ReciboDolar | DECIMAL | Sí |  |  |  |
| CotiDolar | DECIMAL | Sí |  |  |  |
| TipoPago | VARCHAR | Sí |  |  |  |
| TotalEfectivoP | DECIMAL | Sí |  |  |  |
| TotalEfectivoD | DECIMAL | Sí |  |  |  |
| TotalCheque | DECIMAL | Sí |  |  |  |
| TotalPago | DECIMAL | Sí |  |  |  |
| TotalImputacionRec | DECIMAL | Sí |  |  |  |
| NetoImputacionRec | DECIMAL | Sí |  |  |  |
| TotalPagoRec | DECIMAL | Sí |  |  |  |
| Total_MC | DECIMAL | Sí |  |  |  |
| Total_Tarjeta | DECIMAL | Sí |  |  |  |
| TotalRecibo | DECIMAL | Sí |  |  |  |
| TotalDescRec | DECIMAL | No |  |  |  |
| TotalRetencion | DECIMAL | No |  |  |  |
| TipoFactura | VARCHAR | No |  |  |  |
| TipoFacturaPR | VARCHAR | Sí |  |  |  |
| FechaControl | TIMESTAMP | No |  |  |  |
| IdUsuario | INT | Sí |  |  |  |
| CodSucursal | INT | Sí |  |  |  |
| total_trans | DECIMAL | Sí |  |  |  |
| ctabanc_trans | INT | Sí |  |  |  |
| nroref_trans | DECIMAL | Sí |  |  |  |
| fecha_trans | DATE | Sí |  |  |  |
| tiporec | VARCHAR | Sí |  |  |  |
| motivo_nd | VARCHAR | Sí |  |  |  |
| id_chequerechazado | INT | Sí |  |  |  |
| concepto_nd | VARCHAR | Sí |  |  |  |
| id_pv | INT | Sí |  |  |  |
| tipo_devol_nc | VARCHAR | Sí |  |  |  |
| tpv_comp | VARCHAR | Sí |  |  |  |
| tpv_nombre_ocasional | VARCHAR | Sí |  |  |  |
| tpv_domicilio_ocasional | VARCHAR | Sí |  |  |  |
| tpv_nro_identif_ocasional | VARCHAR | Sí |  |  |  |
| tpv_importe_efectivo | DECIMAL | Sí |  |  |  |
| tpv_cambio_efectivo | DECIMAL | Sí |  |  |  |
| tpv_pago_efectivo | DECIMAL | Sí |  |  |  |
| tpv_importe_ctacte | DECIMAL | Sí |  |  |  |
| tpv_importe_cheque | DECIMAL | Sí |  |  |  |
| tpv_importe_tarjeta | DECIMAL | Sí |  |  |  |
| comprobante_fiscal | VARCHAR | Sí |  |  |  |
| interes | DECIMAL | Sí |  |  |  |
| id_cond_venta_tpv | INT | Sí |  |  |  |
| impuesto_interno_total | DECIMAL | Sí |  |  |  |
| fe_cae | VARCHAR | Sí |  |  |  |
| fe_vto_cae | DATE | Sí |  |  |  |
| fe_comp | VARCHAR | Sí |  |  |  |
| fe_transmitido | VARCHAR | Sí |  |  |  |
| id_proyecto | INT | Sí |  |  |  |
| redondeo | DOUBLE | Sí |  |  |  |
| tipo_redondeo | VARCHAR | Sí |  |  |  |
| total_ingreso | DECIMAL | Sí |  |  |  |
| remite_factura_art | VARCHAR | Sí |  |  |  |
| estado_fact_remito | VARCHAR | Sí |  |  |  |
| total_percep | DECIMAL | Sí |  |  |  |
| id_deposito_despacho | DOUBLE | Sí |  |  |  |
| comp_supervisor | VARCHAR | Sí |  |  |  |
| monto_percep_iva | DOUBLE | Sí |  |  |  |
| id_ingreso | DOUBLE | Sí |  |  |  |
| cierre_z | VARCHAR | Sí |  |  |  |
| codmov_cot | BIGINT | Sí |  |  |  |
| interes_porcentaje | DOUBLE | Sí |  |  |  |
| exento_interes | DOUBLE | Sí |  |  |  |
| impuesto_interno_interes | DOUBLE | Sí |  |  |  |
| fe_tipo | VARCHAR | Sí |  |  |  |
| fe_cbu | VARCHAR | Sí |  |  |  |
| tpv_mail_ocasional | VARCHAR | Sí |  |  |  |
| tpv_cel_wp_ocasional | VARCHAR | Sí |  |  |  |
| tpv_doc_cliente_ocasional | VARCHAR | Sí |  |  |  |
| fe_regimen_tipo | VARCHAR | Sí |  |  |  |
| total_costo | DOUBLE | Sí |  |  |  |
| id_vendedor_asistente | INT | Sí |  |  |  |
| observacion_interna | MEDIUMTEXT | Sí |  |  |  |
| monto_devol | DOUBLE | Sí |  |  |  |
| tpv_nc_aplicada | VARCHAR | Sí |  |  |  |

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
| Cliente.frm | 3093 | SELECT | rs_cliente.Open "SELECT * FROM cuentacliente WHERE Codigo = … |
| Stock_Control_Entrada.frm | 762 | SELECT | " FROM cuentacliente " & _ |
| Visualiza_ReciboCobro.frm | 6384 | SELECT | rs_cuentacliente.Open "SELECT * FROM cuentacliente WHERE Cod… |
| Visualiza_ReciboCobro.frm | 6685 | SELECT | rs_cuentacliente.Open "SELECT * FROM cuentacliente WHERE Cod… |
| Visualiza_ReciboCobro.frm | 10548 | SELECT | rs_consultacomp.Open "SELECT * FROM cuentacliente WHERE NroC… |
| Visualiza_ReciboCobro.frm | 10567 | SELECT | rs_consultacomp.Open "SELECT * FROM cuentacliente WHERE NroC… |
| Visualiza_ReciboCobro.frm | 10984 | SELECT | rs_fact.Open "SELECT * from cuentacliente where CodigoMovimi… |
| Visualiza_ReciboCobro.frm | 11360 | SELECT | rs_factb.Open "SELECT * from cuentacliente where CodigoMovim… |
| Visualiza_ReciboCobro.frm | 11852 | SELECT | '        rs_cuentacliente.Open "SELECT * FROM cuentacliente … |
| Visualiza_ReciboCobro.frm | 11998 | SELECT | '            rs_cuentacliente.Open "SELECT * FROM cuentaclie… |
| Visualiza_ReciboCobro.frm | 12173 | SELECT | rs_ND.Open "SELECT * from cuentacliente where codigomovimien… |
| Visualiza_ReciboCobro.frm | 12227 | SELECT | rs_cuentacliente.Open "SELECT * FROM cuentacliente WHERE Cod… |
| Visualiza_ReciboCobro.frm | 12509 | SELECT | rs_factpv.Open "SELECT * from cuentacliente where CodigoMovi… |
| Visualiza_ReciboCobro.frm | 12787 | SELECT | '            rs_cuentacli.Open "SELECT * FROM cuentacliente … |
| Visualiza_ReciboCobro.frm | 12851 | SELECT | rs_cuentacli.Open "SELECT * FROM cuentacliente WHERE CodigoM… |
| Visualiza_NotaCred.frm | 2503 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| Visualiza_NotaCred.frm | 2707 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| Visualiza_NotaCred.frm | 3024 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| Visualiza_NotaCred.frm | 4520 | SELECT | rs_factura.Open "SELECT * FROM cuentacliente WHERE NroCompro… |
| Visualiza_NotaCred.frm | 4539 | SELECT | rs_factura.Open "SELECT * FROM cuentacliente WHERE NroCompro… |
| Visualiza_NotaCred.frm | 4684 | SELECT | rs_cuentacli.Open "SELECT * FROM cuentacliente WHERE CodigoM… |
| Visualiza_NotaCred.frm | 4885 | SELECT | rs_cuentacli.Open "SELECT * FROM cuentacliente WHERE CodigoM… |
| Visualiza_NotaCred.frm | 6304 | SELECT | rs_cuentacli.Open "SELECT * FROM cuentacliente WHERE CodigoM… |
| Info_Estadistica.frm | 2713 | SELECT | " FROM `cuentacliente` WHERE `cuentacliente`.`Anulado`='No' … |
| Info_Estadistica.frm | 2736 | SELECT | '                " FROM `cuentacliente` WHERE  YEAR(cuentacl… |
| Info_Estadistica.frm | 2761 | SELECT | "FROM `cuentacliente` WHERE `cuentacliente`.`Anulado`='No'  … |
| Info_Estadistica.frm | 2943 | SELECT | " FROM `cuentacliente` WHERE `cuentacliente`.`Anulado`='No' … |
| Info_Estadistica.frm | 2959 | SELECT | " FROM `cuentacliente` WHERE `cuentacliente`.`Anulado`='No' … |
| NotaCredCon.frm | 2516 | SELECT | rs_cuentacliente.Open "SELECT * FROM cuentacliente WHERE Cod… |
| NotaCredCon.frm | 2616 | SELECT | rs_recibo_factura.Open "SELECT * FROM cuentacliente where Co… |
| NotaCredCon.frm | 2875 | SELECT | rs_recibo_factura.Open "SELECT * FROM cuentacliente where Co… |
| NotaCredCon.frm | 2889 | SELECT | rs_recibo_factura.Open "SELECT * FROM cuentacliente where Co… |
| NotaCredCon.frm | 3069 | SELECT | rs_recibo_factura.Open "SELECT * FROM cuentacliente where Co… |
| NotaCredCon.frm | 3386 | SELECT | rs_cuentacliente_fe.Open "SELECT id_cuentacliente,fe_cae,fe_… |
| NotaCredCon.frm | 3578 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| NotaCredCon.frm | 3900 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| NotaCredCon.frm | 4387 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| NotaCredCon.frm | 4650 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| NotaCredCon.frm | 4908 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| NotaCredCon.frm | 5153 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| NotaCredCon.frm | 5386 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| NotaCredCon.frm | 6224 | SELECT | rs_factura.Open "SELECT * FROM cuentacliente WHERE NroCompro… |
| NotaCredCon.frm | 6243 | SELECT | rs_factura.Open "SELECT * FROM cuentacliente WHERE NroCompro… |
| NotaCredCon.frm | 6524 | SELECT | rs_cuentacli.Open "SELECT * FROM cuentacliente WHERE CodigoM… |
| NotaCredCon.frm | 7741 | SELECT | rs_CondVta.Open "SELECT id_condventa from cuentacliente WHER… |
| NotaCredCon.frm | 7811 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| NotaCredCon.frm | 9277 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| NotaCredCon.frm | 10304 | SELECT | rs_cuentacliente_fe.Open "SELECT id_cuentacliente,fe_cae,fe_… |
| NotaCredCon.frm | 10600 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| NotaCredCon.frm | 11152 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| NotaCredCon.frm | 11613 | SELECT | rs_cuentacliente_fe.Open "SELECT id_cuentacliente,fe_cae,fe_… |
| FacturaB_COPIA.frm | 4141 | SELECT | rs_cuentacliente.Open "SELECT * FROM cuentacliente WHERE Cod… |
| FacturaB_COPIA.frm | 5401 | SELECT | rs_cuentacliente_fe.Open "SELECT id_cuentacliente,fe_cae,fe_… |
| FacturaB_COPIA.frm | 5567 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| FacturaB_COPIA.frm | 6076 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| FacturaB_COPIA.frm | 6418 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| FacturaB_COPIA.frm | 6709 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| FacturaB_COPIA.frm | 8911 | SELECT | .Source = "SELECT * FROM cuentacliente WHERE " & _ |
| FacturaB_COPIA.frm | 10052 | SELECT | rs_factura.Open "SELECT * FROM cuentacliente WHERE NroCompro… |
| FacturaB_COPIA.frm | 10058 | SELECT | rs_factura.Open "SELECT * FROM cuentacliente WHERE NroCompro… |
| FacturaB_COPIA.frm | 10064 | SELECT | rs_factura.Open "SELECT * FROM cuentacliente WHERE NroCompro… |
| FacturaB_COPIA.frm | 10082 | SELECT | rs_factura.Open "SELECT * FROM cuentacliente WHERE NroCompro… |
| FacturaB_COPIA.frm | 10916 | SELECT | rs_cuentacli.Open "SELECT * FROM cuentacliente WHERE CodigoM… |
| FacturaB_COPIA.frm | 11074 | SELECT | rs_limitescli.Open "SELECT MIN(cuentacliente.Fecha) as ultim… |
| FacturaB_COPIA.frm | 11094 | SELECT | '                         "SELECT " & Principal.idUsuario & … |
| FacturaB_COPIA.frm | 12685 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| FacturaB_COPIA.frm | 13504 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| FacturaB_COPIA.frm | 14691 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| FacturaB_COPIA.frm | 17985 | SELECT | rs_cuentacliente_fe.Open "SELECT id_cuentacliente,fe_cae,fe_… |
| FacturaB_COPIA.frm | 18263 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| NotaCredDesc.frm | 2430 | SELECT | rs_cuentacliente.Open "select * from cuentacliente where Cod… |
| NotaCredDesc.frm | 2776 | SELECT | rs_cuentacliente_fe.Open "SELECT id_cuentacliente,fe_cae,fe_… |
| NotaCredDesc.frm | 2943 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| NotaCredDesc.frm | 3228 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| NotaCredDesc.frm | 3903 | SELECT | rs_cuentacli.Open "SELECT * FROM cuentacliente WHERE CodigoM… |
| NotaCredDesc.frm | 4850 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| NotaCredDesc.frm | 5101 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| NotaCredDesc.frm | 5354 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| NotaCredDesc.frm | 5598 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| NotaCredDesc.frm | 5845 | SELECT | rs_informe.Open "select * from cuentacliente where CodigoMov… |
| … | … | … | *(838 referencias más)* |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| services/query_runner.py | 470 | SELECT | FROM cuentacliente cc |
| services/query_runner.py | 2551 | SELECT | FROM cuentacliente cc |
| services/query_runner.py | 2984 | SELECT | FROM cuentacliente |
| services/query_runner.py | 3030 | SELECT | FROM cuentacliente cc |

[← Índice de tablas](../DB_INDICE_TABLAS.md)