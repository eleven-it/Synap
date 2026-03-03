# Tabla `cuerpostockpe`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| IDArt | INT | Sí |  |  |  |
| CodigoArticulo | VARCHAR | Sí |  |  |  |
| Descripcion | VARCHAR | Sí |  |  |  |
| Cantidad | DECIMAL | Sí |  |  |  |
| CantidadOr | DECIMAL | Sí |  |  |  |
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
| CodUsuario | INT | No |  |  |  |
| CodDeposito | INT | No |  |  |  |
| Orden | DOUBLE | No | ✓ |  |  |
| Detalle | MEDIUMTEXT | Sí |  |  |  |
| NroPresupuesto | VARCHAR | Sí |  |  |  |
| NroPedido | VARCHAR | Sí |  |  |  |
| NroRemito | VARCHAR | Sí |  |  |  |
| CodViajante | INT | Sí |  |  |  |
| CodLaboratorio | INT | Sí |  |  |  |
| lote | VARCHAR | Sí |  |  |  |
| id_lote | INT | Sí |  |  |  |
| cod_lote | VARCHAR | Sí |  |  |  |
| vto_lote | DATE | Sí |  |  |  |
| tipo_art | VARCHAR | Sí |  |  |  |
| imp_alicuota_iva | DECIMAL | Sí |  |  |  |
| imp_alicuota_iibb | DECIMAL | Sí |  |  |  |
| id_manual | VARCHAR | Sí |  |  |  |
| lista_precio | INT | Sí |  |  |  |
| codmov_presupuesto | DOUBLE | Sí |  |  |  |
| codmov_pedido | DOUBLE | Sí |  |  |  |
| promocion | VARCHAR | Sí |  |  |  |
| promocion_por | DECIMAL | Sí |  |  |  |
| promocion_cant | DECIMAL | Sí |  |  |  |
| promocion_tipo | VARCHAR | Sí |  |  |  |
| impuesto_interno | DECIMAL | Sí |  |  |  |
| impuesto_interno_subtotal | DECIMAL | Sí |  |  |  |
| id_stock | DOUBLE | Sí |  |  |  |
| Id_proyecto | DOUBLE | Sí |  |  |  |
| NroFactura | VARCHAR | Sí |  |  |  |
| codmov_factura | DOUBLE | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
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
| Seleccionado | TINYINT | Sí |  |  |  |
| id_serie_entrada | DOUBLE | Sí |  |  |  |
| desc_serie | MEDIUMTEXT | Sí |  |  |  |
| serie | VARCHAR | Sí |  |  |  |
| modifica_nuevo | VARCHAR | Sí |  |  |  |
| unidad_art_peso | DOUBLE | Sí |  |  |  |
| nro_despacho | VARCHAR | Sí |  |  |  |
| id_cotizacion | INT | Sí |  |  |  |
| coti_dolar | DOUBLE | Sí |  |  |  |
| id_marca | BIGINT | Sí |  |  |  |
| marca | VARCHAR | Sí |  |  |  |
| tipo_unidad | VARCHAR | Sí |  |  |  |
| cantidad_unidad_display | DOUBLE | Sí |  |  |  |
| cantidad_bulto | DOUBLE | Sí |  |  |  |
| cantidad_dividir | DOUBLE | Sí |  |  |  |
| ubicacion | VARCHAR | Sí |  |  |  |
| cantidad_pendiente_faltante | DOUBLE | Sí |  |  |  |

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
| Serie_salida.frm | 806 | UPDATE | '        conn.Execute "UPDATE cuerpostockpe " & _ |
| Serie_salida.frm | 818 | UPDATE | conn.Execute "UPDATE cuerpostockpe " & _ |
| Modifica_LP_Global.frm | 593 | SELECT | rs_cuerpostock.Open "SELECT * FROM cuerpostockpe WHERE " & _ |
| Modifica_LP_Global.frm | 758 | SELECT | rs_cuerpostock.Open "SELECT * FROM cuerpostockpe WHERE " & _ |
| Modifica_LP_Global.frm | 923 | SELECT | rs_cuerpostock.Open "SELECT * FROM cuerpostockpe WHERE " & _ |
| Modifica_LP_Global.frm | 1089 | SELECT | rs_cuerpostock.Open "SELECT * FROM cuerpostockpe WHERE " & _ |
| Modifica_LP_Global.frm | 1255 | SELECT | rs_cuerpostock.Open "SELECT * FROM cuerpostockpe WHERE " & _ |
| Importador_Excel.frm | 624 | SELECT | Pedido.CuerpoStock.RecordSource = "SELECT * FROM cuerpostock… |
| Visualiza_Pedido.frm | 3971 | SELECT | Visualiza_Pedido.CuerpoStock.RecordSource = "SELECT * FROM c… |
| Visualiza_Pedido.frm | 3978 | SELECT | conn.Execute "delete from cuerpostockpe where Codusuario = "… |
| Visualiza_Pedido.frm | 3978 | DELETE | conn.Execute "delete from cuerpostockpe where Codusuario = "… |
| Visualiza_Pedido.frm | 4312 | SELECT | '        CuerpoStock.RecordSource = "SELECT * FROM cuerposto… |
| Visualiza_Pedido.frm | 4447 | SELECT | '        CuerpoStock.RecordSource = "SELECT * FROM cuerposto… |
| Visualiza_Pedido.frm | 4817 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostockpe WHER… |
| Visualiza_Pedido.frm | 5053 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostockpe WHER… |
| Visualiza_Pedido.frm | 6218 | SELECT | conn.Execute "DELETE FROM cuerpostockpe WHERE Orden = " & id… |
| Visualiza_Pedido.frm | 6218 | DELETE | conn.Execute "DELETE FROM cuerpostockpe WHERE Orden = " & id… |
| Visualiza_Pedido.frm | 6566 | SELECT | conn.Execute "delete from cuerpostockpe where Codusuario = "… |
| Visualiza_Pedido.frm | 6566 | DELETE | conn.Execute "delete from cuerpostockpe where Codusuario = "… |
| Visualiza_Pedido.frm | 7119 | SELECT | rs_sumPNeto.Open "SELECT SUM(PrecioVentaxRD) as sum FROM cue… |
| Visualiza_Pedido.frm | 7697 | SELECT | 'CuerpoStock.RecordSource = "select sum(impuesto_interno_sub… |
| Visualiza_Pedido.frm | 7714 | SELECT | 'CuerpoStock.RecordSource = "select sum(PrecioVentaxRD) as P… |
| Visualiza_Pedido.frm | 7731 | SELECT | 'CuerpoStock.RecordSource = "select sum(PrecioVentaxRD) as P… |
| Visualiza_Pedido.frm | 7772 | SELECT | 'CuerpoStock.RecordSource = "select sum(PrecioVentaxRD) as P… |
| Visualiza_Pedido.frm | 7801 | SELECT | 'CuerpoStock.RecordSource = "select cuerpostockpe.*, IVA.Ali… |
| Visualiza_Pedido.frm | 7837 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioVentaxRD) as PN… |
| Visualiza_Pedido.frm | 7866 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioVentaxRD) as PN… |
| Visualiza_Pedido.frm | 7935 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioVentaxRD) as PN… |
| Visualiza_Pedido.frm | 7980 | SELECT | CuerpoStock.RecordSource = "select sum(impuesto_interno_subt… |
| Visualiza_Pedido.frm | 8179 | SELECT | " FROM cuerpostockpe " & _ |
| Visualiza_Pedido.frm | 8198 | SELECT | " FROM cuerpostockpe " & _ |
| Visualiza_Pedido.frm | 8271 | SELECT | CuerpoStock.RecordSource = "select CuerpoStockPe.*, IVA.Alic… |
| Visualiza_Pedido.frm | 8314 | SELECT | 'CuerpoStock.RecordSource = "select sum(impuesto_interno_sub… |
| Visualiza_Pedido.frm | 8330 | SELECT | 'CuerpoStock.RecordSource = "select sum(PrecioVentaxRD) as P… |
| Visualiza_Pedido.frm | 8349 | SELECT | 'CuerpoStock.RecordSource = "select sum(PrecioVentaxRD) as P… |
| Visualiza_Pedido.frm | 8396 | SELECT | 'CuerpoStock.RecordSource = "select sum(PrecioVentaxRD) as P… |
| Visualiza_Pedido.frm | 8530 | SELECT | 'CuerpoStock.RecordSource = "select cuerpostockpe.*, IVA.Ali… |
| Visualiza_Pedido.frm | 9958 | SELECT | rs_elimina_stock.Open "SELECT cuerpostockpe.id_stock FROM cu… |
| Visualiza_Pedido.frm | 9989 | SELECT | rs_elimina_stock.Open "SELECT cuerpostockpe.id_stock,cuerpos… |
| Visualiza_Pedido.frm | 10029 | SELECT | rs_elimina_stock.Open "SELECT cuerpostockpe.id_stock FROM cu… |
| Visualiza_Pedido.frm | 11050 | SELECT | conn.Execute "delete from cuerpostockpe where Codusuario = "… |
| Visualiza_Pedido.frm | 11050 | DELETE | conn.Execute "delete from cuerpostockpe where Codusuario = "… |
| Visualiza_Pedido.frm | 11142 | SELECT | rs_cuerpostock.Open "SELECT * FROM cuerpostockpe WHERE Codig… |
| Visualiza_Pedido.frm | 11471 | INSERT | '        conn.Execute "INSERT INTO cuerpostockpe " & _ |
| Visualiza_Pedido.frm | 11501 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostockpe WHER… |
| Visualiza_Pedido.frm | 13389 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostockpe WHER… |
| Visualiza_Pedido.frm | 14545 | UPDATE | ''            conn.Execute "UPDATE cuerpostockpe SET cuerpos… |
| Visualiza_Pedido.frm | 14555 | SELECT | '            rs_cuerpostock.Open "SELECT DISTINCT CodigoMovi… |
| Visualiza_Pedido.frm | 14657 | SELECT | '                rs_cuerpostock.Open "SELECT DISTINCT Codigo… |
| Visualiza_Pedido.frm | 14695 | UPDATE | '            conn.Execute "UPDATE cuerpostockpe SET cuerpost… |
| Visualiza_Pedido.frm | 14911 | SELECT | rs_cuerpostockpe.Open "SELECT * FROM cuerpostockpe WHERE cue… |
| Carga_DatosAdicionales.frm | 2135 | UPDATE | conn.Execute "UPDATE cuerpostockpe " & _ |
| Carga_DatosAdicionales.frm | 2243 | UPDATE | conn.Execute "UPDATE cuerpostockpe " & _ |
| Carga_DatosAdicionales.frm | 2351 | UPDATE | conn.Execute "UPDATE cuerpostockpe " & _ |
| trz_trazabilidad.frm | 4796 | SELECT | conn.Execute "delete from cuerpostockpe where Codusuario = "… |
| trz_trazabilidad.frm | 4796 | DELETE | conn.Execute "delete from cuerpostockpe where Codusuario = "… |
| trz_trazabilidad.frm | 4819 | SELECT | Visualiza_Remito.CuerpoStock.RecordSource = "select * from c… |
| trz_trazabilidad.frm | 4913 | SELECT | Visualiza_Remito.CuerpoStock.RecordSource = "SELECT cuerpost… |
| trz_trazabilidad.frm | 5291 | SELECT | conn.Execute "delete from cuerpostockpe where Codusuario = "… |
| trz_trazabilidad.frm | 5291 | DELETE | conn.Execute "delete from cuerpostockpe where Codusuario = "… |
| trz_trazabilidad.frm | 5321 | SELECT | Visualiza_Presupuesto.CuerpoStock.RecordSource = "select * f… |
| trz_trazabilidad.frm | 5428 | SELECT | Visualiza_Presupuesto.CuerpoStock.RecordSource = "SELECT cue… |
| trz_trazabilidad.frm | 5581 | SELECT | conn.Execute "delete from cuerpostockpe where Codusuario = "… |
| trz_trazabilidad.frm | 5581 | DELETE | conn.Execute "delete from cuerpostockpe where Codusuario = "… |
| trz_trazabilidad.frm | 5614 | SELECT | Visualiza_Pedido.CuerpoStock.RecordSource = "SELECT * FROM c… |
| trz_trazabilidad.frm | 5723 | SELECT | Visualiza_Pedido.CuerpoStock.RecordSource = "SELECT cuerpost… |
| Articulo.frm | 4080 | SELECT | rs_cuerpostock.Open "SELECT * FROM cuerpostockpe WHERE IDArt… |
| Articulo.frm | 4481 | SELECT | rs_cuerpostock.Open "SELECT * FROM cuerpostockpe WHERE IDArt… |
| Articulo.frm | 4855 | SELECT | rs_cuerpostock.Open "SELECT * FROM cuerpostockpe WHERE IDArt… |
| Articulo.frm | 5563 | SELECT | rs_cuerpostock.Open "SELECT * FROM cuerpostockpe WHERE IDArt… |
| Articulo.frm | 5883 | SELECT | rs_cuerpostock.Open "SELECT * FROM cuerpostockpe WHERE IDArt… |
| Articulo.frm | 10279 | SELECT | rs_cuerpostock.Open "SELECT * FROM cuerpostockpe WHERE Orden… |
| Articulo.frm | 12131 | SELECT | Pedido.CuerpoStock.RecordSource = "SELECT * FROM cuerpostock… |
| Articulo.frm | 15141 | SELECT | Presupuesto.CuerpoStock.RecordSource = "SELECT * FROM cuerpo… |
| Articulo.frm | 16136 | SELECT | Remito.CuerpoStock.RecordSource = "SELECT * FROM cuerpostock… |
| Stock_Control.frm | 2511 | SELECT | conn.Execute "delete from cuerpostockpe where Codusuario = "… |
| Stock_Control.frm | 2511 | DELETE | conn.Execute "delete from cuerpostockpe where Codusuario = "… |
| Stock_Control.frm | 2558 | SELECT | rs_validacion.Open "SELECT * FROM cuerpostockpe WHERE visual… |
| Stock_Control.frm | 2671 | SELECT | Remito.CuerpoStock.RecordSource = "SELECT * FROM cuerpostock… |
| Inventario.frm | 3633 | SELECT | '    CuerpoStock.RecordSource = "SELECT * FROM cuerpostockpe… |
| … | … | … | *(247 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)