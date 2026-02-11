# Tabla `sucursales`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_sucursal | INT | No | ✓ |  |  |
| nombre_sucursal | VARCHAR | No |  |  |  |
| desc_sucursal | VARCHAR | No |  |  |  |
| id_provincia | INT | No |  |  |  |
| domicilio_sucursal | VARCHAR | No |  |  |  |
| telefono_sucursal | VARCHAR | No |  |  |  |
| email_sucursal | VARCHAR | No |  |  |  |
| nro_estab_sucursal | VARCHAR | No |  |  |  |
| id_empresa | INT | No |  |  |  |
| limite_consulta | INT | Sí |  |  |  |
| ruta_reporte_servidor | VARCHAR | Sí |  |  |  |
| ruta_reporte_comprobante | VARCHAR | Sí |  |  |  |
| cant_renglon_venta | INT | Sí |  |  |  |
| salida_sin_stock | VARCHAR | Sí |  |  |  |
| dias_venc_pedido | INT | Sí |  |  |  |
| dias_venc_presup | INT | Sí |  |  |  |
| tipo_calculo_precios_impuesto_venta | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| lim_redondeo_tpv | DOUBLE | Sí |  |  |  |
| tipo_impresora | VARCHAR | Sí |  |  |  |
| nombre_impresora | VARCHAR | Sí |  |  |  |
| puerto_impresora | VARCHAR | Sí |  |  |  |
| agente_retib | VARCHAR | Sí |  |  |  |
| agente_retg | VARCHAR | Sí |  |  |  |
| agente_reti | VARCHAR | Sí |  |  |  |
| agente_percep | VARCHAR | Sí |  |  |  |
| vendedor_defecto | DOUBLE | Sí |  |  |  |
| doble_imp_etiqueta | VARCHAR | Sí |  |  |  |
| cont | VARCHAR | Sí |  |  |  |
| dnf_vta | VARCHAR | Sí |  |  |  |
| dnf_tipo | VARCHAR | Sí |  |  |  |
| dnf_texto | VARCHAR | Sí |  |  |  |
| dnf_texto2 | VARCHAR | Sí |  |  |  |
| dnf_texto3 | VARCHAR | Sí |  |  |  |
| tipo_dnfh_hasar | VARCHAR | Sí |  |  |  |
| tipo_tpv | VARCHAR | Sí |  |  |  |
| geo_latitud | VARCHAR | Sí |  |  |  |
| geo_longitud | VARCHAR | Sí |  |  |  |
| geo_api_key | VARCHAR | Sí |  |  |  |
| cot_kg_limite | DOUBLE | Sí |  |  |  |
| cot_monto_limite | DECIMAL | Sí |  |  |  |
| cot_obligatorio_actividad | VARCHAR | Sí |  |  |  |
| cot_cantidad_operaciones | DOUBLE | Sí |  |  |  |
| cot_clave_acceso | VARCHAR | Sí |  |  |  |
| cod_postal | VARCHAR | Sí |  |  |  |
| id_localidad | INT | Sí |  |  |  |
| geo_api_key_javascript | VARCHAR | Sí |  |  |  |
| agente_percep_resol_afip_5329_iva | VARCHAR | Sí |  |  |  |
| habilita_sucursal | VARBINARY | Sí |  |  |  |
| id_articulo_fact_envio | BIGINT | Sí |  |  |  |
| activa_calculo_envios | VARCHAR | Sí |  |  |  |
| medios_pago_factura | MEDIUMTEXT | Sí |  |  |  |
| id_pais | INT | Sí |  |  |  |

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
| AsigUsrPv.frm | 758 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| CargaUsuario.frm | 2083 | SELECT | DataSucursal.RecordSource = "select * from sucursales where … |
| Info_Estadistica.frm | 5898 | SELECT | DataSucursal.RecordSource = "SELECT * FROM sucursales ORDER … |
| Info_Estadistica.frm | 5908 | SELECT | DataSucursal.RecordSource = "SELECT * FROM sucursales WHERE … |
| NotaCredCon.frm | 5839 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Visualiza_PNotaDeb.frm | 2027 | SELECT | DataSucursal.RecordSource = "SELECT id_sucursal,nombre_sucur… |
| FacturaB_COPIA.frm | 8571 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| NotaCredDesc.frm | 1388 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| NotaCred_COPIA.frm | 6893 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| CargaSucursal.frm | 1067 | SELECT | rs_sucursal.Open "SELECT * FROM sucursales where id_sucursal… |
| CargaSucursal.frm | 1190 | SELECT | ABMSucursal.DataSucursal.RecordSource = "SELECT sucursales.*… |
| CargaSucursal.frm | 1203 | SELECT | rs_sucursal.Open "SELECT * FROM sucursales where id_sucursal… |
| CargaSucursal.frm | 1264 | SELECT | ABMSucursal.DataSucursal.RecordSource = "SELECT sucursales.*… |
| CargaSucursal.frm | 1568 | SELECT | "FROM sucursales " & _ |
| TPV.frm | 12771 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Info_Impositivo.frm | 2298 | SELECT | DataSucursal.RecordSource = "SELECT * FROM sucursales ORDER … |
| Info_Impositivo.frm | 2308 | SELECT | DataSucursal.RecordSource = "SELECT * FROM sucursales WHERE … |
| Info_Impositivo.frm | 2326 | JOIN | '                            "LEFT JOIN sucursales ON (sucur… |
| Info_Impositivo.frm | 2350 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Info_Impositivo.frm | 2370 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Info_Impositivo.frm | 2658 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Proceso_Fiscal.frm | 1680 | JOIN | '    " LEFT JOIN sucursales ON (sucursales.id_sucursal = pun… |
| Proceso_Fiscal.frm | 1689 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Logi_Gestion2.frm | 5467 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Logi_Gestion2.frm | 8528 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Logi_Gestion2.frm | 8879 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Logi_Gestion2.frm | 9238 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| CargaMovCaja.frm | 1398 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Facturacion_Ciclica.frm | 3134 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Facturacion_Ciclica.frm | 3528 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Visualiza_Pedido.frm | 6501 | SELECT | rs_vtoped.Open "SELECT dias_venc_pedido from sucursales wher… |
| Logi_Gestion.frm | 6724 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Logi_Gestion.frm | 10075 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Logi_Gestion.frm | 10459 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Logi_Gestion.frm | 10893 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Configuracion2.frm | 4603 | SELECT | rs_sucursal_datos.Open "SELECT * FROM sucursales WHERE id_su… |
| Configuracion2.frm | 5234 | SELECT | 'DataSucursal.RecordSource = "SELECT * FROM sucursales WHERE… |
| Configuracion2.frm | 5235 | SELECT | DataSucursal.RecordSource = "SELECT * FROM sucursales order … |
| Configuracion2.frm | 5936 | SELECT | rs_sucursal.Open "SELECT * FROM sucursales WHERE id_sucursal… |
| Configuracion.frm | 4696 | SELECT | rs_sucursal_datos.Open "SELECT * FROM sucursales WHERE id_su… |
| Configuracion.frm | 5333 | SELECT | 'DataSucursal.RecordSource = "SELECT * FROM sucursales WHERE… |
| Configuracion.frm | 5334 | SELECT | DataSucursal.RecordSource = "SELECT * FROM sucursales order … |
| Configuracion.frm | 6037 | SELECT | rs_sucursal.Open "SELECT * FROM sucursales WHERE id_sucursal… |
| OrdenPago.frm | 10394 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| OrdenPago.frm | 10419 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Visualiza_PNotaCred_Importe.frm | 1674 | SELECT | DataSucursal.RecordSource = "SELECT id_sucursal,nombre_sucur… |
| Visualiza_POrden_Compra.frm | 5151 | SELECT | DataSucursal.RecordSource = "SELECT id_sucursal,nombre_sucur… |
| Info_Banco.frm | 3090 | SELECT | DataSucursal.RecordSource = "SELECT * FROM sucursales ORDER … |
| Info_Banco.frm | 3100 | SELECT | DataSucursal.RecordSource = "SELECT * FROM sucursales WHERE … |
| Info_Venta_respaldo_bruno.frm | 10024 | SELECT | DataSucursal.RecordSource = "SELECT * FROM sucursales ORDER … |
| Info_Venta_respaldo_bruno.frm | 10033 | SELECT | DataSucursal.RecordSource = "SELECT * FROM sucursales WHERE … |
| Info_Venta_respaldo_bruno.frm | 10054 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Info_Venta_respaldo_bruno.frm | 10074 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Info_Venta_respaldo_bruno.frm | 12170 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Visualiza_PNotaCredDev.frm | 3744 | SELECT | DataSucursal.RecordSource = "SELECT id_sucursal,nombre_sucur… |
| Info_Venta.frm | 10112 | SELECT | DataSucursal.RecordSource = "SELECT * FROM sucursales ORDER … |
| Info_Venta.frm | 10121 | SELECT | DataSucursal.RecordSource = "SELECT * FROM sucursales WHERE … |
| Info_Venta.frm | 10142 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Info_Venta.frm | 10162 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Info_Venta.frm | 12665 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| IngresoUsuario.frm | 2289 | SELECT | .Source = "SELECT  sucursales.*,datosempresa.idiva as id_iva… |
| IngresoUsuario.frm | 2760 | SELECT | .Source = "SELECT sucursales.*,provincia.CodProvincia as id_… |
| Visualiza_PNotaCredDesc.frm | 1705 | SELECT | DataSucursal.RecordSource = "SELECT id_sucursal,nombre_sucur… |
| FacturaB.frm | 13731 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| CM_Principal.frm | 1206 | SELECT | DataSucursal.RecordSource = "SELECT * FROM sucursales ORDER … |
| CM_Principal.frm | 1216 | SELECT | DataSucursal.RecordSource = "SELECT * FROM sucursales WHERE … |
| CM_Principal2.frm | 736 | SELECT | DataSucursal.RecordSource = "SELECT * FROM sucursales ORDER … |
| CM_Principal2.frm | 746 | SELECT | DataSucursal.RecordSource = "SELECT * FROM sucursales WHERE … |
| NotaCred_SinCompO.frm | 8521 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| FacturaA.frm | 9254 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Proceso_Fiscal_Conf.frm | 1296 | JOIN | " LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ve… |
| NotaCred_Importe.frm | 5390 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Exportacion.frm | 5207 | JOIN | " LEFT JOIN sucursales ON (sucursales.id_sucursal = cuentapr… |
| Exportacion.frm | 6021 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = cuentapro… |
| Exportacion.frm | 10655 | JOIN | " LEFT JOIN sucursales ON (sucursales.id_sucursal = cuentapr… |
| Exportacion.frm | 11137 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = cuentapro… |
| Seleccion_PV.frm | 247 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| NotaCredCopia.frm | 7504 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| Remito.frm | 8312 | JOIN | '                            "LEFT JOIN sucursales ON (sucur… |
| Remito.frm | 8549 | JOIN | "LEFT JOIN sucursales ON (sucursales.id_sucursal = punto_ven… |
| … | … | … | *(120 referencias más)* |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| api_views.py | 613 | SELECT | FROM sucursales |
| services/query_runner.py | 471 | JOIN | LEFT JOIN sucursales s ON s.id_sucursal = cc.CodSucursal |
| services/query_runner.py | 1467 | JOIN | LEFT JOIN sucursales s ON s.id_sucursal = c.cod_sucursal |
| services/query_runner.py | 2240 | JOIN | LEFT JOIN sucursales s ON s.id_sucursal = cp.CodSucursal |
| services/query_runner.py | 3096 | JOIN | LEFT JOIN sucursales s ON s.id_sucursal = cp.CodSucursal |

[← Índice de tablas](../DB_INDICE_TABLAS.md)