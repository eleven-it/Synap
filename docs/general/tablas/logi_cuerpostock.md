# Tabla `logi_cuerpostock`

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
| Logi_Gestion2.frm | 5103 | SELECT | conn.Execute "DELETE FROM logi_cuerpostock WHERE codUsuario … |
| Logi_Gestion2.frm | 5103 | DELETE | conn.Execute "DELETE FROM logi_cuerpostock WHERE codUsuario … |
| Logi_Gestion2.frm | 5442 | SELECT | conn.Execute "DELETE logi_cuerpostock.* FROM logi_cuerpostoc… |
| Logi_Gestion2.frm | 6966 | SELECT | '                    dataLupa.RecordSource = "SELECT * FROM … |
| Logi_Gestion2.frm | 6998 | SELECT | '                    dataLupa.RecordSource = "SELECT * FROM … |
| Logi_Gestion2.frm | 10164 | SELECT | rs_cant.Open "SELECT * FROM logi_cuerpostock WHERE CodigoMov… |
| Logi_Gestion2.frm | 10189 | SELECT | "From logi_cuerpostock " & _ |
| Logi_Gestion2.frm | 10649 | SELECT | conn.Execute "DELETE logi_cuerpostock.* FROM logi_cuerpostoc… |
| Logi_Gestion.frm | 4153 | SELECT | conn.Execute "DELETE logi_cuerpostock.* FROM logi_cuerpostoc… |
| Logi_Gestion.frm | 6286 | SELECT | conn.Execute "DELETE From logi_cuerpostock WHERE CodUsuario … |
| Logi_Gestion.frm | 6286 | DELETE | conn.Execute "DELETE From logi_cuerpostock WHERE CodUsuario … |
| Logi_Gestion.frm | 6346 | SELECT | conn.Execute "DELETE FROM logi_cuerpostock WHERE codUsuario … |
| Logi_Gestion.frm | 6346 | DELETE | conn.Execute "DELETE FROM logi_cuerpostock WHERE codUsuario … |
| Logi_Gestion.frm | 6699 | SELECT | conn.Execute "DELETE logi_cuerpostock.* FROM logi_cuerpostoc… |
| Logi_Gestion.frm | 8466 | SELECT | "FROM logi_cuerpostock WHERE logi_cuerpostock.CodigoMovimien… |
| Logi_Gestion.frm | 8478 | SELECT | dataLupa.RecordSource = "SELECT * FROM logi_cuerpostock " & … |
| Logi_Gestion.frm | 8516 | SELECT | "FROM logi_cuerpostock WHERE logi_cuerpostock.CodigoMovimien… |
| Logi_Gestion.frm | 8528 | SELECT | dataLupa.RecordSource = "SELECT * FROM logi_cuerpostock " & … |
| Logi_Gestion.frm | 11828 | SELECT | rs_cant.Open "SELECT * FROM logi_cuerpostock WHERE CodigoMov… |
| Logi_Gestion.frm | 11853 | SELECT | "From logi_cuerpostock " & _ |
| Logi_Gestion.frm | 12480 | SELECT | conn.Execute "DELETE logi_cuerpostock.* FROM logi_cuerpostoc… |
| logi_renglon_ped.frm | 361 | SELECT | conn.Execute "DELETE FROM logi_cuerpostock WHERE orden = " &… |
| logi_renglon_ped.frm | 361 | DELETE | conn.Execute "DELETE FROM logi_cuerpostock WHERE orden = " &… |
| logi_renglon_ped.frm | 412 | SELECT | "FROM logi_cuerpostock WHERE logi_cuerpostock.CodigoMovimien… |
| Logi_Renglon.frm | 2202 | SELECT | CuerpoStock.RecordSource = "select * from logi_cuerpostock w… |
| Logi_Renglon.frm | 2585 | SELECT | CuerpoStock.RecordSource = "select * from logi_cuerpostock w… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)