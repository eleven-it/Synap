# Tabla `cuerpostock_ped_sin_stock`

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
| Visualiza_Pedido.frm | 9977 | SELECT | conn.Execute "DELETE FROM cuerpostock_ped_sin_stock WHERE co… |
| Visualiza_Pedido.frm | 9977 | DELETE | conn.Execute "DELETE FROM cuerpostock_ped_sin_stock WHERE co… |
| Visualiza_Pedido.frm | 11472 | SELECT | '                    " SELECT * FROM cuerpostock_ped_sin_sto… |
| Visualiza_Pedido.frm | 14735 | SELECT | rs_cuerpostock.Open "SELECT * FROM cuerpostock_ped_sin_stock… |
| Visualiza_Pedido.frm | 14907 | SELECT | rs_cuerpostock_ped_sin_stock.Open "SELECT * FROM cuerpostock… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)