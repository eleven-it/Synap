# Análisis de persistencia: Remitos de compra (PRemito.frm)

Documento desglosado del **contrato de persistencia** para la migración PRemito.frm → Synap. El inventario completo, mapa de eventos, diseño Django y plan por etapas están en [INVENTARIO_FORMULARIO_REMITOS_DE_COMPRA.md](INVENTARIO_FORMULARIO_REMITOS_DE_COMPRA.md).

**Fuentes:** Código VB6 en `administranet_vb6/Formularios/PRemito.frm` (Guardar ~3308–4226, Eliminar_Click ~5240, modificacion_comp ~6334, GuardarSerie ~6652); [STOCK_VB6_PROCEDIMIENTOS_GUARDADO](../self_checkout/STOCK_VB6_PROCEDIMIENTOS_GUARDADO.md) § 2.6; referencias en `docs/general/tablas/`.

---

## Estado de paridad UI: selección de depósito (2026-02-15)

- Se replicó en Synap el selector VB6 `Deposito_Seleccion` con modos:
  - `defecto_usuario` (equiv. "Defecto usuario")
  - `comp_original` (equiv. "Comp. original")
  - `seleccionado` (equiv. "Seleccionado" + `Deposito_Global`)
  - `por_articulo` (equiv. "Por artículo" + `Deposito_Articulo`)
- Carga de opciones de depósito:
  - Si `cambia_deposito = Si`: primero `deposito_usr` por `id_usuario`; si no hay filas, todos los depósitos no anulados.
  - Si `cambia_deposito <> Si`: solo `id_deposito` del usuario (equiv. `Principal.id_deposito`).
- En alta de renglón (`cuerpostockp.CodDeposito`) se respeta el modo seleccionado:
  - `por_articulo`: usa depósito del renglón.
  - `seleccionado`: usa depósito global de cabecera.
  - `defecto_usuario` / `comp_original`: usa depósito del usuario.

---

## Contrato de persistencia (operaciones y orden)

| Operación / flujo | SQL / operación | Tablas/campos impactados | Transacción | Manejo de errores |
|-------------------|-----------------|---------------------------|-------------|-------------------|
| Lectura contador | SELECT * FROM codmov WHERE codigo = 1 | codmov (lectura) | No | *A completar con código VB6* |
| Lectura cabecera OC/remito/factura | SELECT * FROM cuentaproveedor WHERE ... | cuentaproveedor (lectura) | No | — |
| Lectura renglones temporales | SELECT * FROM cuerpostockp WHERE CodUsuario=? AND visualiza=? [y CodigoMovimiento] | cuerpostockp (lectura) | No | — |
| Borrar renglón temporal | DELETE FROM cuerpostockp WHERE Orden = ? | cuerpostockp.Orden | (dentro de transacción si aplica) | Doc: PRemito.frm ~5255 |
| Limpieza series temporales | DELETE FROM serie_entrada_temp WHERE ... | serie_entrada_temp | (dentro de transacción si aplica) | Doc: ~5260, 6244 |
| Alta cabecera remito | INSERT cuentaproveedor (TipoComprobante REM, NroComprobante, Fecha, Codigo proveedor, CodigoMovimiento, ...) | cuentaproveedor | Sí | *A completar: On Error, Rollback* |
| Actualizar contador | UPDATE codmov SET CodigoMovimiento = ? WHERE codigo = 1 | codmov.CodigoMovimiento | Sí | — |
| Por cada renglón: alta stock | INSERT stock (CodigoMovimiento, Fecha, IDArt, Entrada, Comprobante='REM', TipoComp='Remito Entrada', CodDeposito, ...) | stock | Sí | — |
| Por cada renglón: saldo depósito | UPDATE stock_deposito SET Saldo = Saldo + ? [y saldo_pedido_proveedor si OC] WHERE ... | stock_deposito.Saldo, saldo_pedido_proveedor | Sí | — |
| Vínculo remito–OC | INSERT oc_remp (codigo_movimiento_remp, codigo_movimiento_oc, anulado) | oc_remp | Sí | — |
| Series | INSERT serie_entrada desde serie_entrada_temp; INSERT serie_movimiento | serie_entrada, serie_movimiento | Sí | — |
| Lotes (si aplica) | SELECT/INSERT lote, UPDATE/INSERT lote_stock | lote, lote_stock | Sí | PRemito.frm ~3857, 3916 |
| Commit / Rollback | CommitTrans tras todos los writes; RollbackTrans en error | — | Sí | *A completar con código VB6* |

