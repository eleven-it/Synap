# Tabla `movimiento_stock`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| ID_movimiento_stock | INT | No | ✓ |  |  |
| motivo_movimiento | VARCHAR | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
| deposito_origen | INT | Sí |  |  |  |
| deposito_destino | INT | Sí |  |  |  |
| detalle | MEDIUMTEXT | Sí |  |  |  |
| codigo_movimiento | DECIMAL | Sí |  |  |  |
| nro_comprobante | VARCHAR | Sí |  |  |  |
| nro_comprobante_busq | INT | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| id_sucursal | INT | Sí |  |  |  |
| id_pv | INT | Sí |  |  |  |
| tipo_comprobante | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_ref_movstock | INT | Sí |  |  |  |
| id_proyecto | INT | Sí |  |  |  |
| fecha_control | TIMESTAMP | No |  |  |  |
| cant_desarme | DOUBLE | Sí |  |  |  |
| CotiDolar | DECIMAL | Sí |  |  |  |
| transmitido | VARCHAR | Sí |  |  |  |
| id_cliente | BIGINT | Sí |  |  |  |
| estado | VARCHAR | Sí |  |  |  |
| id_vendedor | BIGINT | Sí |  |  |  |
| tipo_mov | VARCHAR | Sí |  |  |  OPT = Pedido producción (motivo 10); OPP = Parte producción (motivo 11). CargaMovStock.frm, Lista_Pedidos_OPT.frm. Synap lo escribe en alta. |

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
| Visualiza_CargaMovStock.frm | 3373 | SELECT | rs_movimiento_stock.Open "select * from movimiento_stock whe… |
| Visualiza_CargaMovStock.frm | 5873 | SELECT | rs_cuentaproveedor.Open "SELECT * FROM movimiento_stock WHER… |
| CargaArticulo_Original.frm | 12827 | SELECT | '    rs_movimiento_stock.Open "select * from movimiento_stoc… |
| POrden_CompraCopia.frm | 5652 | SELECT | .Source = "SELECT * FROM movimiento_stock WHERE movimiento_s… |
| CargaArticulo2.frm | 12733 | SELECT | '    rs_movimiento_stock.Open "select * from movimiento_stoc… |
| ConsultaComprobante.frm | 2462 | SELECT | DataConsulta.RecordSource = "select movimiento_stock.*,usuar… |
| ConsultaComprobante.frm | 2470 | SELECT | DataConsulta.RecordSource = "select movimiento_stock.*,usuar… |
| ConsultaComprobante.frm | 2534 | SELECT | DataConsulta.RecordSource = "select movimiento_stock.*,usuar… |
| ConsultaComprobante.frm | 2545 | SELECT | DataConsulta.RecordSource = "select movimiento_stock.*,usuar… |
| ConsultaComprobante.frm | 5467 | SELECT | rs_movimiento_stock.Open "SELECT * FROM movimiento_stock WHE… |
| ConsultaComprobante.frm | 14133 | SELECT | rs_movimiento_stock.Open "select ID_movimiento_stock,fecha_c… |
| ConsultaComprobante.frm | 21303 | SELECT | rs_movimiento_stock.Open "SELECT * FROM movimiento_stock WHE… |
| CargaArticulo.frm | 14846 | SELECT | '    rs_movimiento_stock.Open "select * from movimiento_stoc… |
| Pedido_Interno.frm | 1605 | SELECT | rs_movimiento_stock.Open "select * from movimiento_stock whe… |
| Pedido_Interno.frm | 1747 | SELECT | rs_movimiento_stock.Open "select ID_movimiento_stock,fecha_c… |
| CargaMovStock.frm | 4165 | SELECT | rs_movimiento_stock.Open "select * from movimiento_stock whe… |
| Visualiza_CargaMovStock_Copia.frm | 3208 | SELECT | rs_movimiento_stock.Open "select * from movimiento_stock whe… |
| Visualiza_CargaMovStock_Copia.frm | 5607 | SELECT | rs_cuentaproveedor.Open "SELECT * FROM movimiento_stock WHER… |
| En_Carga_Vale.frm | 4706 | SELECT | rs_movimiento_stock.Open "select * from movimiento_stock whe… |
| POrden_Compra.frm | 6543 | SELECT | .Source = "SELECT * FROM movimiento_stock WHERE movimiento_s… |
| CargaArticulo2.frm | 12733 | SELECT | '    rs_movimiento_stock.Open "select * from movimiento_stoc… |
| Visualiza.bas | 7029 | SELECT | "FROM movimiento_stock " & _ |
| Visualiza.bas | 7061 | SELECT | rs_mstock.Open "SELECT * FROM movimiento_stock WHERE codigo_… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)