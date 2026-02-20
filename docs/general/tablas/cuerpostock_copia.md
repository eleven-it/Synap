# Tabla `cuerpostock_copia`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| Orden | DOUBLE | No | ✓ |  |  |
| IDArt | DECIMAL | Sí |  |  |  |
| CodigoArticulo | VARCHAR | Sí |  |  |  |
| Descripcion | VARCHAR | Sí |  |  |  |
| Cantidad | DECIMAL | Sí |  |  |  |
| entrada | DECIMAL | Sí |  |  |  |
| salida | DECIMAL | Sí |  |  |  |
| CantidadOr | DECIMAL | Sí |  |  |  |
| ES | VARCHAR | Sí |  |  |  |
| PrecioCostoxU | DECIMAL | Sí |  |  |  |
| PrecioVentaxU | DECIMAL | Sí |  |  |  |
| PrecioBrutoxU | DECIMAL | Sí |  |  |  |
| PrecioBrutoxUSD | DECIMAL | Sí |  |  |  |
| PrecioNetoxU | DECIMAL | Sí |  |  |  |
| PrecioIVAxU | DECIMAL | Sí |  |  |  |
| PrecioCostoxR | DECIMAL | Sí |  |  |  |
| PrecioVentaxR | DECIMAL | Sí |  |  |  |
| PrecioVentaxRD | DECIMAL | Sí |  |  |  |
| PrecioBrutoxR | DECIMAL | Sí |  |  |  |
| PrecioNetoxR | DECIMAL | Sí |  |  |  |
| PrecioIVAxR | DECIMAL | Sí |  |  |  |
| ImpDesc | DECIMAL | Sí |  |  |  |
| PorDesc | DECIMAL | Sí |  |  |  |
| Alicuota | INT | Sí |  |  |  |
| AlicuotaIB | INT | Sí |  |  |  |
| ImpIB | DECIMAL | Sí |  |  |  |
| NetoIB | DECIMAL | Sí |  |  |  |
| TipoIVA | VARCHAR | Sí |  |  |  |
| CodigoMovimiento | DECIMAL | Sí |  |  |  |
| Seleccionado | TINYINT | Sí |  |  |  |
| CodUsuario | INT | No |  |  |  |
| CodDeposito | INT | Sí |  |  |  |
| cod_deposito_destino | INT | Sí |  |  |  |
| NroPresupuesto | VARCHAR | Sí |  |  |  |
| NroPedido | VARCHAR | Sí |  |  |  |
| NroRemito | VARCHAR | Sí |  |  |  |
| Detalle | MEDIUMTEXT | Sí |  |  |  |
| CodViajante | INT | Sí |  |  |  |
| CodLaboratorio | INT | Sí |  |  |  |
| id_lote | INT | Sí |  |  |  |
| cod_lote | VARCHAR | Sí |  |  |  |
| vto_lote | DATE | Sí |  |  |  |
| lote | VARCHAR | Sí |  |  |  |
| tipo_art | VARCHAR | Sí |  |  |  |
| id_manual | VARCHAR | Sí |  |  |  |
| imp_alicuota_iva | DECIMAL | Sí |  |  |  |
| imp_alicuota_iibb | DECIMAL | Sí |  |  |  |
| lista_precio | INT | Sí |  |  |  |
| codmov_presupuesto | DECIMAL | Sí |  |  |  |
| codmov_remito | DECIMAL | Sí |  |  |  |
| codmov_pedido | DECIMAL | Sí |  |  |  |
| promocion | VARCHAR | Sí |  |  |  |
| promocion_por | DECIMAL | Sí |  |  |  |
| promocion_cant | DECIMAL | Sí |  |  |  |
| promocion_tipo | VARCHAR | Sí |  |  |  |
| nro_pedi | VARCHAR | Sí |  |  |  |
| codmov_nro_pedi | DECIMAL | Sí |  |  |  |
| impuesto_interno | DECIMAL | Sí |  |  |  |
| impuesto_interno_subtotal | DECIMAL | Sí |  |  |  |
| id_stock | DECIMAL | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| descuenta_stock_nc | VARCHAR | Sí |  |  |  |
| multiplicador_comp | DECIMAL | Sí |  |  |  |
| multiplicador_vta | DECIMAL | Sí |  |  |  |
| id_unimed_vta | DOUBLE | Sí |  |  |  |
| id_unimed_comp | DOUBLE | Sí |  |  |  |
| cantidad_uni | DECIMAL | Sí |  |  |  |
| id_presentacion_vta | DOUBLE | Sí |  |  |  |
| id_presentacion_comp | DOUBLE | Sí |  |  |  |
| nombre_unimed_vta | VARCHAR | Sí |  |  |  |
| nombre_unimed_comp | VARCHAR | Sí |  |  |  |
| nombre_presentacion_vta | VARCHAR | Sí |  |  |  |
| nombre_presentacion_comp | VARCHAR | Sí |  |  |  |
| id_serie_entrada | DOUBLE | Sí |  |  |  |
| desc_serie | MEDIUMTEXT | Sí |  |  |  |
| serie | VARCHAR | Sí |  |  |  |
| unidad_art_peso | DOUBLE | Sí |  |  |  |
| codmov_dev | BIGINT | Sí |  |  |  |
| NroDev | VARCHAR | Sí |  |  |  |
| nro_despacho | VARCHAR | Sí |  |  |  |
| id_cotizacion | INT | Sí |  |  |  |
| coti_dolar | DOUBLE | Sí |  |  |  |
| id_marca | BIGINT | Sí |  |  |  |
| marca | VARCHAR | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
| id_cliente | BIGINT | Sí |  |  |  |
| nro_comp | VARCHAR | Sí |  |  |  |
| tipo_comp | VARCHAR | Sí |  |  |  |
| comprobante | VARCHAR | Sí |  |  |  |
| id_cv | INT | Sí |  |  |  |
| monto_descuento_pie | DOUBLE | Sí |  |  |  |
| monto_interes | DOUBLE | Sí |  |  |  |
| detalle_comp | MEDIUMTEXT | Sí |  |  |  |
| id_vendedor | INT | Sí |  |  |  |
| comp_tpv | VARCHAR | Sí |  |  |  |

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
| TPV.frm | 39231 | SELECT | conn.Execute "DELETE FROM cuerpostock_copia WHERE cuerpostoc… |
| TPV.frm | 39231 | DELETE | conn.Execute "DELETE FROM cuerpostock_copia WHERE cuerpostoc… |
| TPV.frm | 39235 | SELECT | rs_cuerpostock_copia.Open "SELECT * FROM cuerpostock_copia W… |
| FacturaB.frm | 26612 | SELECT | conn.Execute "DELETE FROM cuerpostock_copia WHERE cuerpostoc… |
| FacturaB.frm | 26612 | DELETE | conn.Execute "DELETE FROM cuerpostock_copia WHERE cuerpostoc… |
| FacturaB.frm | 26616 | SELECT | rs_cuerpostock_copia.Open "SELECT * FROM cuerpostock_copia W… |
| FacturaA.frm | 22454 | SELECT | conn.Execute "DELETE FROM cuerpostock_copia WHERE cuerpostoc… |
| FacturaA.frm | 22454 | DELETE | conn.Execute "DELETE FROM cuerpostock_copia WHERE cuerpostoc… |
| FacturaA.frm | 22458 | SELECT | rs_cuerpostock_copia.Open "SELECT * FROM cuerpostock_copia W… |
| NotaCredCopia.frm | 5403 | SELECT | conn.Execute "delete from cuerpostock_copia where CodUsuario… |
| NotaCredCopia.frm | 5403 | DELETE | conn.Execute "delete from cuerpostock_copia where CodUsuario… |
| adm_felectronicas_consulta.frm | 2405 | SELECT | rs_cuerpostock_copia.Open "SELECT * FROM cuerpostock_copia W… |
| NotaCred.frm | 5550 | SELECT | '                conn.Execute "delete from cuerpostock_copia… |
| NotaCred.frm | 5550 | DELETE | '                conn.Execute "delete from cuerpostock_copia… |
| TPV_2.frm | 36564 | SELECT | conn.Execute "DELETE FROM cuerpostock_copia WHERE cuerpostoc… |
| TPV_2.frm | 36564 | DELETE | conn.Execute "DELETE FROM cuerpostock_copia WHERE cuerpostoc… |
| TPV_2.frm | 36568 | SELECT | rs_cuerpostock_copia.Open "SELECT * FROM cuerpostock_copia W… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)