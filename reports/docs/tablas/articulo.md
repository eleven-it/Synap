# Tabla `articulo`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| IDArt | INT | No | ✓ |  |  |
| id_manual | VARCHAR | Sí |  |  |  |
| CodigoRubro | INT | Sí |  |  |  |
| CodigoSubRubro | INT | No |  |  |  |
| CodigoSubRubroT | VARCHAR | No |  |  |  |
| CodigoArticulo | INT | Sí |  |  |  |
| IDSubRubro | INT | Sí |  |  |  |
| CodigoArticuloT | VARCHAR | No |  |  |  |
| CodArtProv | VARCHAR | Sí |  |  |  |
| NombreArticulo | VARCHAR | Sí |  |  |  |
| PrecioCosto | DECIMAL | Sí |  |  |  |
| Util1 | DECIMAL | Sí |  |  |  |
| Util2 | DECIMAL | Sí |  |  |  |
| Util3 | DECIMAL | Sí |  |  |  |
| Util4 | DECIMAL | Sí |  |  |  |
| Util5 | DECIMAL | Sí |  |  |  |
| Precio1V | DECIMAL | Sí |  |  |  |
| Precio2V | DECIMAL | Sí |  |  |  |
| Precio3V | DECIMAL | Sí |  |  |  |
| Precio4V | DECIMAL | Sí |  |  |  |
| Precio5V | DECIMAL | Sí |  |  |  |
| Precio1VI | DECIMAL | Sí |  |  |  |
| Precio2VI | DECIMAL | Sí |  |  |  |
| Precio3VI | DECIMAL | Sí |  |  |  |
| Precio4VI | DECIMAL | Sí |  |  |  |
| Precio5VI | DECIMAL | Sí |  |  |  |
| PNOficial | DECIMAL | Sí |  |  |  |
| PFOficial | DECIMAL | Sí |  |  |  |
| PorOficial1 | DECIMAL | Sí |  |  |  |
| PorOficial2 | DECIMAL | Sí |  |  |  |
| PorOficial3 | DECIMAL | Sí |  |  |  |
| UtilOficial | DECIMAL | Sí |  |  |  |
| Alicuota | INT | Sí |  |  |  |
| AlicuotaIB | INT | No |  |  |  |
| saldo_articulo | INT | Sí |  |  |  |
| Moneda | VARCHAR | Sí |  |  |  |
| TipoIVA | VARCHAR | Sí |  |  |  |
| TipoIB | VARCHAR | No |  |  |  |
| CodigoProveedor | INT | Sí |  |  |  |
| CodigoModelo | INT | Sí |  |  |  |
| CodigoMarca | INT | Sí |  |  |  |
| CodLaboratorio | INT | Sí |  |  |  |
| NroCodBarra | VARCHAR | Sí |  |  |  |
| NroCodBarraF | VARCHAR | Sí |  |  |  |
| Simbologia | VARCHAR | Sí |  |  |  |
| SimbologiaF | VARCHAR | Sí |  |  |  |
| Foto1 | LONGBLOB | Sí |  |  |  |
| Foto2 | LONGBLOB | Sí |  |  |  |
| Discontinuo | VARCHAR | No |  |  |  |
| Detalle | LONGTEXT | Sí |  |  |  |
| lote | VARCHAR | Sí |  |  |  |
| tipo_art | VARCHAR | Sí |  |  |  |
| cod_gasto | INT | Sí |  |  |  |
| cod_act_iibb | INT | Sí |  |  |  |
| stock_max | DECIMAL | Sí |  |  |  |
| stock_min | DECIMAL | Sí |  |  |  |
| punto_pedido | INT | Sí |  |  |  |
| promocion | VARCHAR | Sí |  |  |  |
| promocion_por | DECIMAL | Sí |  |  |  |
| promocion_cant | DECIMAL | Sí |  |  |  |
| promocion_alcance | VARCHAR | Sí |  |  |  |
| promocion_tipo | VARCHAR | Sí |  |  |  |
| promocion_listaoficial | VARCHAR | Sí |  |  |  |
| promocion_lista1 | VARCHAR | Sí |  |  |  |
| promocion_lista2 | VARCHAR | Sí |  |  |  |
| promocion_lista3 | VARCHAR | Sí |  |  |  |
| promocion_lista4 | VARCHAR | Sí |  |  |  |
| promocion_lista5 | VARCHAR | Sí |  |  |  |
| promocion_destacado_web | VARCHAR | Sí |  |  |  |
| impuesto_interno | DECIMAL | Sí |  |  |  |
| promocion_vigencia_hasta | DATE | Sí |  |  |  |
| promocion_vigencia_desde | DATE | Sí |  |  |  |
| id_unimed | DOUBLE | Sí |  |  |  |
| AlicuotaC | INT | Sí |  |  |  |
| ecommerce | VARCHAR | Sí |  |  |  |
| id_pc_vta | DOUBLE | Sí |  |  |  |
| id_pc_comp | DOUBLE | Sí |  |  |  |
| limVtaxArt | DECIMAL | Sí |  |  |  |
| detalle_web | LONGTEXT | Sí |  |  |  |
| id_proyecto | INT | Sí |  |  |  |
| recalcula_pc | VARCHAR | Sí |  |  |  |
| recalcula_pv | VARCHAR | Sí |  |  |  |
| ensamblado | VARCHAR | Sí |  |  |  |
| id_en_abm | DOUBLE | Sí |  |  |  |
| multiplicador_vta | DECIMAL | Sí |  |  |  |
| id_presentacionV | DOUBLE | Sí |  |  |  |
| formulacion_nom_matriz | VARCHAR | Sí |  |  |  |
| transmite_datos | VARCHAR | Sí |  |  |  |
| disponible_vta | VARCHAR | Sí |  |  |  |
| disponible_comp | VARCHAR | Sí |  |  |  |
| promo_destacado | VARCHAR | Sí |  |  |  |
| serie | VARCHAR | Sí |  |  |  |
| tipo_regla | VARCHAR | Sí |  |  |  |
| importe_regla | DECIMAL | Sí |  |  |  |
| prioridad_regla | VARCHAR | Sí |  |  |  |
| integracion_balanza | VARCHAR | Sí |  |  |  |
| cantidad_promedio_bulto | DECIMAL | Sí |  |  |  |
| nro_despacho | VARCHAR | Sí |  |  |  |
| costo_dolar | DECIMAL | Sí |  |  |  |
| selec_costo_dolar | VARCHAR | Sí |  |  |  |
| costo_adicional | DECIMAL | Sí |  |  |  |
| comprobante_interno | VARCHAR | Sí |  |  |  |
| id_cotizacion | INT | Sí |  |  |  |
| id_descuento_proveedor | BIGINT | Sí |  |  |  |
| id_impuesto_interno_abm | BIGINT | Sí |  |  |  |
| promo_prioridad_regla_precio | VARCHAR | Sí |  |  |  |
| nro_cod_barra_bulto | VARCHAR | Sí |  |  |  |
| nro_cod_barra_display | VARCHAR | Sí |  |  |  |
| stock_promocion | DOUBLE | Sí |  |  |  |
| fecha_alta | TIMESTAMP | Sí |  |  |  |
| fecha_mod | TIMESTAMP | Sí |  |  |  |
| sin_tacc | VARCHAR | Sí |  |  |  |
| costo_proveedor | DOUBLE | Sí |  |  |  |
| dias_vencimiento | INT | Sí |  |  |  |
| id_articulo_categoria | BIGINT | Sí |  |  |  |
| desc_comercial | DOUBLE | Sí |  |  |  |
| id_tiendanube | BIGINT | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| crm_articulo | articulo | Crm_CargaLlamada.frm | 4162 | sql_lista = "SELECT * FROM crm_articulo INNER JOIN articulo ON (crm_articulo.id_… |
| articulo | stock_deposito | Sup_importacion_tablas.frm | 11031 | '                "SELECT articulo.IDArt,deposito.CodDeposito FROM articulo LEFT … |
| crm_articulo | articulo | Crm_Presupuesto_Llamada.frm | 681 | 'SELECT * FROM crm_articulo INNER JOIN articulo ON (crm_articulo.id_articulo = a… |
| crm_articulo | articulo | Crm_Presupuesto_Llamada.frm | 682 | rs_articulo.Open "SELECT * FROM crm_articulo INNER JOIN articulo ON (crm_articul… |
| crm_articulo | articulo | Crm_Presupuesto_Llamada.frm | 692 | rs_stock.Open "SELECT * FROM crm_articulo INNER JOIN articulo ON (crm_articulo.i… |
| articulo | en_abm_formula | Principal.frm | 7532 | " FROM articulo LEFT JOIN en_abm_formula as formula ON formula.id_articulo = art… |
| en_abm_formula | articulo | Principal.frm | 7549 | " FROM en_abm_formula As formula LEFT JOIN articulo AS insumo ON insumo.IDArt=fo… |
| en_abm_formula | articulo | Principal.frm | 7693 | " FROM en_abm_formula As formula LEFT JOIN articulo AS insumo ON insumo.IDArt=fo… |
| en_abm_formula | articulo | Principal.frm | 7702 | " FROM en_abm_formula As formula LEFT JOIN articulo AS insumo ON insumo.IDArt=fo… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| Cliente.frm | 2388 | SELECT | rs_articulo.Open "SELECT DISTINCT * FROM articulo where Disc… |
| Cliente.frm | 4151 | SELECT | rs_r.Open "SELECT CodigoProveedor, CodigoRubro, IDSubRubro F… |
| Cliente.frm | 4324 | SELECT | rs_r.Open "SELECT CodigoProveedor, CodigoRubro, IDSubRubro F… |
| PNotaCred.frm | 5086 | SELECT | " FROM articulo " & _ |
| PNotaCred.frm | 6735 | SELECT | rs_vect.Open "SELECT * from articulo where idart = " & Cuerp… |
| PNotaCred.frm | 7518 | JOIN | "INNER JOIN articulo ON (articulo.IDArt = cuerpostockp.IDArt… |
| PNotaCred.frm | 7768 | JOIN | "INNER JOIN articulo ON (articulo.IDArt = cuerpostockp.IDArt… |
| PNotaCred.frm | 7792 | SELECT | "FROM articulo " & _ |
| Liq_Carga_Comision_avanzada.frm | 926 | SELECT | Sql = "SELECT DISTINCT CodigoMarca AS codigo FROM articulo W… |
| Liq_Carga_Comision_avanzada.frm | 928 | SELECT | Sql = "SELECT DISTINCT CodigoRubro AS codigo FROM articulo W… |
| Liq_Carga_Comision_avanzada.frm | 930 | SELECT | Sql = "SELECT DISTINCT CodigoSubRubro AS codigo FROM articul… |
| Stock_Control_Entrada.frm | 764 | JOIN | " LEFT JOIN articulo ON (articulo.IDArt = stock.IDArt) " & _ |
| Visualiza_NotaCred.frm | 5124 | SELECT | rs_vect.Open "SELECT * from articulo where idart = " & Cuerp… |
| Visualiza_NotaCred.frm | 6082 | JOIN | "INNER JOIN articulo ON (articulo.IDArt = cuerpostock.IDArt … |
| Visualiza_NotaCred.frm | 6217 | JOIN | "INNER JOIN articulo ON (articulo.IDArt = cuerpostock.IDArt … |
| Visualiza_NotaCred.frm | 6233 | JOIN | "INNER JOIN articulo ON (articulo.IDArt = cuerpostock.IDArt … |
| Visualiza_NotaCred.frm | 6289 | SELECT | "FROM articulo " & _ |
| Visualiza_NotaCred.frm | 6375 | JOIN | "INNER JOIN articulo ON (articulo.IDArt = cuerpostock.IDArt … |
| Erp_Carga_Parte_Diario.frm | 3884 | JOIN | " LEFT JOIN articulo AS ar ON ar.`IDArt` = pr.id_articulo" &… |
| Erp_Carga_Parte_Diario.frm | 4127 | SELECT | 'Data_Articulos.RecordSource = "SELECT IDArt,NombreArticulo,… |
| Erp_Carga_Parte_Diario.frm | 4128 | SELECT | Data_Articulos.RecordSource = "SELECT IDArt,NombreArticulo,t… |
| Erp_Carga_Parte_Diario.frm | 4286 | SELECT | 'SELECT IDArt,NombreArticulo FROM articulo WHERE NombreArtic… |
| Erp_Carga_Parte_Diario.frm | 4431 | SELECT | Data_Articulos.RecordSource = "SELECT IDArt,NombreArticulo,t… |
| Articulo_tipo_cliente.frm | 764 | SELECT | "From articulo " & _ |
| Articulo_tipo_cliente.frm | 791 | JOIN | "RIGHT JOIN articulo ON (articulo.IDArt = articulo_tipo_clie… |
| Articulo_tipo_cliente.frm | 961 | JOIN | "RIGHT JOIN articulo ON (articulo.IDArt = articulo_tipo_clie… |
| Articulo_Carga_datos_adicional.frm | 2251 | SELECT | " subrubro.NombreSubRubro as NombSubRub FROM articulo " & _ |
| Articulo_Carga_datos_adicional.frm | 2270 | SELECT | " subrubro.NombreSubRubro as NombSubRub FROM articulo " & _ |
| Articulo_Carga_datos_adicional.frm | 2529 | SELECT | " FROM articulo " & _ |
| Articulo_Carga_datos_adicional.frm | 2629 | SELECT | rs_articulo_consulta.Open "SELECT NombreArticulo,nrocodbarra… |
| Articulo_Carga_datos_adicional.frm | 2640 | SELECT | rs_articulo_consulta.Open "SELECT NombreArticulo,nro_cod_bar… |
| Articulo_Carga_datos_adicional.frm | 2651 | SELECT | rs_articulo_consulta.Open "SELECT NombreArticulo,nro_cod_bar… |
| Articulo_Carga_datos_adicional.frm | 2679 | UPDATE | sentencia_tabla = "UPDATE articulo " |
| Articulo_Carga_datos_adicional.frm | 2689 | SELECT | rs_articulo.Open "SELECT * FROM articulo WHERE IDArt = " & i… |
| Visualiza_CargaMovStock.frm | 3669 | SELECT | rs_consul.Open "select * from articulo where idart = " & ID_… |
| Visualiza_CargaMovStock.frm | 3727 | SELECT | rs_consul.Open "select * from articulo where idart = " & ID_… |
| Visualiza_CargaMovStock.frm | 4603 | SELECT | ABMArticulo_seleccion.DataABMArt.RecordSource = "SELECT * fr… |
| Visualiza_CargaMovStock.frm | 4821 | SELECT | rs_vect.Open "SELECT * from articulo where idart = " & Cuerp… |
| Visualiza_CargaMovStock.frm | 5999 | JOIN | "INNER JOIN articulo ON (articulo.IDArt = cuerpostock_mstock… |
| Visualiza_CargaMovStock.frm | 6104 | JOIN | "INNER JOIN articulo ON (articulo.IDArt = cuerpostock_mstock… |
| Visualiza_CargaMovStock.frm | 6126 | SELECT | "FROM articulo " & _ |
| AsigProvArt.frm | 800 | UPDATE | conn.Execute "UPDATE articulo SET articulo.CodigoProveedor =… |
| AsigProvArt.frm | 886 | SELECT | " FROM articulo" & _ |
| FacturaB_COPIA.frm | 4561 | SELECT | rs_consulta_articulo.Open "SELECT articulo.IDArt,articulo.ti… |
| FacturaB_COPIA.frm | 4974 | SELECT | "FROM articulo " & _ |
| FacturaB_COPIA.frm | 7016 | SELECT | rs_LimVtaxArt.Open "SELECT idart, limVtaxArt from articulo w… |
| FacturaB_COPIA.frm | 7461 | SELECT | "FROM articulo " & _ |
| FacturaB_COPIA.frm | 7481 | SELECT | 'rs_multi.Open "SELECT multiplicador_vta, CodigoProveedor FR… |
| FacturaB_COPIA.frm | 7484 | SELECT | "FROM articulo " & _ |
| FacturaB_COPIA.frm | 7576 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant from arti… |
| FacturaB_COPIA.frm | 7868 | SELECT | rs_mon.Open "SELECT moneda FROM articulo WHERE IDArt = " & F… |
| FacturaB_COPIA.frm | 9522 | SELECT | "FROM articulo " & _ |
| FacturaB_COPIA.frm | 9614 | SELECT | " FROM articulo " & _ |
| FacturaB_COPIA.frm | 10563 | SELECT | rs_articulo.Open "SELECT * FROM articulo where IDArt = " & C… |
| FacturaB_COPIA.frm | 11765 | SELECT | rs_vect.Open "SELECT * from articulo where idart = " & Cuerp… |
| FacturaB_COPIA.frm | 15965 | SELECT | rs_vect.Open "SELECT * from articulo where idart = " & Cuerp… |
| FacturaB_COPIA.frm | 16546 | JOIN | "INNER JOIN articulo ON (articulo.IDArt = cuerpostock.IDArt … |
| FacturaB_COPIA.frm | 16619 | JOIN | "INNER JOIN articulo ON (articulo.IDArt = cuerpostock.IDArt … |
| FacturaB_COPIA.frm | 16642 | SELECT | "FROM articulo " & _ |
| FacturaB_COPIA.frm | 17018 | SELECT | rs_r.Open "SELECT CodigoProveedor, CodigoRubro, IDSubRubro F… |
| FacturaB_COPIA.frm | 17191 | SELECT | rs_r.Open "SELECT CodigoProveedor, CodigoRubro, IDSubRubro F… |
| FacturaB_COPIA.frm | 17336 | SELECT | rs_articulo.Open "SELECT * From articulo " & _ |
| FacturaB_COPIA.frm | 17645 | SELECT | rs_articulo.Open "SELECT * From Articulo WHERE IDArt = " & I… |
| FacturaB_COPIA.frm | 17789 | SELECT | rs_lote.Open "SELECT * FROM articulo WHERE IDArt = " & rs_st… |
| FacturaB_COPIA.frm | 17904 | SELECT | rs_idEn.Open "SELECT ensamblado FROM articulo " & _ |
| FacturaB_COPIA.frm | 17916 | SELECT | rs_idEn.Open "SELECT id_en_abm FROM articulo " & _ |
| Rprecios_abm.frm | 2107 | SELECT | "From articulo " & _ |
| Rprecios_abm.frm | 2843 | JOIN | "LEFT JOIN Articulo ON (articulo.IdArt = reglas_precio.id_ar… |
| NotaCred_COPIA.frm | 8154 | SELECT | rs_vect.Open "SELECT * from articulo where idart = " & Cuerp… |
| NotaCred_COPIA.frm | 11457 | SELECT | rs_vect.Open "SELECT * from articulo where idart = " & Cuerp… |
| NotaCred_COPIA.frm | 12135 | JOIN | "INNER JOIN articulo ON (articulo.IDArt = cuerpostock.IDArt … |
| NotaCred_COPIA.frm | 12264 | JOIN | "INNER JOIN articulo ON (articulo.IDArt = cuerpostock.IDArt … |
| NotaCred_COPIA.frm | 12287 | SELECT | "FROM articulo " & _ |
| Visualiza_TPV.frm | 6942 | SELECT | "FROM articulo, iva WHERE " & _ |
| Visualiza_TPV.frm | 6955 | SELECT | "FROM articulo, iva WHERE " & _ |
| Visualiza_TPV.frm | 6972 | SELECT | rs_LimVtaxArt.Open "SELECT idart, limVtaxArt from articulo w… |
| Visualiza_TPV.frm | 8982 | SELECT | rs_vect.Open "SELECT * from articulo where idart = " & data_… |
| Visualiza_TPV.frm | 9593 | SELECT | rs_vect.Open "SELECT * from articulo where idart = " & data_… |
| Visualiza_TPV.frm | 10637 | SELECT | "FROM articulo " & _ |
| TPV.frm | 9606 | SELECT | rs_consulta_articulo.Open "SELECT articulo.IDArt,articulo.ti… |
| … | … | … | *(1410 referencias más)* |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| services/reconciliation_saldo_stock.py | 118 | SELECT | f"SELECT IDArt, COALESCE(id_manual,'') AS id_manual, COALESC… |
| services/query_runner.py | 2863 | JOIN | 4) Subrubro: existe. Tabla subrubro, join articulo.IDSubRubr… |
| services/query_runner.py | 3151 | JOIN | LEFT JOIN articulo a ON a.IDArt = sp.IDArt |
| services/query_runner.py | 3556 | JOIN | LEFT JOIN articulo a ON a.IDArt = spr.IDArt |
| services/reconciliation_saldo_pedido_proveedor.py | 271 | SELECT | f"SELECT IDArt, COALESCE(id_manual,'') AS id_manual, COALESC… |

[← Índice de tablas](../DB_INDICE_TABLAS.md)