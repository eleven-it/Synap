# Tabla `cuerpostock`

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
| id_sp_desc | BIGINT | Sí |  |  |  |
| nrocodbarra | VARCHAR | Sí |  |  |  |
| cantidad_bulto_cerrado | DOUBLE | Sí |  |  |  |
| cantidad_bulto_pallet | DOUBLE | Sí |  |  |  |
| tipo_unidad | VARCHAR | Sí |  |  |  |
| cantidad_unidad_display | DOUBLE | Sí |  |  |  |
| cantidad_bulto | DOUBLE | Sí |  |  |  |
| cantidad_dividir | DOUBLE | Sí |  |  |  |

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
| Cliente.frm | 2274 | SELECT | TPV.data_renglon_tpv.RecordSource = "select cuerpostock.*, I… |
| Cliente.frm | 2383 | SELECT | rs_cuerpostock.Open "SELECT * FROM cuerpostock WHERE " & _ |
| PNotaCred.frm | 4174 | SELECT | CuerpoStock.RecordSource = "select cuerpostock.*, IVA.Alicuo… |
| Visualiza_ReciboCobro.frm | 10955 | SELECT | conn.Execute "delete from cuerpostock where Codusuario = " &… |
| Visualiza_ReciboCobro.frm | 10955 | DELETE | conn.Execute "delete from cuerpostock where Codusuario = " &… |
| Visualiza_ReciboCobro.frm | 11003 | SELECT | Visualiza_FA.CuerpoStock.RecordSource = "select * from cuerp… |
| Visualiza_ReciboCobro.frm | 11125 | SELECT | Visualiza_FA.CuerpoStock.RecordSource = "select * from cuerp… |
| Visualiza_ReciboCobro.frm | 11209 | SELECT | '        Visualiza_FA.CuerpoStock.RecordSource = "SELECT cue… |
| Visualiza_ReciboCobro.frm | 11327 | SELECT | conn.Execute "delete from cuerpostock where Codusuario = " &… |
| Visualiza_ReciboCobro.frm | 11327 | DELETE | conn.Execute "delete from cuerpostock where Codusuario = " &… |
| Visualiza_ReciboCobro.frm | 11374 | SELECT | Visualiza_FB.CuerpoStock.RecordSource = "select * from Cuerp… |
| Visualiza_ReciboCobro.frm | 11469 | SELECT | Visualiza_FB.CuerpoStock.RecordSource = "select * from Cuerp… |
| Visualiza_ReciboCobro.frm | 11580 | SELECT | '        Visualiza_FB.CuerpoStock.RecordSource = "SELECT cue… |
| Visualiza_ReciboCobro.frm | 11704 | SELECT | '        conn.Execute "delete from cuerpostock where Codusua… |
| Visualiza_ReciboCobro.frm | 11704 | DELETE | '        conn.Execute "delete from cuerpostock where Codusua… |
| Visualiza_ReciboCobro.frm | 11730 | SELECT | '        NotaCred.CuerpoStock.RecordSource = "select * from … |
| Visualiza_ReciboCobro.frm | 11790 | SELECT | '        NotaCred.CuerpoStock.RecordSource = "SELECT cuerpos… |
| Visualiza_ReciboCobro.frm | 12305 | SELECT | conn.Execute "delete from cuerpostock where Codusuario = " &… |
| Visualiza_ReciboCobro.frm | 12305 | DELETE | conn.Execute "delete from cuerpostock where Codusuario = " &… |
| Visualiza_ReciboCobro.frm | 12395 | SELECT | Visualiza_TPV.data_renglon_tpv.RecordSource = "select * from… |
| Visualiza_ReciboCobro.frm | 12490 | SELECT | Visualiza_TPV.data_renglon_tpv.RecordSource = "SELECT cuerpo… |
| Visualiza_NotaCred.frm | 3338 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock WHERE … |
| Visualiza_NotaCred.frm | 3447 | SELECT | CuerpoStock.RecordSource = "select * from cuerpostock where … |
| Visualiza_NotaCred.frm | 3779 | SELECT | conn.Execute "DELETE FROM cuerpostock WHERE Orden = " & id_c… |
| Visualiza_NotaCred.frm | 3779 | DELETE | conn.Execute "DELETE FROM cuerpostock WHERE Orden = " & id_c… |
| Visualiza_NotaCred.frm | 4298 | SELECT | CuerpoStock.RecordSource = "select sum(impuesto_interno_subt… |
| Visualiza_NotaCred.frm | 4310 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioVentaxRD) as PN… |
| Visualiza_NotaCred.frm | 4327 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioVentaxRD) as PN… |
| Visualiza_NotaCred.frm | 4368 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioVentaxRD) as PN… |
| Visualiza_NotaCred.frm | 4396 | SELECT | CuerpoStock.RecordSource = "select cuerpostock.*, IVA.Alicuo… |
| Visualiza_NotaCred.frm | 4677 | SELECT | conn.Execute "delete from cuerpostock where Codusuario = " &… |
| Visualiza_NotaCred.frm | 4677 | DELETE | conn.Execute "delete from cuerpostock where Codusuario = " &… |
| Visualiza_NotaCred.frm | 6081 | SELECT | "FROM cuerpostock " & _ |
| Visualiza_CargaMovStock.frm | 3413 | SELECT | 'CuerpoStock.RecordSource = "SELECT DISTINCT CodigoMovimient… |
| NotaCredCon.frm | 3186 | INSERT | conn.Execute "INSERT INTO Cuerpostock(Cantidad,Codusuario,Co… |
| NotaCredCon.frm | 3309 | SELECT | '            rs_cuerpostock.Open "SELECT * FROM cuerpostock … |
| NotaCredCon.frm | 6416 | SELECT | conn.Execute "delete from cuerpostock where Codusuario = " &… |
| NotaCredCon.frm | 6416 | DELETE | conn.Execute "delete from cuerpostock where Codusuario = " &… |
| FacturaB_COPIA.frm | 3391 | SELECT | rs_tipoiva.Open "SELECT * FROM cuerpostock " & _ |
| FacturaB_COPIA.frm | 5062 | SELECT | rs_valid_pedido.Open "SELECT CodigoMovimiento,visualiza FROM… |
| FacturaB_COPIA.frm | 5068 | SELECT | rs_cuerpostock.Open "SELECT DISTINCT CodigoMovimiento,NroPed… |
| FacturaB_COPIA.frm | 5157 | SELECT | rs_cuerpostock.Open "SELECT DISTINCT NroRemito, CodigoMovimi… |
| FacturaB_COPIA.frm | 5295 | SELECT | "FROM cuerpostock WHERE CodUsuario = " & Principal.idUsuario… |
| FacturaB_COPIA.frm | 5373 | SELECT | "FROM cuerpostock WHERE CodUsuario = " & Principal.idUsuario… |
| FacturaB_COPIA.frm | 7053 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock WHERE … |
| FacturaB_COPIA.frm | 7239 | SELECT | CuerpoStock.RecordSource = "select * from cuerpostock where … |
| FacturaB_COPIA.frm | 7990 | SELECT | conn.Execute "delete from cuerpostock where Codusuario = " &… |
| FacturaB_COPIA.frm | 7990 | DELETE | conn.Execute "delete from cuerpostock where Codusuario = " &… |
| FacturaB_COPIA.frm | 8162 | SELECT | rs_promo.Open "SELECT cuerpostock.promocion,cuerpostock.CodU… |
| FacturaB_COPIA.frm | 8344 | SELECT | conn.Execute "DELETE FROM cuerpostock WHERE IdArt = " & Cuer… |
| FacturaB_COPIA.frm | 8344 | DELETE | conn.Execute "DELETE FROM cuerpostock WHERE IdArt = " & Cuer… |
| FacturaB_COPIA.frm | 8351 | SELECT | conn.Execute "DELETE FROM cuerpostock WHERE Orden = " & id_c… |
| FacturaB_COPIA.frm | 8351 | DELETE | conn.Execute "DELETE FROM cuerpostock WHERE Orden = " & id_c… |
| FacturaB_COPIA.frm | 9200 | SELECT | rs_sumPNeto.Open "SELECT SUM(PrecioNetoxR) as sum FROM cuerp… |
| FacturaB_COPIA.frm | 9665 | SELECT | CuerpoStock.RecordSource = "select sum(impuesto_interno_subt… |
| FacturaB_COPIA.frm | 9677 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioVentaxRD) as PN… |
| FacturaB_COPIA.frm | 9695 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioVentaxRD) as PN… |
| FacturaB_COPIA.frm | 9741 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioVentaxRD) as PN… |
| FacturaB_COPIA.frm | 9882 | SELECT | CuerpoStock.RecordSource = "select cuerpostock.*, IVA.Alicuo… |
| FacturaB_COPIA.frm | 13230 | SELECT | CuerpoStock.RecordSource = "select * from cuerpostock where … |
| FacturaB_COPIA.frm | 15886 | SELECT | rs_tipoArt.Open "SELECT COUNT(*) as Cant FROM cuerpostock WH… |
| FacturaB_COPIA.frm | 15901 | SELECT | '        rs_suma.Open "SELECT SUM(PrecioCostoxR) As Costo FR… |
| FacturaB_COPIA.frm | 15904 | SELECT | rs_suma.Open "SELECT SUM(PrecioCostoxR) As Costo FROM Cuerpo… |
| FacturaB_COPIA.frm | 16612 | SELECT | "From cuerpostock " & _ |
| NotaCredDesc.frm | 2725 | SELECT | rs_cuerpostock.Open "SELECT * FROM cuerpostock WHERE visuali… |
| NotaCredDesc.frm | 7548 | SELECT | conn.Execute "delete from cuerpostock where Codusuario = " &… |
| NotaCredDesc.frm | 7548 | DELETE | conn.Execute "delete from cuerpostock where Codusuario = " &… |
| Serie_salida.frm | 746 | UPDATE | '    conn.Execute "UPDATE cuerpostock " & _ |
| Serie_salida.frm | 763 | UPDATE | conn.Execute "UPDATE cuerpostock " & _ |
| Serie_salida.frm | 782 | UPDATE | 'UPDATE cuerpostock |
| Serie_salida.frm | 786 | UPDATE | conn.Execute "UPDATE cuerpostock " & _ |
| NotaCred_COPIA.frm | 4217 | SELECT | "FROM cuerpostock WHERE CodUsuario = " & Principal.idUsuario… |
| NotaCred_COPIA.frm | 4295 | SELECT | "FROM cuerpostock WHERE visualiza = 'No' AND CodUsuario = " … |
| NotaCred_COPIA.frm | 6162 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostock WHERE … |
| NotaCred_COPIA.frm | 6292 | SELECT | CuerpoStock.RecordSource = "select * from cuerpostock where … |
| NotaCred_COPIA.frm | 6691 | SELECT | conn.Execute "DELETE FROM cuerpostock WHERE Orden = " & id_c… |
| NotaCred_COPIA.frm | 6691 | DELETE | conn.Execute "DELETE FROM cuerpostock WHERE Orden = " & id_c… |
| NotaCred_COPIA.frm | 7263 | SELECT | CuerpoStock.RecordSource = "select sum(impuesto_interno_subt… |
| NotaCred_COPIA.frm | 7275 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioVentaxRD) as PN… |
| NotaCred_COPIA.frm | 7294 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioVentaxRD) as PN… |
| … | … | … | *(751 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)