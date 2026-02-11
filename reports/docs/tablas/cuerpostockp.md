# Tabla `cuerpostockp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| Orden | DOUBLE | No | ✓ |  |  |
| IDArt | INT | Sí |  |  |  |
| CodigoArticulo | VARCHAR | Sí |  |  |  |
| Descripcion | VARCHAR | Sí |  |  |  |
| Cantidad | DECIMAL | Sí |  |  |  |
| CantidadOr | DECIMAL | Sí |  |  |  |
| PrecioCostoxU | DECIMAL | Sí |  |  |  |
| PrecioVentaxU | DECIMAL | Sí |  |  |  |
| PrecioBrutoxU | DECIMAL | Sí |  |  |  |
| PrecioNetoxU | DECIMAL | Sí |  |  |  |
| PrecioIVAxU | DECIMAL | Sí |  |  |  |
| PrecioCostoxR | DECIMAL | Sí |  |  |  |
| PrecioVentaxR | DECIMAL | Sí |  |  |  |
| PrecioBrutoxR | DECIMAL | Sí |  |  |  |
| PrecioNetoxR | DECIMAL | Sí |  |  |  |
| PrecioIVAxR | DECIMAL | Sí |  |  |  |
| ImpDesc | DECIMAL | Sí |  |  |  |
| PorDesc | DECIMAL | Sí |  |  |  |
| Alicuota | INT | Sí |  |  |  |
| TipoIVA | VARCHAR | Sí |  |  |  |
| CodigoMovimiento | DECIMAL | Sí |  |  |  |
| nro_remito | VARCHAR | Sí |  |  |  |
| nro_presupuesto | VARCHAR | Sí |  |  |  |
| nro_oc | VARCHAR | Sí |  |  |  |
| CodUsuario | INT | No |  |  |  |
| CodDeposito | INT | No |  |  |  |
| CodLaboratorio | INT | Sí |  |  |  |
| id_lote | INT | Sí |  |  |  |
| vto_lote | DATE | Sí |  |  |  |
| cod_lote | VARCHAR | Sí |  |  |  |
| lote | VARCHAR | Sí |  |  |  |
| tipo_art | VARCHAR | Sí |  |  |  |
| id_manual | VARCHAR | Sí |  |  |  |
| imp_alicuota_iva | DECIMAL | Sí |  |  |  |
| actualiza_costo | INT | Sí |  |  |  |
| actualiza_venta | INT | Sí |  |  |  |
| actualiza_desc | VARCHAR | Sí |  |  |  |
| codmov_presupuesto | DECIMAL | Sí |  |  |  |
| codmov_oc | DECIMAL | Sí |  |  |  |
| codmov_remito | DECIMAL | Sí |  |  |  |
| detalle | MEDIUMTEXT | Sí |  |  |  |
| CodGasto | INT | Sí |  |  |  |
| impdesc_bonif | DECIMAL | Sí |  |  |  |
| pordesc_bonif | DECIMAL | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| id_stock | DECIMAL | Sí |  |  |  |
| NroFactura | VARCHAR | Sí |  |  |  |
| codmov_factura | DOUBLE | Sí |  |  |  |
| multiplicador_comp | DECIMAL | Sí |  |  |  |
| multiplicador_vta | DECIMAL | Sí |  |  |  |
| cantidad_uni | DECIMAL | Sí |  |  |  |
| id_unimed | DOUBLE | Sí |  |  |  |
| id_presentacion | DOUBLE | Sí |  |  |  |
| nombre_unimed | VARCHAR | Sí |  |  |  |
| nombre_presentacion | VARCHAR | Sí |  |  |  |
| Seleccionado | CHAR | Sí |  |  |  |
| id_serie_entrada | DOUBLE | Sí |  |  |  |
| desc_serie | VARCHAR | Sí |  |  |  |
| serie | VARCHAR | Sí |  |  |  |
| unidad_art_peso | DOUBLE | Sí |  |  |  |
| id_cotizacion | INT | Sí |  |  |  |
| coti_dolar | DOUBLE | Sí |  |  |  |
| id_marca | BIGINT | Sí |  |  |  |
| marca | VARCHAR | Sí |  |  |  |
| impuesto_interno_subtotal | DOUBLE | Sí |  |  |  |
| cantidad_bulto_pallet | DOUBLE | Sí |  |  |  |

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
| PNotaCred.frm | 3992 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostockp WHERE… |
| PNotaCred.frm | 4103 | SELECT | CuerpoStock.RecordSource = "select * from cuerpostockp where… |
| PNotaCred.frm | 4451 | SELECT | conn.Execute "DELETE FROM cuerpostockp WHERE Orden = " & id_… |
| PNotaCred.frm | 4451 | DELETE | conn.Execute "DELETE FROM cuerpostockp WHERE Orden = " & id_… |
| PNotaCred.frm | 4520 | SELECT | conn.Execute "delete from cuerpostockp where Codusuario = " … |
| PNotaCred.frm | 4520 | DELETE | conn.Execute "delete from cuerpostockp where Codusuario = " … |
| PNotaCred.frm | 5156 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioNetoxR) as PNet… |
| PNotaCred.frm | 5174 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioNetoxR) as PNet… |
| PNotaCred.frm | 5192 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioNetoxR) as PNet… |
| PNotaCred.frm | 5239 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioNetoxR) as PNet… |
| PNotaCred.frm | 5272 | SELECT | CuerpoStock.RecordSource = "select sum(impuesto_interno_subt… |
| PNotaCred.frm | 5318 | SELECT | CuerpoStock.RecordSource = "SELECT cuerpostockp.*, IVA.Alicu… |
| PNotaCred.frm | 5372 | SELECT | 'CuerpoStock.RecordSource = "select sum(PrecioNetoxR) as PNe… |
| PNotaCred.frm | 5388 | SELECT | 'CuerpoStock.RecordSource = "select sum(PrecioNetoxR) as PNe… |
| PNotaCred.frm | 5404 | SELECT | 'CuerpoStock.RecordSource = "select sum(PrecioNetoxR) as PNe… |
| PNotaCred.frm | 5434 | SELECT | 'CuerpoStock.RecordSource = "select sum(PrecioNetoxR) as PNe… |
| PNotaCred.frm | 5469 | SELECT | 'CuerpoStock.RecordSource = "select cuerpostockp.*, iva.Alic… |
| PNotaCred.frm | 5784 | SELECT | conn.Execute "delete from cuerpostockp where Codusuario = " … |
| PNotaCred.frm | 5784 | DELETE | conn.Execute "delete from cuerpostockp where Codusuario = " … |
| PNotaCred.frm | 7761 | SELECT | "From cuerpostockp " & _ |
| Serie_salida.frm | 845 | UPDATE | '    conn.Execute "UPDATE cuerpostockp " & _ |
| Serie_salida.frm | 857 | UPDATE | conn.Execute "UPDATE cuerpostockp " & _ |
| Importador_Excel.frm | 1549 | SELECT | POrden_Compra.CuerpoStock.RecordSource = "SELECT * FROM cuer… |
| OrdenPago.frm | 15194 | SELECT | conn.Execute "delete from cuerpostockp where Codusuario = " … |
| OrdenPago.frm | 15194 | DELETE | conn.Execute "delete from cuerpostockp where Codusuario = " … |
| OrdenPago.frm | 15225 | SELECT | Visualiza_PFactura.CuerpoStock.RecordSource = "SELECT * FROM… |
| OrdenPago.frm | 15398 | SELECT | '            Visualiza_PFactura.CuerpoStock.RecordSource = "… |
| OrdenPago.frm | 15406 | SELECT | '            Visualiza_PFactura.CuerpoStock.RecordSource = "… |
| OrdenPago.frm | 15561 | SELECT | conn.Execute "delete from cuerpostockp where Codusuario = " … |
| OrdenPago.frm | 15561 | DELETE | conn.Execute "delete from cuerpostockp where Codusuario = " … |
| trz_trazabilidad.frm | 5057 | SELECT | '        conn.Execute "delete from cuerpostockp where Codusu… |
| trz_trazabilidad.frm | 5057 | DELETE | '        conn.Execute "delete from cuerpostockp where Codusu… |
| trz_trazabilidad.frm | 5078 | SELECT | '        Visualiza_PRemito.CuerpoStock.RecordSource = "selec… |
| trz_trazabilidad.frm | 5135 | SELECT | '        Visualiza_PRemito.CuerpoStock.RecordSource = "SELEC… |
| Visualiza_POrden_Compra.frm | 3708 | SELECT | CuerpoStock.RecordSource = "SELECT DISTINCT CodigoMovimiento… |
| Visualiza_POrden_Compra.frm | 3984 | SELECT | '        CuerpoStock.RecordSource = "SELECT * FROM cuerposto… |
| Visualiza_POrden_Compra.frm | 4058 | SELECT | '        CuerpoStock.RecordSource = "SELECT * FROM cuerposto… |
| Visualiza_POrden_Compra.frm | 4193 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostockp WHERE… |
| Visualiza_POrden_Compra.frm | 4294 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostockp WHERE… |
| Visualiza_POrden_Compra.frm | 4896 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostockp WHERE… |
| Visualiza_POrden_Compra.frm | 5111 | SELECT | conn.Execute "DELETE FROM cuerpostockp WHERE Orden = " & id_… |
| Visualiza_POrden_Compra.frm | 5111 | DELETE | conn.Execute "DELETE FROM cuerpostockp WHERE Orden = " & id_… |
| Visualiza_POrden_Compra.frm | 5636 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioNetoxR) as PNet… |
| Visualiza_POrden_Compra.frm | 5653 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioNetoxR) as PNet… |
| Visualiza_POrden_Compra.frm | 5670 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioNetoxR) as PNet… |
| Visualiza_POrden_Compra.frm | 5716 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioNetoxR) as PNet… |
| Visualiza_POrden_Compra.frm | 5754 | SELECT | CuerpoStock.RecordSource = "SELECT cuerpostockp.*, IVA.Alicu… |
| Visualiza_POrden_Compra.frm | 5917 | SELECT | conn.Execute "delete from cuerpostockp where Codusuario = " … |
| Visualiza_POrden_Compra.frm | 5917 | DELETE | conn.Execute "delete from cuerpostockp where Codusuario = " … |
| Visualiza_POrden_Compra.frm | 6310 | SELECT | rs_elimina_stock.Open "SELECT cuerpostockp.id_stock FROM cue… |
| Visualiza_POrden_Compra.frm | 6814 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostockp WHERE… |
| POrden_CompraCopia.frm | 3271 | SELECT | CuerpoStock.RecordSource = "SELECT DISTINCT CodigoMovimiento… |
| POrden_CompraCopia.frm | 3643 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostockp WHERE… |
| POrden_CompraCopia.frm | 3747 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostockp WHERE… |
| POrden_CompraCopia.frm | 4240 | SELECT | rs_sumPNeto.Open "SELECT SUM(PrecioNetoxR) as sum FROM cuerp… |
| POrden_CompraCopia.frm | 4409 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostockp WHERE… |
| POrden_CompraCopia.frm | 4665 | SELECT | conn.Execute "DELETE FROM cuerpostockp WHERE Orden = " & id_… |
| POrden_CompraCopia.frm | 4665 | DELETE | conn.Execute "DELETE FROM cuerpostockp WHERE Orden = " & id_… |
| POrden_CompraCopia.frm | 5182 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioNetoxR) as PNet… |
| POrden_CompraCopia.frm | 5201 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioNetoxR) as PNet… |
| POrden_CompraCopia.frm | 5220 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioNetoxR) as PNet… |
| POrden_CompraCopia.frm | 5268 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioNetoxR) as PNet… |
| POrden_CompraCopia.frm | 5293 | SELECT | CuerpoStock.RecordSource = "select sum(impuesto_interno_subt… |
| POrden_CompraCopia.frm | 5341 | SELECT | CuerpoStock.RecordSource = "SELECT cuerpostockp.*, IVA.Alicu… |
| POrden_CompraCopia.frm | 5513 | SELECT | conn.Execute "delete from cuerpostockp where Codusuario = " … |
| POrden_CompraCopia.frm | 5513 | DELETE | conn.Execute "delete from cuerpostockp where Codusuario = " … |
| PRemito.frm | 4044 | SELECT | '            CuerpoStock.RecordSource = "SELECT distinct (nr… |
| PRemito.frm | 4082 | SELECT | rs_valid_remito.Open "SELECT CodigoMovimiento,visualiza FROM… |
| PRemito.frm | 4088 | SELECT | rs_cuerpostock.Open "SELECT DISTINCT CodigoMovimiento,Nro_oc… |
| PRemito.frm | 4147 | SELECT | rs_cuerpostock.Open "SELECT DISTINCT CodigoMovimiento,NroFac… |
| PRemito.frm | 4348 | SELECT | CuerpoStock.RecordSource = "SELECT * FROM cuerpostockp WHERE… |
| PRemito.frm | 4497 | SELECT | CuerpoStock.RecordSource = "select * from cuerpostockp where… |
| PRemito.frm | 4644 | SELECT | CuerpoStock.RecordSource = "select cuerpostockp.*, iva.Alicu… |
| PRemito.frm | 5255 | SELECT | conn.Execute "DELETE FROM cuerpostockp WHERE Orden = " & id_… |
| PRemito.frm | 5255 | DELETE | conn.Execute "DELETE FROM cuerpostockp WHERE Orden = " & id_… |
| PRemito.frm | 5853 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioNetoxR) as PNet… |
| PRemito.frm | 5871 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioNetoxR) as PNet… |
| PRemito.frm | 5889 | SELECT | CuerpoStock.RecordSource = "select sum(PrecioNetoxR) as PNet… |
| PRemito.frm | 5936 | SELECT | CuerpoStockTemp.RecordSource = "select sum(PrecioNetoxR) as … |
| PRemito.frm | 5973 | SELECT | CuerpoStock.RecordSource = "select sum(impuesto_interno_subt… |
| … | … | … | *(357 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)