---

## Orden de escritura a replicar en Django (regla de oro)

En VB6 hay **dos transacciones** en Guardar: la primera solo actualiza codmov; la segunda agrupa el resto.

1. **Transacción 1 (corta):** BeginTrans → **codmov** UPDATE (incrementar CodigoMovimiento) → CommitTrans.
2. **Transacción 2 (remito):** BeginTrans →
   - **cuentaproveedor** — INSERT cabecera (TipoComprobante REM, NroComprobante, Fecha, Codigo, CodigoMovimiento, ImporteCompra, IVA, Percepciones, etc.).
   - Por cada renglón: **stock_deposito** (SELECT; UPDATE Saldo o AddNew); **stock** INSERT (Comprobante='REM', TipoComp='Remito Entrada', ...); **lote**/**lote_stock** si aplica.
   - **cuentaproveedor** (OC): UPDATE Estado = "En Remito" o "Parcial" de la OC origen.
   - **oc_remp** — INSERT (codigo_movimiento_remp, codigo_movimiento_oc, anulado='No').
   - **remp_factp** y **cuentaproveedor** estado_fact_remito/estado_remito si factura no remite.
   - **serie_entrada** y **serie_movimiento** — INSERT desde serie_entrada_temp (GuardarSerie).
   - CommitTrans. En error: RollbackTrans.

Eliminar renglón (sin transacción): DELETE cuerpostockp WHERE Orden = id; DELETE serie_entrada_temp (id_articulo, orden, id_usuario, tipo_comprobante).

---

## Conexión y tipos de datos

- **Conexión VB6:** `conn.ConnectionString = IngresoUsuario.Conex`; `conn.CursorLocation = adUseClient`; `conn.Open` al inicio de Guardar, Eliminar_Click, Inicial, Form_Load (rs_depo). Objeto `conn` (ADODB.Connection) de formulario.
- **Synap:** Usar el mismo patrón que en stock/compras: `core.mysql_pool` o `core.services.administranet_*` con `base_empresa` de sesión. Validar y normalizar tipos con `core.utils.administranet_types` (INT, DATE, VARCHAR, DECIMAL) según [TIPOS_DATOS_ADMINISTRANET.md](TIPOS_DATOS_ADMINISTRANET.md) y schemas en `docs/general/tablas/`.

---

## Referencias

- [INVENTARIO_FORMULARIO_REMITOS_DE_COMPRA.md](INVENTARIO_FORMULARIO_REMITOS_DE_COMPRA.md) — sección 5 (contrato completo en el mismo documento).
- [STOCK_VB6_PROCEDIMIENTOS_GUARDADO](../self_checkout/STOCK_VB6_PROCEDIMIENTOS_GUARDADO.md) — § 2.6 PRemito.
- Tablas: [stock](tablas/stock.md), [stock_deposito](tablas/stock_deposito.md), [cuentaproveedor](tablas/cuentaproveedor.md), [cuerpostockp](tablas/cuerpostockp.md), [oc_remp](tablas/oc_remp.md), [serie_entrada](tablas/serie_entrada.md), [serie_entrada_temp](tablas/serie_entrada_temp.md), [serie_movimiento](tablas/serie_movimiento.md), [codmov](tablas/codmov.md), [lote](tablas/lote.md), [lote_stock](tablas/lote_stock.md).
