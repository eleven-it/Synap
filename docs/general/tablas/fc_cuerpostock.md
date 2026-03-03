# Tabla `fc_cuerpostock`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| Orden | DOUBLE | No | ✓ |  |  |
| id_Cliente | DOUBLE | Sí |  |  |  |
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
| Facturacion_Ciclica.frm | 2232 | SELECT | rs_existe.Open "SELECT * FROM fc_cuerpostock " & _ |
| Facturacion_Ciclica.frm | 2382 | SELECT | "FROM fc_cuerpostock " & _ |
| Facturacion_Ciclica.frm | 2586 | SELECT | conn.Execute "DELETE FROM fc_cuerpostock WHERE codUsuario = … |
| Facturacion_Ciclica.frm | 2586 | DELETE | conn.Execute "DELETE FROM fc_cuerpostock WHERE codUsuario = … |
| Facturacion_Ciclica.frm | 3840 | SELECT | rs_cant.Open "SELECT * FROM fc_cuerpostock " & _ |
| Facturacion_Ciclica.frm | 3867 | SELECT | "From fc_cuerpostock " & _ |
| Facturacion_Ciclica.frm | 4270 | SELECT | conn.Execute "DELETE From fc_cuerpostock where CodUsuario = … |
| Facturacion_Ciclica.frm | 4270 | DELETE | conn.Execute "DELETE From fc_cuerpostock where CodUsuario = … |
| Facturacion_Ciclica.frm | 4520 | SELECT | conn.Execute "DELETE FROM fc_cuerpostock WHERE orden = " & D… |
| Facturacion_Ciclica.frm | 4520 | DELETE | conn.Execute "DELETE FROM fc_cuerpostock WHERE orden = " & D… |
| Facturacion_Ciclica.frm | 4547 | SELECT | "FROM fc_cuerpostock " & _ |
| Facturacion_Ciclica_Renglon.frm | 1810 | SELECT | rs.Open "SELECT * FROM fc_cuerpostock " & _ |
| Facturacion_Ciclica_Renglon.frm | 1829 | SELECT | rs.Open "SELECT * FROM fc_cuerpostock " & _ |
| Facturacion_Ciclica_Renglon.frm | 1861 | SELECT | Facturacion_Ciclica.Data_Renglon.RecordSource = "SELECT * FR… |
| Facturacion_Ciclica_Renglon.frm | 1863 | SELECT | Facturacion_Ciclica.Data_Renglon.RecordSource = "SELECT * FR… |
| Facturacion_Ciclica_Renglon.frm | 2566 | SELECT | CuerpoStock.RecordSource = "select * from fc_cuerpostock whe… |
| Facturacion_Ciclica_Renglon.frm | 2968 | SELECT | CuerpoStock.RecordSource = "select * from fc_cuerpostock whe… |
| Principal.frm | 6103 | SELECT | conn.Execute "delete from fc_cuerpostock where CodUsuario = … |
| Principal.frm | 6103 | DELETE | conn.Execute "delete from fc_cuerpostock where CodUsuario = … |
| Principal.frm | 6169 | SELECT | conn.Execute "delete from fc_cuerpostock where CodUsuario = … |
| Principal.frm | 6169 | DELETE | conn.Execute "delete from fc_cuerpostock where CodUsuario = … |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)