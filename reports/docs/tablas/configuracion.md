# Tabla `configuracion`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_configuracion | INT | No | ✓ |  |  |
| Limite | INT | Sí |  |  |  |
| FechaCAI | DATE | Sí |  |  |  |
| Act_Prec_Costo | VARCHAR | Sí |  |  |  |
| ValidezPresup | DATE | Sí |  |  |  |
| tiempo_sesion | DECIMAL | Sí |  |  |  |
| Genera_REC | VARCHAR | Sí |  |  |  |
| Decimales | INT | Sí |  |  |  |
| cant_pv | INT | Sí |  |  |  |
| logo | LONGBLOB | Sí |  |  |  |
| genera_cret | VARCHAR | Sí |  |  |  |
| activ_laboratorio | VARCHAR | Sí |  |  |  |
| valor_util1 | DECIMAL | Sí |  |  |  |
| valor_util2 | DECIMAL | Sí |  |  |  |
| valor_util3 | DECIMAL | Sí |  |  |  |
| valor_util4 | DECIMAL | Sí |  |  |  |
| valor_util5 | DECIMAL | Sí |  |  |  |
| desc_util1 | VARCHAR | Sí |  |  |  |
| desc_util2 | VARCHAR | Sí |  |  |  |
| desc_util3 | VARCHAR | Sí |  |  |  |
| desc_util4 | VARCHAR | Sí |  |  |  |
| desc_util5 | VARCHAR | Sí |  |  |  |
| fiscal_monto_tq_fac | DECIMAL | Sí |  |  |  |
| fiscal_monto_CF_FB | DECIMAL | Sí |  |  |  |
| fiscal_monto_CF_FC | DECIMAL | Sí |  |  |  |
| fe_url_login | VARCHAR | Sí |  |  |  |
| fe_url_acceso_servidor | VARCHAR | Sí |  |  |  |
| activ_contabilidad | VARCHAR | Sí |  |  |  |
| activ_proyecto | VARCHAR | Sí |  |  |  |
| nro_proyecto | DOUBLE | Sí |  |  |  |
| utiliza_embalaje | VARCHAR | Sí |  |  |  |
| reglas_precios | VARCHAR | Sí |  |  |  |
| activ_logistica | VARCHAR | Sí |  |  |  |
| cont_tipo_fecha | VARCHAR | Sí |  |  |  |
| visualiza_stock_web | VARCHAR | Sí |  |  |  |
| descuento_renglon_web | VARCHAR | Sí |  |  |  |
| id_usuario_web | INT | Sí |  |  |  |
| repite_cod_manual | VARCHAR | Sí |  |  |  |
| auto_genera_codbarra | VARCHAR | Sí |  |  |  |
| codigo_plu | VARCHAR | Sí |  |  |  |
| longitud_cod_art_balanza | VARCHAR | Sí |  |  |  |
| usa_multiplica_bulto_promedio | VARCHAR | Sí |  |  |  |
| lista_precio_web | INT | Sí |  |  |  |
| padron_afip | VARCHAR | Sí |  |  |  |
| activ_ensamblaje_venta | VARCHAR | Sí |  |  |  |
| articulo_costo_dolar | VARCHAR | Sí |  |  |  |
| tablero_refresco | INT | Sí |  |  |  |
| tablero_zoom | INT | Sí |  |  |  |
| activ_sp | VARCHAR | Sí |  |  |  |
| nombre_sp | VARCHAR | Sí |  |  |  |
| imprime_comp_sp | VARCHAR | Sí |  |  |  |
| lista_precio_franquicia | VARCHAR | Sí |  |  |  |
| promedio_porc_costo_fijo | DOUBLE | Sí |  |  |  |
| cotizacion_moneda_tipo | VARCHAR | Sí |  |  |  |
| nro_automatica_cod_cliente_manual | VARCHAR | Sí |  |  |  |
| codigo_barra_defecto | VARCHAR | Sí |  |  |  |
| repite_descripcion_articulo | VARCHAR | Sí |  |  |  |
| texto_aviso_envio_mail | MEDIUMTEXT | Sí |  |  |  |
| texto_aviso_pago_mail | MEDIUMTEXT | Sí |  |  |  |
| tipo_balanza | VARCHAR | Sí |  |  |  |
| activ_ml | VARCHAR | Sí |  |  |  |
| guarda_foto_base | VARCHAR | Sí |  |  |  |
| transf_FCE | VARCHAR | Sí |  |  |  |
| fe_caea_limite_facturacion | DOUBLE | Sí |  |  |  |
| resol_afip_5003 | VARCHAR | Sí |  |  |  |
| texto_resol_afip_5003 | VARCHAR | Sí |  |  |  |
| valida_pv_comp_compra | VARCHAR | Sí |  |  |  |
| activ_pd | VARCHAR | Sí |  |  |  |
| nombre_pd | VARCHAR | Sí |  |  |  |
| imprime_comp_pd | VARCHAR | Sí |  |  |  |
| detalle_cuerpo_mail_pd | VARCHAR | Sí |  |  |  |
| detalle_pie_mail_pd | VARCHAR | Sí |  |  |  |
| host_servidor_principal | VARCHAR | Sí |  |  |  |
| puerto_servidor_principal | INT | Sí |  |  |  |
| host_servidor_principal_nube | VARCHAR | Sí |  |  |  |
| puerto_servidor_principal_nube | INT | Sí |  |  |  |
| base_servidor_principal | VARCHAR | Sí |  |  |  |
| base_servidor_principal_nube | VARCHAR | Sí |  |  |  |
| muestra_logo_empresa | VARCHAR | Sí |  |  |  |
| logo_principal_empresa | LONGBLOB | Sí |  |  |  |
| utiliza_bulto_cerrado | VARCHAR | Sí |  |  |  |
| acumula_items_renglon | VARCHAR | Sí |  |  |  |
| acumula_items_renglon_codigo | VARCHAR | Sí |  |  |  |
| utiliza_display | VARCHAR | Sí |  |  |  |
| codigo_barra_busqueda | VARCHAR | Sí |  |  |  |
| cambio_lista_conserva_promo | VARCHAR | Sí |  |  |  |
| recalculo_lp_tpv_cliente | VARCHAR | Sí |  |  |  |
| cantidad2x1_desc_cant | VARCHAR | Sí |  |  |  |
| tpv_lista_precio_x_pv | VARCHAR | Sí |  |  |  |
| servidor_imagenes_nube | VARCHAR | Sí |  |  |  |
| utiliza_cambio_lp_bulto | VARCHAR | Sí |  |  |  |
| lista_cambio_lp_bulto | VARCHAR | Sí |  |  |  |
| lista_cambio_lp_display | VARCHAR | Sí |  |  |  |
| conserva_lp_bulto_descuento | VARCHAR | Sí |  |  |  |
| valida_repite_codigo_barra_interno | VARCHAR | Sí |  |  |  |
| texto_aviso_envio_mail_fact_pedido | MEDIUMTEXT | Sí |  |  |  |
| texto_aviso_envio_mail_prep_pedido | MEDIUMTEXT | Sí |  |  |  |
| redondeo_cambio_precio | VARCHAR | Sí |  |  |  |
| tpv_lista_precio_x_pv_prioridad_cliente | VARCHAR | Sí |  |  |  |
| calc_fecha_venc | VARCHAR | Sí |  |  |  |
| usuario_ARBA | VARCHAR | Sí |  |  |  |
| pass_ARBA | VARCHAR | Sí |  |  |  |
| usuario_AGIP | VARCHAR | Sí |  |  |  |
| pass_AGIP | VARCHAR | Sí |  |  |  |
| habilita_precio_peso_unidad | VARCHAR | Sí |  |  |  |
| muestra_stock_unidad_peso | VARCHAR | Sí |  |  |  |
| muestra_foto_articulo_ventanas | VARCHAR | Sí |  |  |  |
| foto_articulo_defecto_visualiza | VARCHAR | Sí |  |  |  |
| tiempo_segundos_publicidad | INT | Sí |  |  |  |
| codigo_barra_usa_ean13 | VARCHAR | Sí |  |  |  |
| fe_url_acceso_servidor_export | VARCHAR | Sí |  |  |  |
| lista_cambio_lp_unidad | VARCHAR | Sí |  |  |  |
| repite_codigo_prov | VARCHAR | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| configuracion | viajantes | Info_Estadistica.frm | 3183 | "From `configuracion`, `stock` INNER JOIN viajantes ON (`viajantes`.`CodViajante… |
| configuracion | cliente | Info_Estadistica.frm | 3361 | '"From `configuracion`,`stock` INNER JOIN cliente ON (`cliente`.`codigo` = `stoc… |
| configuracion | cliente | Info_Estadistica.frm | 3495 | '"From `configuracion`, ((((`cuentacliente` left join `cliente` on((`cuentaclien… |
| configuracion | provincia | Info_Estadistica.frm | 3495 | '"From `configuracion`, ((((`cuentacliente` left join `cliente` on((`cuentaclien… |
| configuracion | departamento | Info_Estadistica.frm | 3495 | '"From `configuracion`, ((((`cuentacliente` left join `cliente` on((`cuentaclien… |
| configuracion | distrito | Info_Estadistica.frm | 3495 | '"From `configuracion`, ((((`cuentacliente` left join `cliente` on((`cuentaclien… |
| configuracion | administranet | Conta_Info.frm | 1487 | '            rs_command.Open "SELECT configuracion.*, SUM(cont_asiento.debe_asie… |
| configuracion | administranet | Conta_Info.frm | 1493 | '            rs_command.Open "SELECT configuracion.*, SUM(cont_asiento.debe_asie… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| CargaBDeposito.frm | 2273 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| PNotaCred.frm | 6120 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| Visualiza_ReciboCobro.frm | 13381 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| Visualiza_NotaCred.frm | 5076 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| Configuracion._Adicional.frm | 2997 | SELECT | rs_configuracion.Open "SELECT * FROM configuracion", conn, a… |
| Configuracion._Adicional.frm | 3053 | SELECT | rs_configuracion.Open "SELECT * FROM configuracion", conn, a… |
| Configuracion._Adicional.frm | 3154 | SELECT | rs.Open "Select * from configuracion", conn, adOpenDynamic, … |
| Info_Estadistica.frm | 3183 | SELECT | "From `configuracion`, `stock` INNER JOIN viajantes ON (`via… |
| Info_Estadistica.frm | 3361 | SELECT | '"From `configuracion`,`stock` INNER JOIN cliente ON (`clien… |
| Info_Estadistica.frm | 3495 | SELECT | '"From `configuracion`, ((((`cuentacliente` left join `clien… |
| Visualiza_CargaMovStock.frm | 4752 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| NotaCredCon.frm | 6632 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| Configuracion_Adicional2.frm | 3826 | SELECT | rs_configuracion.Open "SELECT * FROM configuracion", conn, a… |
| Configuracion_Adicional2.frm | 4099 | SELECT | rs_configuracion.Open "SELECT * FROM configuracion", conn, a… |
| Configuracion_Adicional2.frm | 4333 | SELECT | rs.Open "Select * from configuracion", conn, adOpenDynamic, … |
| Configuracion_Adicional2.frm | 4401 | SELECT | rs.Open "Select * from configuracion", conn, adOpenDynamic, … |
| Visualiza_PNotaDeb.frm | 3026 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| Configuracion._Adicionalfrm.frm | 2830 | SELECT | rs_configuracion.Open "SELECT * FROM configuracion", conn, a… |
| Configuracion._Adicionalfrm.frm | 2882 | SELECT | rs_configuracion.Open "SELECT * FROM configuracion", conn, a… |
| FacturaB_COPIA.frm | 11256 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| NotaCredDesc.frm | 3977 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| NotaCred_COPIA.frm | 8106 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| Visualiza_TPV.frm | 8608 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| Visualiza_TPV.frm | 9545 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| Visualiza_TPV.frm | 10804 | SELECT | rs.Open "Select * from configuracion", conn, adOpenDynamic, … |
| TPV.frm | 18440 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| TPV.frm | 19652 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| TPV.frm | 39866 | SELECT | rs.Open "Select * from configuracion", conn, adOpenDynamic, … |
| Visualiza_NotaCredDesc.frm | 1943 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| CorreoEnvio2.frm | 2191 | SELECT | rs_consulta_texto.Open "SELECT texto_aviso_envio_mail FROM c… |
| CorreoEnvio2.frm | 2242 | SELECT | rs_consulta_texto.Open "SELECT texto_aviso_pago_mail FROM co… |
| CargaMovCaja.frm | 3859 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| Configuracion2.frm | 4470 | SELECT | rs_configuracion.Open "SELECT * FROM configuracion", conn, a… |
| Configuracion2.frm | 5104 | SELECT | rs_configuracion.Open "SELECT * FROM configuracion", conn, a… |
| Configuracion2.frm | 5649 | SELECT | '    rs.Open "Select * from configuracion", conn, adOpenDyna… |
| Configuracion.frm | 4537 | SELECT | rs_configuracion.Open "SELECT * FROM configuracion", conn, a… |
| Configuracion.frm | 5201 | SELECT | rs_configuracion.Open "SELECT * FROM configuracion", conn, a… |
| Configuracion.frm | 5748 | SELECT | '    rs.Open "Select * from configuracion", conn, adOpenDyna… |
| OrdenPago.frm | 13033 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| Imp_Carga.frm | 910 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| Visualiza_PNotaCred_Importe.frm | 3119 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| Visualiza_FB_Copia.frm | 6680 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| Visualiza_PNotaCredDev.frm | 4915 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| IngresoUsuario.frm | 2156 | SELECT | .Source = "SELECT DATE_FORMAT(NOW(),'%Y/%m/%d %H:%i:%s') as … |
| Visualiza_PNotaCredDesc.frm | 2644 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| FacturaB.frm | 17064 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| CM_Principal.frm | 1170 | SELECT | rs_config.Open "SELECT tablero_zoom, tablero_refresco FROM c… |
| CargaExtraccion.frm | 984 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| NotaCred_SinCompO.frm | 10440 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| FacturaA.frm | 13147 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| Visualiza_NotaDeb.frm | 3696 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| PNotaDebCopia.frm | 3366 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| NotaCred_Importe.frm | 6182 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| CargaGastoBancario.frm | 1570 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| Conta_Info.frm | 1303 | SELECT | "FROM configuracion,(`administranet`.`cont_asiento` `cont_as… |
| Conta_Info.frm | 1324 | SELECT | "FROM configuracion,(`administranet`.`cont_asiento` `cont_as… |
| Conta_Info.frm | 1358 | SELECT | '                                "FROM configuracion,(`admin… |
| Conta_Info.frm | 1381 | SELECT | '                            "FROM configuracion,(`administr… |
| Conta_Info.frm | 1478 | SELECT | '                    "FROM configuracion,(`administranet`.`c… |
| Conta_Info.frm | 1487 | SELECT | '            rs_command.Open "SELECT configuracion.*, SUM(co… |
| Conta_Info.frm | 1493 | SELECT | '            rs_command.Open "SELECT configuracion.*, SUM(co… |
| Visualiza_FA.frm | 6520 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| Inventario.frm | 2203 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| Inventario.frm | 2874 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| NotaCredCopia.frm | 8954 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| Configuracion_Adicional-2.frm | 506 | SELECT | rs_configuracion.Open "SELECT * FROM configuracion", conn, a… |
| Configuracion_Adicional-2.frm | 565 | SELECT | rs_configuracion.Open "SELECT * FROM configuracion", conn, a… |
| Visualiza_NotaCred_Importe.frm | 2913 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| Visualiza_PNotaCred_ImporteCopia.frm | 2989 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| Visualiza_FB.frm | 7215 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| PFactura.frm | 8596 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| CargaLiquidacionTC.frm | 2391 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| NotaDeb.frm | 7279 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| PNotaCredDesc.frm | 2546 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| CargaClearing.frm | 1059 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| Erp_ABM_Proyecto.frm | 1168 | SELECT | rs_nro_proyecto.Open "SELECT * FROM configuracion", conn, ad… |
| ABM_Filtros.frm | 474 | UPDATE | conn.Execute "UPDATE configuracion SET " & _ |
| Visualiza_PFactura_Copia.frm | 6264 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| Erp_Carga_Proyecto.frm | 983 | SELECT | rs_configuracion.Open "SELECT * FROM configuracion", conn, a… |
| PNotaCred_Importe.frm | 3396 | SELECT | rs_config.Open "SELECT activ_contabilidad from configuracion… |
| … | … | … | *(53 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)