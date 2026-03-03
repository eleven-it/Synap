# Tabla `stock_deposito`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_stock_deposito | DOUBLE | No | ✓ |  |  |
| id_articulo | DECIMAL | Sí |  |  |  |
| id_deposito | INT | No |  |  |  |
| saldo | DOUBLE | Sí |  |  |  |
| saldo_pedido_cliente | DOUBLE | Sí |  |  |  |
| saldo_pedido_proveedor | DOUBLE | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| articulo | stock_deposito | Sup_importacion_tablas.frm | 11031 | '                "SELECT articulo.IDArt,deposito.CodDeposito FROM articulo LEFT … |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| PNotaCred.frm | 3112 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| Visualiza_CargaMovStock.frm | 2963 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| Visualiza_CargaMovStock.frm | 3244 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| FacturaB_COPIA.frm | 4506 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| FacturaB_COPIA.frm | 17358 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito " & _ |
| FacturaB_COPIA.frm | 17667 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito " & _ |
| NotaCred_COPIA.frm | 3435 | SELECT | '                rs_saldo_stock.Open "SELECT * FROM stock_de… |
| NotaCred_COPIA.frm | 3449 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| NotaCred_COPIA.frm | 12483 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| NotaCred_COPIA.frm | 12752 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| TPV.frm | 6531 | SELECT | '                rs_saldo_stock.Open "SELECT * FROM stock_de… |
| TPV.frm | 6548 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| TPV.frm | 9497 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| TPV.frm | 35145 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito " & _ |
| TPV.frm | 35457 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito " & _ |
| TPV.frm | 35881 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| TPV.frm | 36154 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| TPV.frm | 39902 | SELECT | '        rs_saldo_stock.Open "SELECT * FROM stock_deposito W… |
| TPV.frm | 39905 | UPDATE | ''        sentencia_tabla_sd = "UPDATE stock_deposito " |
| Logi_Gestion2.frm | 9404 | JOIN | "LEFT JOIN stock_deposito ON (stock_deposito.id_articulo = s… |
| Visualiza_Pedido.frm | 3946 | JOIN | " LEFT JOIN stock_deposito ON (stock_deposito.id_articulo = … |
| Visualiza_Pedido.frm | 10059 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| Visualiza_Pedido.frm | 11078 | JOIN | '            " LEFT JOIN stock_deposito ON (stock_deposito.i… |
| Visualiza_Pedido.frm | 11107 | JOIN | '            " LEFT JOIN stock_deposito ON (stock_deposito.i… |
| Visualiza_Pedido.frm | 11125 | JOIN | '            " LEFT JOIN stock_deposito ON (stock_deposito.i… |
| Visualiza_Pedido.frm | 12800 | JOIN | '            " LEFT JOIN stock_deposito ON (stock_deposito.i… |
| Visualiza_Pedido.frm | 14375 | SELECT | '                        rs_saldo_stock.Open "SELECT * FROM … |
| Logi_Gestion.frm | 11060 | JOIN | "LEFT JOIN stock_deposito ON (stock_deposito.id_articulo = s… |
| AjustarSaldos.frm | 491 | JOIN | '    "INNER JOIN stock_deposito on (stock.saldo = stock_depo… |
| AjustarSaldos.frm | 536 | SELECT | rs_AjustarSaldos.Open "select * from stock_deposito where id… |
| AjustarSaldos.frm | 954 | SELECT | rs_AjustarSaldosMasivo.Open "select * from stock_deposito wh… |
| CargaArticulo_Original.frm | 9546 | SELECT | rs_stock_deposito.Open "SELECT * FROM stock_deposito WHERE i… |
| CargaArticulo_Original.frm | 9902 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| CargaArticulo_Original.frm | 12711 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| ABMArticulo_seleccion.frm | 3355 | SELECT | "FROM stock_deposito,deposito " & _ |
| ABMArticulo_seleccion.frm | 3385 | SELECT | "FROM stock_deposito,deposito " & _ |
| ABMArticulo_seleccion.frm | 3401 | SELECT | Data_Stock.RecordSource = "SELECT stock_deposito.id_deposito… |
| ABMArticulo_seleccion.frm | 3419 | SELECT | Data_Stock.RecordSource = "SELECT stock_deposito.id_deposito… |
| ABMArticulo_seleccion.frm | 3439 | SELECT | Data_Stock.RecordSource = "SELECT stock_deposito.id_deposito… |
| ABMArticulo_seleccion.frm | 3458 | SELECT | " FROM stock_deposito " & _ |
| ABMArticulo_seleccion.frm | 3482 | SELECT | " FROM stock_deposito " & _ |
| ABMArticulo_seleccion.frm | 3507 | SELECT | Data_Stock.RecordSource = "SELECT stock_deposito.id_deposito… |
| ABMArticulo_seleccion.frm | 4964 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| Articulo.frm | 6561 | SELECT | .Source = "select * from stock_deposito where id_articulo = … |
| Articulo.frm | 8508 | JOIN | " LEFT JOIN stock_deposito ON (stock_deposito.id_articulo = … |
| Visualiza_POrden_Compra.frm | 3627 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| Stock_Control.frm | 1910 | JOIN | '        " LEFT JOIN stock_deposito ON (stock_deposito.id_ar… |
| Stock_Control.frm | 2089 | JOIN | " LEFT JOIN stock_deposito ON (stock_deposito.id_articulo = … |
| POrden_CompraCopia.frm | 3152 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| PRemito.frm | 3634 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| PRemito.frm | 6959 | JOIN | '            " LEFT JOIN stock_deposito ON (stock_deposito.i… |
| Visualiza_PNotaCredDev.frm | 2751 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| Lista_Confeccion_OC_Gral.frm | 1096 | JOIN | " LEFT JOIN stock_deposito ON (stock_deposito.id_articulo = … |
| Lista_Pedidos_OPT.frm | 2031 | SELECT | Data_Stock.RecordSource = "SELECT * FROM stock_deposito WHER… |
| Lista_Pedidos_OPT.frm | 2427 | SELECT | "FROM stock_deposito,deposito " & _ |
| Lista_Pedidos_OPT.frm | 2443 | SELECT | "FROM stock_deposito,deposito " & _ |
| Lista_Pedidos_OPT.frm | 2482 | SELECT | Data_Stock.RecordSource = "SELECT stock_deposito.id_deposito… |
| Lista_Pedidos_OPT.frm | 2518 | SELECT | Data_Stock.RecordSource = "SELECT stock_deposito.id_deposito… |
| Lista_Pedidos_OPT.frm | 2557 | SELECT | Data_Stock.RecordSource = "SELECT stock_deposito.id_deposito… |
| Lista_Pedidos_OPT.frm | 2569 | SELECT | Data_Stock.RecordSource = "SELECT stock_deposito.id_deposito… |
| FacturaB.frm | 5564 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| FacturaB.frm | 8395 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| FacturaB.frm | 24012 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito " & _ |
| FacturaB.frm | 24322 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito " & _ |
| FacturaB.frm | 27023 | JOIN | '            " LEFT JOIN stock_deposito ON (stock_deposito.i… |
| NotaCred_SinCompO.frm | 4324 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| NotaCred_SinCompO.frm | 14877 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| FacturaA.frm | 5277 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| FacturaA.frm | 20625 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito " & _ |
| FacturaA.frm | 20935 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito " & _ |
| FacturaA.frm | 22784 | JOIN | '             " LEFT JOIN stock_deposito ON (stock_deposito.… |
| PNotaDebCopia.frm | 5115 | SELECT | '                        rs_saldo_stock.Open "SELECT * FROM … |
| CargaDeposito.frm | 268 | SELECT | rs_nuevo_deposito.Open "select * from stock_deposito where i… |
| En_GeneraOE.frm | 3896 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| En_GeneraOE.frm | 4187 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| En_GeneraOE.frm | 5119 | JOIN | " LEFT JOIN  stock_deposito ON (stock_deposito.id_deposito=d… |
| En_GeneraOE.frm | 5130 | SELECT | Data_Stock.RecordSource = "SELECT stock_deposito.id_deposito… |
| En_GeneraOE.frm | 5138 | SELECT | Data_Stock.RecordSource = "SELECT stock_deposito.id_deposito… |
| stock_consulta_avanzada.frm | 2063 | JOIN | Mysql_2 = " LEFT JOIN stock_deposito ON (stock_deposito.id_a… |
| stock_consulta_avanzada.frm | 3841 | SELECT | rs_saldo_stock.Open "SELECT * FROM stock_deposito WHERE id_a… |
| … | … | … | *(186 referencias más)* |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| management/commands/verify_reservado_por_deposito.py | 52 | SELECT | FROM stock_deposito |
| management/commands/verify_reservado_por_deposito.py | 61 | SELECT | FROM stock_deposito sd |
| services/reconciliation_saldo_stock.py | 47 | SELECT | FROM stock_deposito |
| services/query_runner.py | 3155 | SELECT | FROM stock_deposito{sd_where_excl} |
| services/query_runner.py | 3447 | SELECT | FROM stock_deposito sd |
| services/reconciliation_saldo_pedido_proveedor.py | 244 | SELECT | FROM stock_deposito |

**Búsqueda predictiva (módulo stock):** `core/services/administranet_stock.py` — `get_stock_por_deposito(base_empresa, id_articulo)` usa esta tabla con JOIN a `deposito` para mostrar stock por depósito en el ingreso de renglón de movimiento de stock. Véase [BUSQUEDA_PREDICTIVA_ARTICULO_MOVIMIENTO_STOCK.md](../../BUSQUEDA_PREDICTIVA_ARTICULO_MOVIMIENTO_STOCK.md).

[← Índice de tablas](../DB_INDICE_TABLAS.md)