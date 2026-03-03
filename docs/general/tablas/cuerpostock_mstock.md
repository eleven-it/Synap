# Tabla `cuerpostock_mstock`

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
| Seleccionado | CHAR | Sí |  |  |  |
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
| cantidad_pres_comp | DECIMAL | Sí |  |  |  |
| multiplicador_comp | DECIMAL | Sí |  |  |  |
| multiplicador_vta | DECIMAL | Sí |  |  |  |
| cantidad_uni | DECIMAL | Sí |  |  |  |
| id_serie_entrada | DOUBLE | Sí |  |  |  |
| desc_serie | MEDIUMTEXT | Sí |  |  |  |
| serie | VARCHAR | Sí |  |  |  |
| id_cotizacion | INT | Sí |  |  |  |
| coti_dolar | DOUBLE | Sí |  |  |  |
| id_marca | BIGINT | Sí |  |  |  |
| marca | VARCHAR | Sí |  |  |  |
| tipo_unidad | VARCHAR | Sí |  |  |  |
| cantidad_unidad_display | DOUBLE | Sí |  |  |  |
| cantidad_bulto | DOUBLE | Sí |  |  |  |
| cantidad_dividir | DOUBLE | Sí |  |  |  |
| unidad_art_peso | DOUBLE | Sí |  |  |  |

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
| Visualiza_CargaMovStock.frm | 2748 | SELECT | 'CuerpoStock.RecordSource = "SELECT * FROM cuerpostock_mstoc… |
| Visualiza_CargaMovStock.frm | 3412 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock_mstock… |
| Visualiza_CargaMovStock.frm | 3692 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock_mstock… |
| Visualiza_CargaMovStock.frm | 3775 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock_mstock… |
| Visualiza_CargaMovStock.frm | 3828 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock_mstock… |
| Visualiza_CargaMovStock.frm | 4091 | SELECT | conn.Execute "DELETE FROM cuerpostock_mstock WHERE Orden = "… |
| Visualiza_CargaMovStock.frm | 4091 | DELETE | conn.Execute "DELETE FROM cuerpostock_mstock WHERE Orden = "… |
| Visualiza_CargaMovStock.frm | 4107 | SELECT | conn.Execute "DELETE FROM cuerpostock_mstock WHERE Orden = "… |
| Visualiza_CargaMovStock.frm | 4107 | DELETE | conn.Execute "DELETE FROM cuerpostock_mstock WHERE Orden = "… |
| Visualiza_CargaMovStock.frm | 4688 | SELECT | conn.Execute "delete from cuerpostock_mstock where Codusuari… |
| Visualiza_CargaMovStock.frm | 4688 | DELETE | conn.Execute "delete from cuerpostock_mstock where Codusuari… |
| Visualiza_CargaMovStock.frm | 4709 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock_mstock… |
| Serie_salida.frm | 877 | UPDATE | conn.Execute "UPDATE cuerpostock_mstock " & _ |
| Lista_Pedidos_OPT.frm | 1580 | SELECT | rs_valid_ingreso_comp.Open "SELECT * FROM cuerpostock_mstock… |
| Lista_Pedidos_OPT.frm | 1596 | SELECT | CargaMovStock.CuerpoStock.RecordSource = "SELECT * FROM cuer… |
| Lista_Pedidos_OPT.frm | 2938 | SELECT | CargaMovStock.CuerpoStock.RecordSource = "SELECT * FROM cuer… |
| Lista_Pedidos_OPT.frm | 3137 | SELECT | CargaMovStock.CuerpoStock.RecordSource = "SELECT * FROM cuer… |
| Lista_Pedidos_OPT.frm | 3172 | SELECT | CargaMovStock.CuerpoStock.RecordSource = "SELECT * FROM cuer… |
| Lista_Pedidos_OPT.frm | 3400 | SELECT | CargaMovStock.CuerpoStock.RecordSource = "SELECT * FROM cuer… |
| ConsultaComprobante.frm | 13953 | SELECT | conn.Execute "delete from cuerpostock_mstock where Codusuari… |
| ConsultaComprobante.frm | 13953 | DELETE | conn.Execute "delete from cuerpostock_mstock where Codusuari… |
| ConsultaComprobante.frm | 13964 | SELECT | Data_Renglon.RecordSource = "SELECT * FROM cuerpostock_mstoc… |
| Lista_Comp_Gral.frm | 3976 | SELECT | rs_valid_ingreso_comp.Open "SELECT * FROM cuerpostock_mstock… |
| Lista_Comp_Gral.frm | 3992 | SELECT | CargaMovStock.CuerpoStock.RecordSource = "SELECT * FROM cuer… |
| CargaMovStock.frm | 4230 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock_mstock… |
| CargaMovStock.frm | 4674 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock_mstock… |
| CargaMovStock.frm | 4914 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock_mstock… |
| CargaMovStock.frm | 5187 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock_mstock… |
| CargaMovStock.frm | 5658 | SELECT | conn.Execute "DELETE FROM cuerpostock_mstock WHERE Orden = "… |
| CargaMovStock.frm | 5658 | DELETE | conn.Execute "DELETE FROM cuerpostock_mstock WHERE Orden = "… |
| CargaMovStock.frm | 5693 | SELECT | conn.Execute "DELETE FROM cuerpostock_mstock WHERE Orden = "… |
| CargaMovStock.frm | 5693 | DELETE | conn.Execute "DELETE FROM cuerpostock_mstock WHERE Orden = "… |
| CargaMovStock.frm | 6684 | SELECT | conn.Execute "delete from cuerpostock_mstock where Codusuari… |
| CargaMovStock.frm | 6684 | DELETE | conn.Execute "delete from cuerpostock_mstock where Codusuari… |
| CargaMovStock.frm | 6704 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock_mstock… |
| CargaMovStock.frm | 8399 | SELECT | "From cuerpostock_mstock " & _ |
| CargaMovStock.frm | 8773 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock_mstock… |
| CargaMovStock.frm | 8972 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock_mstock… |
| CargaMovStock.frm | 9007 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock_mstock… |
| CargaMovStock.frm | 9235 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock_mstock… |
| Visualiza_CargaMovStock_Copia.frm | 2587 | SELECT | 'CuerpoStock.RecordSource = "SELECT * FROM cuerpostock_mstoc… |
| Visualiza_CargaMovStock_Copia.frm | 3247 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock_mstock… |
| Visualiza_CargaMovStock_Copia.frm | 3527 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock_mstock… |
| Visualiza_CargaMovStock_Copia.frm | 3610 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock_mstock… |
| Visualiza_CargaMovStock_Copia.frm | 3663 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock_mstock… |
| Visualiza_CargaMovStock_Copia.frm | 3926 | SELECT | conn.Execute "DELETE FROM cuerpostock_mstock WHERE Orden = "… |
| Visualiza_CargaMovStock_Copia.frm | 3926 | DELETE | conn.Execute "DELETE FROM cuerpostock_mstock WHERE Orden = "… |
| Visualiza_CargaMovStock_Copia.frm | 3942 | SELECT | conn.Execute "DELETE FROM cuerpostock_mstock WHERE Orden = "… |
| Visualiza_CargaMovStock_Copia.frm | 3942 | DELETE | conn.Execute "DELETE FROM cuerpostock_mstock WHERE Orden = "… |
| Visualiza_CargaMovStock_Copia.frm | 4422 | SELECT | conn.Execute "delete from cuerpostock_mstock where Codusuari… |
| Visualiza_CargaMovStock_Copia.frm | 4422 | DELETE | conn.Execute "delete from cuerpostock_mstock where Codusuari… |
| Visualiza_CargaMovStock_Copia.frm | 4443 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock_mstock… |
| En_Carga_Vale.frm | 4207 | SELECT | rs_mov_stock_cuerpostock.Open "SELECT * FROM cuerpostock_mst… |
| En_Carga_Vale.frm | 4590 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock_mstock… |
| En_Carga_Vale.frm | 5383 | SELECT | conn.Execute "DELETE FROM cuerpostock_mstock WHERE cuerposto… |
| En_Carga_Vale.frm | 5383 | DELETE | conn.Execute "DELETE FROM cuerpostock_mstock WHERE cuerposto… |
| En_Carga_Vale.frm | 5686 | SELECT | conn.Execute "DELETE FROM cuerpostock_mstock WHERE cuerposto… |
| En_Carga_Vale.frm | 5686 | DELETE | conn.Execute "DELETE FROM cuerpostock_mstock WHERE cuerposto… |
| Principal.frm | 6076 | SELECT | conn.Execute "delete from cuerpostock_mstock where Codusuari… |
| Principal.frm | 6076 | DELETE | conn.Execute "delete from cuerpostock_mstock where Codusuari… |
| Principal.frm | 6142 | SELECT | conn.Execute "delete from cuerpostock_mstock where Codusuari… |
| Principal.frm | 6142 | DELETE | conn.Execute "delete from cuerpostock_mstock where Codusuari… |
| Visualiza.bas | 7048 | SELECT | conn.Execute "DELETE FROM cuerpostock_mstock WHERE Codusuari… |
| Visualiza.bas | 7048 | DELETE | conn.Execute "DELETE FROM cuerpostock_mstock WHERE Codusuari… |
| Visualiza.bas | 7121 | SELECT | Visualiza_CargaMovStock.CuerpoStock.RecordSource = "select *… |
| Visualiza.bas | 7249 | SELECT | Visualiza_CargaMovStock.CuerpoStock.RecordSource = "SELECT c… |
| Funciones.bas | 10895 | SELECT | rs_consulta.Open "SELECT * FROM cuerpostock_mstock " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)