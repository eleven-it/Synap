# Tabla `permisos_sistema`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_permisos_sistema | INT | No | ✓ |  |  |
| IDPuesto | INT | Sí |  |  |  |
| Mod_Precio_Fact | CHAR | Sí |  |  |  |
| cambia_cv | VARCHAR | Sí |  |  |  |
| actualiza_abm_art | VARCHAR | Sí |  |  |  |
| mod_lista_de_precio | VARCHAR | Sí |  |  |  |
| cambia_deposito | VARCHAR | Sí |  |  |  |
| cambia_caja | VARCHAR | Sí |  |  |  |
| cambia_sucursal | VARCHAR | Sí |  |  |  |
| cambia_talonario | VARCHAR | Sí |  |  |  |
| mod_descuento_pie | VARCHAR | Sí |  |  |  |
| mod_descuento_renglon | VARCHAR | Sí |  |  |  |
| visualizar_comprobantes | VARCHAR | Sí |  |  |  |
| anular_comprobantes | VARCHAR | Sí |  |  |  |
| reimprimir_comprobantes | VARCHAR | Sí |  |  |  |
| actualiza_lista_compra | VARCHAR | Sí |  |  |  |
| lista_compra_venta_defecto | VARCHAR | Sí |  |  |  |
| imprime_cheques | VARCHAR | Sí |  |  |  |
| modifica_pedido_presupuesto | VARCHAR | Sí |  |  |  |
| modifica_factura_pedido | VARCHAR | Sí |  |  |  |
| modifica_remito_pedido | VARCHAR | Sí |  |  |  |
| acceso_pv | VARCHAR | Sí |  |  |  |
| acceso_comp_ventas_talonario | VARCHAR | Sí |  |  |  |
| carga_comp_venta | VARCHAR | Sí |  |  |  |
| modifica_oc_presupuesto | VARCHAR | Sí |  |  |  |
| modifica_factura_oc | VARCHAR | Sí |  |  |  |
| modifica_remito_oc | VARCHAR | Sí |  |  |  |
| modifica_remitoc_facturac | VARCHAR | Sí |  |  |  |
| ver_cliente_sucursal | VARCHAR | Sí |  |  |  |
| ver_proveedor_sucursal | VARCHAR | Sí |  |  |  |
| carga_comp_cobranza | VARCHAR | Sí |  |  |  |
| carga_comp_ped | VARCHAR | Sí |  |  |  |
| id_refmovstock | INT | Sí |  |  |  |
| acceso_ref_movstock | VARCHAR | Sí |  |  |  |
| acceso_motivo_movstock | VARCHAR | Sí |  |  |  |
| genera_fact_rem | VARCHAR | Sí |  |  |  |
| factura_importe_cero | VARCHAR | Sí |  |  |  |
| calcula_precio_oficial | VARCHAR | Sí |  |  |  |
| autoriza_documentos | VARCHAR | Sí |  |  |  |
| cont_prev_asiento | VARCHAR | Sí |  |  |  |
| cont_acceso_contabilidad | VARCHAR | Sí |  |  |  |
| medio_cobro_pend | VARCHAR | Sí |  |  |  |
| pre_ped_otro_cliente | VARCHAR | Sí |  |  |  |
| login_supervisor_credito | VARCHAR | Sí |  |  |  |
| selec_pv | VARCHAR | Sí |  |  |  |
| cambia_cv_abmcliente | VARCHAR | Sí |  |  |  |
| cambia_lp_abmcliente | VARCHAR | Sí |  |  |  |
| modifica_comp_talonario | VARCHAR | Sí |  |  |  |
| visualiza_aviso | VARCHAR | Sí |  |  |  |
| obliga_cambvendedor | VARCHAR | Sí |  |  |  |
| caja_opciones_total | VARCHAR | Sí |  |  |  |
| obliga_selecpv | VARCHAR | Sí |  |  |  |
| desc_int_cv | VARCHAR | Sí |  |  |  |
| secuencia_tpv_cant | VARCHAR | Sí |  |  |  |
| obliga_selecTipoDevol | VARCHAR | Sí |  |  |  |
| popup_mensajeria | VARCHAR | Sí |  |  |  |
| traslada_detalle | VARCHAR | Sí |  |  |  |
| modif_prec_remito_fact | VARCHAR | Sí |  |  |  |
| remite_factura_art | VARCHAR | Sí |  |  |  |
| selec_item_total_ped_rem | VARCHAR | Sí |  |  |  |
| limita_pendientes_ped_max | VARCHAR | Sí |  |  |  |
| Habilita_selecpv_consultacomp | VARCHAR | Sí |  |  |  |
| ajuste_cta_cte | VARCHAR | Sí |  |  |  |
| selec_ejer_per_cont | VARCHAR | Sí |  |  |  |
| precio_final_fa | VARCHAR | Sí |  |  |  |
| visualiza_clientes_todos_web | VARCHAR | Sí |  |  |  |
| selec_DatosAdicionales | VARCHAR | Sí |  |  |  |
| lim_desc_pie | DECIMAL | Sí |  |  |  |
| lim_desc_renglon | DECIMAL | Sí |  |  |  |
| utiliza_lista_oficial | VARCHAR | Sí |  |  |  |
| modifica_vendedor | VARCHAR | Sí |  |  |  |
| filtra_art_proveedor | VARCHAR | Sí |  |  |  |
| pedido_web | VARCHAR | Sí |  |  |  |
| remito_web | VARCHAR | Sí |  |  |  |
| descuento_cv | VARCHAR | Sí |  |  |  |
| actualiza_abm_cliente | VARCHAR | Sí |  |  |  |
| actualiza_abm_proveedor | VARCHAR | Sí |  |  |  |
| mov_stock_utiliza_cbarra | VARCHAR | Sí |  |  |  |
| obliga_cierre_caja | VARCHAR | Sí |  |  |  |
| impresion_etiquetas | VARCHAR | Sí |  |  |  |
| seleccion_usr_total | VARCHAR | Sí |  |  |  |
| obliga_domicilio_cliente | VARCHAR | Sí |  |  |  |
| recuerda_ruta_zona | VARCHAR | Sí |  |  |  |
| alerta_crm | VARCHAR | Sí |  |  |  |
| ver_informes_gerencia_web | VARCHAR | Sí |  |  |  |
| oe_ultima_etapa | VARCHAR | Sí |  |  |  |
| impresion_oe | VARCHAR | Sí |  |  |  |
| genera_edita_oe | VARCHAR | Sí |  |  |  |
| plantillas | VARCHAR | Sí |  |  |  |
| art_precios_negativos | VARCHAR | Sí |  |  |  |
| fiscal_cambio | VARCHAR | Sí |  |  |  |
| fiscal_codigo_linea_comp | VARCHAR | Sí |  |  |  |
| abmcli_mod_vendedor | VARCHAR | Sí |  |  |  |
| abmcli_mod_desc | VARCHAR | Sí |  |  |  |
| bloquea_oc | VARCHAR | Sí |  |  |  |
| oe_deposito_origenxarticulo | VARCHAR | Sí |  |  |  |
| informes_vendedor | VARCHAR | Sí |  |  |  |
| nc_ruta_cerrada | VARCHAR | Sí |  |  |  |
| serie_cod_barra | VARCHAR | Sí |  |  |  |
| mod_fecha_venta | VARCHAR | Sí |  |  |  |
| mod_item_pre_ped | VARCHAR | Sí |  |  |  |
| reporte_pedido | VARCHAR | Sí |  |  |  |
| ventana_busqueda_art | VARCHAR | Sí |  |  |  |
| logi_repite_ruta_prepp | VARCHAR | Sí |  |  |  |
| utiliza_embalaje | VARCHAR | Sí |  |  |  |

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
| FacturaB_COPIA.frm | 3558 | SELECT | rs_limdesc.Open "SELECT lim_desc_pie FROM permisos_sistema W… |
| FacturaB_COPIA.frm | 6977 | SELECT | rs_limdesc.Open "SELECT lim_desc_renglon FROM permisos_siste… |
| NotaCred_COPIA.frm | 2407 | SELECT | '    rs_limdesc.Open "SELECT lim_desc_pie FROM permisos_sist… |
| TPV.frm | 5433 | SELECT | '                    rs_limdesc.Open "SELECT lim_desc_pie FR… |
| TPV.frm | 16247 | SELECT | '                        rs_limdesc.Open "SELECT lim_desc_re… |
| Visualiza_Pedido.frm | 4742 | SELECT | rs_limdesc.Open "SELECT lim_desc_renglon FROM permisos_siste… |
| Articulo.frm | 12483 | SELECT | '                        rs_limdesc.Open "SELECT lim_desc_re… |
| Articulo.frm | 13490 | SELECT | '                        rs_limdesc.Open "SELECT lim_desc_re… |
| Articulo.frm | 14492 | SELECT | '                        rs_limdesc.Open "SELECT lim_desc_re… |
| Articulo.frm | 15491 | SELECT | '                        rs_limdesc.Open "SELECT lim_desc_re… |
| IngresoUsuario.frm | 2314 | SELECT | .Source = "SELECT * FROM permisos_sistema WHERE idpuesto=" &… |
| IngresoUsuario.frm | 2799 | SELECT | .Source = "SELECT  * FROM permisos_sistema where IDpuesto = … |
| FacturaB.frm | 4495 | SELECT | '                    rs_limdesc.Open "SELECT lim_desc_pie FR… |
| FacturaB.frm | 7311 | SELECT | '                    rs_limdesc.Open "SELECT lim_desc_pie FR… |
| FacturaB.frm | 11759 | SELECT | '                rs_limdesc.Open "SELECT lim_desc_renglon FR… |
| Clave_Supervisor.frm | 652 | JOIN | "INNER JOIN permisos_sistema ON (permisos_sistema.IDPuesto =… |
| FacturaA.frm | 4210 | SELECT | '                    rs_limdesc.Open "SELECT lim_desc_pie FR… |
| FacturaA.frm | 7147 | SELECT | '                rs_limdesc.Open "SELECT lim_desc_renglon FR… |
| TPV_Modifica_Renglon.frm | 1159 | SELECT | '                rs_limdesc.Open "SELECT lim_desc_renglon FR… |
| CargaPuesto.frm | 689 | SELECT | rs_permiso_sistema.Open "SELECT * FROM permisos_sistema wher… |
| CargaPermiso_Sistema_Puesto.frm | 3117 | SELECT | rs_permisos_sistema.Open "SELECT * FROM permisos_sistema WHE… |
| Presupuesto.frm | 3681 | SELECT | rs_limdesc.Open "SELECT lim_desc_pie FROM permisos_sistema W… |
| Presupuesto.frm | 4822 | SELECT | rs_limdesc.Open "SELECT lim_desc_renglon FROM permisos_siste… |
| Pedido.frm | 3853 | SELECT | rs_limdesc.Open "SELECT lim_desc_pie FROM permisos_sistema W… |
| Pedido.frm | 5284 | SELECT | rs_limdesc.Open "SELECT lim_desc_renglon FROM permisos_siste… |
| Logi_Renglon.frm | 2138 | SELECT | rs_limdesc.Open "SELECT lim_desc_renglon FROM permisos_siste… |
| Facturacion_Ciclica_Renglon.frm | 2502 | SELECT | rs_limdesc.Open "SELECT lim_desc_renglon FROM permisos_siste… |
| Visualiza_Presupuesto.frm | 4568 | SELECT | rs_limdesc.Open "SELECT lim_desc_renglon FROM permisos_siste… |
| ABMPermiso_Sistema.frm | 488 | SELECT | DataPermisos_Sistema.RecordSource = "select * from permisos_… |
| TPV_2.frm | 5035 | SELECT | '                    rs_limdesc.Open "SELECT lim_desc_pie FR… |
| TPV_2.frm | 14589 | SELECT | '                        rs_limdesc.Open "SELECT lim_desc_re… |
| CargaPermiso_Sistema.frm | 4360 | SELECT | rs_permisos_sistema.Open "SELECT * FROM permisos_sistema WHE… |
| CargaPermiso_Sistema.frm | 4623 | SELECT | ABMPermiso_Sistema.DataPermisos_Sistema.RecordSource = "sele… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)