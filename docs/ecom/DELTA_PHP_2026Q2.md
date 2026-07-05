# Delta PHP administraNET-ecom (2026‑03‑31 → 2026‑07‑02) vs migración Synap

**Fecha del análisis:** 02/07/2026
**Repo PHP:** `git@github.com:licPflores/administraNET-ecom.git` (rama `master`)
**Corte del inventario de migración:** ~2026‑03‑30 (ver [REVERSE_ENGINEERING.md](./REVERSE_ENGINEERING.md), fecha de análisis).
**Base del diff:** `git diff --stat c3f8f422 HEAD` en `administraNET-ecom/` (último commit HEAD: `5898619c`, 02/07/2026).

## Propósito

El PHP original siguió en desarrollo activo (~3 meses) después de que se congelara el inventario de la migración `ecom/`. Este documento reconcilia cada **cambio funcional** PHP contra su estado en Synap (`ecom/` y `reports/`) para decidir qué incorporar y en qué orden. Excluye cambios puramente cosméticos (CSS, imágenes, ajustes mobile) salvo cuando afectan contrato de datos o negocio.

Leyenda de estado: **Pendiente** (no migrado) · **Parcial** (migrado v1, falta paridad) · **Reconciliar** (existe equivalente Synap, revisar fuente única) · **N/A** (cosmético / no aplica a Synap).

## Resumen cuantitativo del diff

- ~68 archivos funcionales (`.php`/`.js`/`.inc.php`) modificados, **+12.685 / −5.439** líneas.
- Grandes bloques: `lista-pedidos-total.php` (+1.740), `relay-pedidos.php` (+1.276), `gestion-devoluciones.php` (~1.211), `mod-cliente-rapido.php` (+1.119), `informe-clientes-vendedor.php` (+1.075, nuevo), `dashboard-estadisticas.php` (+956).

## Tabla de reconciliación (por área)

### Informes (destino: `reports/`) — PRIORIDAD

| Cambio PHP | Archivos | Estado Synap | Destino sugerido | Prioridad |
|---|---|---|---|---|
| **Clientes sin ventas por vendedor** (nuevo): clientes activos sin comprobantes en período, resumen por vendedor/global, gráfico | `relay-clientes-vendedor.php` (+319), `informe-clientes-vendedor.php` (+1.075) | **Migrado** ✅ (change `informe-clientes-sin-ventas-vendedor`; checkpoint `mayoristapp_informe_clientes_sin_ventas`; tests 18/18) | `reports` (ReportDefinition `clientes-sin-ventas-vendedor` + relay API operativo/gerencial) | **P0** |
| Utilidad gerencial + utilidad con inflación | `informe-utilidad-gerencial.php`, `informe-utilidad-inflacion-gerencial.php`, `relay-ventas-netas-gerencia.php` (`ut`/`uti`) | **Migrado** ✅ (change `informe-utilidad-gerencial`; checkpoint `mayoristapp_informe_utilidad_gerencial`; servicio dedicado `utilidad_gerencial.py`; tests 17/17) | `reports` gerencial (ReportDefinition `utilidad-gerencial` + relay API operativo/gerencial) | P1 |
| Cobranzas por vendedor / listado cobranza | `listado-cobranzas-vendedor.php`, `informes-json/cobranza_lista_vendedor_resumen.php` | **Migrado** ✅ (change `informe-cobranzas-por-vendedor`; checkpoint `mayoristapp_informe_cobranzas_vendedor`; tests 14/14) | `reports` (ReportDefinition `cobranzas-por-vendedor` + relay API operativo/gerencial) | P1 |
| Cuenta corriente (listado de pedidos del cliente) | `relay-cuenta-corriente.php` | **Migrado** ✅ en `ecom/` (portal cliente, scope `idcliente` de sesión): servicio `cuenta_corriente_pedidos_relay.py` + `CuentaCorrientePedidosRelayAPIView` (`/ecom/api/mayoristapp/ctacte/pedidos/` y `.../sugerencias-nro/`); checkpoint `mayoristapp_ctacte` (mig. 0004/0006/0007); tests `ecom/tests/test_ctacte_relay.py`. Es estado de cuenta **del propio cliente**, no informe gerencial. | `ecom` (portal cliente) | ✅ |
| Comprobantes no cancelados | `relay-comprobantes-ncancelados.php`, `relay-comp-no-cancelados-resumen.php` | **Migrado** ✅ en `ecom/` (portal cliente, scope `idcliente`): servicio `comprobantes_no_cancelados_relay.py` (listado + resumen, saldo firmado por TipoComprobante y saldo acumulado) + `ComprobantesNoCanceladosRelayAPIView`/`...ResumenRelayAPIView` (`/ecom/api/mayoristapp/comprobantes/no-cancelados/` y `.../no-cancelados-resumen/`); checkpoint `mayoristapp_comprobantes` (mig. 0003/0012); tests `ecom/tests/test_comprobantes_relay.py`. | `ecom` (portal cliente) | ✅ |
| Dashboard estadísticas | `dashboard-estadisticas.php` (+956) | Pendiente | `reports` (dashboard) | P2 |
| Promociones (listado) | `lista-promociones.php` | Pendiente | `reports`/`ecom` | P2 |
| Otros listados: nota crédito, recibos, stock existencias, facturas sin stock, mis consumos, clientes | `lista_nota_credito.php`, `lista-recibos.php`, `listado-stock-existencias.php`, `lista-facturas-sin-stock.php`, `lista-mis-consumos.php`, `listado-clientes.php` | Parcial (`ecom` relays lectura) | `reports`/`ecom` | P3 |

### Precios y catálogo (destino: `ecom/`)

| Cambio PHP | Archivos | Estado Synap | Prioridad |
|---|---|---|---|
| **Catálogo de productos mayorista (listado paginado + ficha detalle)** | `ajax-articulos.php`, `relay-art.php`, `inventario/includes/mas-vendidos.php` | **Migrado** ✅ (change `catalogo-carrito-checkout-mayorista` **Fase P0** implementada: listado paginado con filtros + ficha de detalle, solo lectura, precio calculado con motor existente `price_rules_engine`, stock desde `StockService`; servicios `ecom/services/catalogo_producto.py`; vistas `ecom/catalogo_producto_relay_views.py`; rutas `/ecom/api/mayoristapp/catalogo/articulos/listado/` y `.../articulos/<idart>/detalle/`; tests 8/8 OK. Doc: `docs/ecom/CATALOGO_MAYORISTA_P0.md`) | P0 |
| **Carrito mayorista (jcart)** | `jcart/jcart.php`, `carrito.js`, `ajax-calcula-precio.php` | **Migrado** ✅ (change `catalogo-carrito-checkout-mayorista` **Fase P1** implementada: carrito borrador persistido en Postgres synap (`EcomCart`/`EcomCartItem`, migración `ecom/0015`), precio del renglón vía motor único `resolver_precio_articulo` (paridad P0), stock con `StockService`, totales con desglose 21/10,5/exento + impuesto interno + descuento al pie (paridad `Jcart.update_subtotal`); servicio `ecom/services/mayorista_cart_service.py`; vistas `ecom/carrito_relay_views.py`; rutas `/ecom/api/mayoristapp/carrito/...`; **sin escritura MySQL legacy** (eso llega en P2); tests 15/15 OK. Doc: `docs/ecom/CARRITO_MAYORISTA_P1.md`) | P1 |
| **Checkout mayorista (alta PED/PRE)** | `alta_pedido_confirmado.php`, `alta_presupuesto_confirmado.php`, `control-cliente.php` | **Migrado** ✅ (change `catalogo-carrito-checkout-mayorista` **Fase P2** implementada: confirmación transaccional del carrito → alta de comprobante legacy en MySQL (`comp_ped` + `stockp` + `cliente_datos_adicionales`; `stock_deposito` solo PED) con `autocommit(False)` + COMMIT/ROLLBACK; numeración `codmov`/`talonarios` con `SELECT ... FOR UPDATE` (**corrige bug de concurrencia del PHP**); validación de stock disponible en el commit; idempotencia por estado del carrito; precio recalculado con el motor en el commit; autorización por límite de crédito (`cuentacliente` + `credito_limite_dias`); servicios `ecom/services/mayorista_checkout_service.py` + `mayorista_credito.py`; vista `ecom/checkout_relay_views.py`; ruta `/ecom/api/mayoristapp/checkout/confirmar/`; migraciones `ecom/0017` (campos resultado) y `0018` (checkpoint `mayoristapp_checkout`); tests 11/11 OK. **Gaps documentados:** CAE/FE, medios de pago/caja, devolución (DEV→P3). Doc: `docs/ecom/CHECKOUT_MAYORISTA_P2.md`) | P2 |
| **Percepciones IIBB (checkout)** | `jcart/jcart.php` (1093–1171), `alta_pedido_confirmado.php` (407–421), `alta_presupuesto_confirmado.php` (222–236), `sucursales.agente_percep` | **Migrado** ✅ (change `catalogo-carrito-checkout-mayorista` **Fase P4**, 03/07/2026): **configurable por implementación** vía `sucursales.agente_percep`. Servicio `ecom/services/mayorista_percepciones.py` (base = neto con descuento; lee `percep_cli_param`+`percep_cli_tipo`; `importe=base*alic/100` sin `importe_minimo`, paridad jcart); integrado transaccionalmente en `mayorista_checkout_service.confirmar` (INSERT `percep_cli` por tipo + `comp_ped.total_percep`) para PED/PRE; flag resuelto desde sucursal del usuario (`usuarios→sucursales`) u override de sesión; bloqueo con ROLLBACK si agente sin `percep_cli_param`; DEV fuera de alcance; checkpoint `mayoristapp_percepciones_iibb` (`0025`); tests 22/22 (`TestCheckoutPercepcionesIIBB`, 5 casos). REQ-CHK-009. Doc `PERCEPCIONES_IIBB_P4.md` | P4 |
| **Cálculo de pallet legacy + optimizado** y edición de cantidad | commits `be0bae8d`, `09c6879e`, `1851269d`, `f0ad624c`; `carrito.js`, `jcart.php`, `ajax-calcula-precio.php` | Pendiente en `ecom/services/price_calculator.py` (crítico paridad precios) | **P0/P1** |
| Quita filtro `ecommerce`/`publicados`, cambios de rubro | `relay-rubro.php` (+49), `4f5fde53`, `fe5f84f0` | Verificar contra `ecom` catálogo relays | P1 |
| Fix IVA anterior | `ebf02d77` | Verificar `price_calculator` | P1 |
| Export PDF lista precios alto volumen (umbrales, chunking, shutdown handler) | `exporta_lista_pdf.php` (+699); `LP_PDF_MAX_*` | **Migrado** ✅ (change `catalogo-carrito-checkout-mayorista` **Fase P3**: `ecom/services/lista_precio_pdf.py` con reportlab A3-L, reutiliza catálogo P0 (filtros + motor de precios) sin paginar; guardrails de volumen (`LP_PDF_MAX_ITEMS/_CON_IMAGEN`) y tiempo (`LP_PDF_MAX_SECONDS/_CON_IMAGEN`, cada 50 filas) desde `settings`/env con página HTML amigable en español; ruta `GET /ecom/api/mayoristapp/catalogo/lista-precios.pdf`; checkpoint `mayoristapp_lista_precios_pdf` (`0021`); tests 4/4. **Gaps:** imágenes embebidas y background (Celery off; síncrono acotado como el legacy); `*_SECONDS` a re-medir en deploy. Docs `LISTA_PRECIOS_PDF_P3.md` + `RUNBOOK_EXPORTACION_PDF.md`) | P3 |

### Comprobantes y pedidos (destino: `ecom/`)

| Cambio PHP | Archivos | Estado Synap | Prioridad |
|---|---|---|---|
| **Selección de punto de venta en comprobante** (ped/pre/dev) | `c4642e20`; `alta_pedido.php`, `alta_presupuesto.php`, `alta-devolucion.php` | Pendiente en comprobantes relay | P1 |
| **Promociones dentro del pedido** | `f0964e57`; `alta_pedido.php`, `ajax-articulos.php` | Pendiente | P1 |
| Listado de pedidos con detalle + export PDF/Excel propios; filtro `anulado` | `relay-pedidos.php` (+1.276), `lista-pedidos-total.php` (+1.740), `cd66b590` | Parcial (comprobantes listados v1) | P1 |
| Confirmación modal checkout (íconos FA, jerarquía) | `jcart.js`, `jcart.php` | Pendiente (UI) | P3 |
| Devoluciones (rediseño) | `gestion-devoluciones.php`, `alta-devolucion.php` | **Alta migrada** ✅ (change `catalogo-carrito-checkout-mayorista` **Fase P3**: alta de devolución (DEV) reutilizando el servicio transaccional de checkout — `mayorista_checkout_service.confirmar(tipo='DEV')`; `comp_ped`+`stockp`+numeración `FOR UPDATE`; `stock_deposito.saldo_pedido_cliente` incrementa **sin** validación de disponible (paridad legacy); **corrige bug PHP** que numeraba talonario `PED` en un alta `DEV`; endpoint compartido `/ecom/api/mayoristapp/checkout/confirmar/` con `tipo='DEV'`; tipo `DEV` en `EcomCart` (migración `0019`); checkpoint `mayoristapp_devolucion` (`0020`); tests 13/13. Lectura/gestión ya existía en `ecom` devoluciones relay. Doc: `CHECKOUT_MAYORISTA_P2.md` §Devolución) | P3 |

### Módulos / features nuevos

| Cambio PHP | Archivos | Estado Synap | Acción |
|---|---|---|---|
| **Módulo objetivos** | `modulo_objetivos.php`, `modulo_objetivos/abm-objetivos.php` (+433), `modulo_objetivos/relay-objetivos.php` (+489) | **Reconciliado** ✅ — fuente única = Synap: CRUD en MySQL `viajantes_objetivos_periodo/ventas` (`ventas/services/objetivos_mysql.py`, `/ventas/objetivos-venta/`) + informe de cumplimiento `reports` slug `ventas-objetivos-vs-bo` (`reports/services/ventas_objetivos_bo_runner.py`). El PHP guarda objetivos en **archivos JSON** por vendedor/tipo y **no calcula cumplimiento**: NO se porta. Gap cerrado: `reports/migrations/0036_add_ventas_objetivos_vs_bo_report.py` registra el `ReportDefinition` faltante (tests 12/12 OK). | **NO portar PHP**; Synap canónico |
| **Productos destacados** (dashboard) | `componente-productos-destacados.php` (+432), lógica real en `inventario/includes/mas-vendidos.php` (`trae_productos_destacados`) | **Diferido** ⏸️ (02/07/2026; prerequisito **desbloqueado** 03/07/2026) — grid de promocionados por `articulo.promocion_destacado_web='Si'`; dependía del motor de precios mayoristas + carrito + sesión de cliente, **ya migrados en P3** (catálogo/carrito/checkout y UI `/ecom/mayoristapp/compra/`). Queda como **follow-up de ficha/dashboard visual** (grid de destacados + imágenes), no de la mecánica de precios/carrito. | **Follow-up** (ficha/destacados web sobre catálogo P0 ya migrado) |
| **Medicamentos AMICO** | commit `47c8bd3d` (`control.php`, `ajax-articulos.php`) | **Migrado** ✅ (change `catalogo-carrito-checkout-mayorista` **Fase P3**, 03/07/2026): rehecho como **restricciones de catálogo por PV con config en BD** (no hardcode, no atado a AMICO). Modelo `EcomCatalogoRestriccionPV` (Postgres, migr. `0022`) por PV excluye artículo/rubro/subrubro; `catalogo_restricciones.py` + `_construir_where_catalogo` (NOT IN parametrizado); aplicado en listado + export PDF; gestionable por Django admin; checkpoint `mayoristapp_restricciones_pv` (`0023`); tests 8/8. Doc `RESTRICCIONES_CATALOGO_PV_P3.md` | P3 |
| Inventario: carga imágenes / scanner | `inventario/js/busqueda-rapida/*` | Fuera de núcleo mayorista (SPA inventario) | Diferido |

### Sesión / login / dashboard / cliente

| Cambio PHP | Archivos | Estado Synap | Prioridad |
|---|---|---|---|
| Login: botón mostrar contraseña, ajustes control | `control.php` (+70), `index.php`, `sesion.inc.php` | UI login Synap propia | P3 |
| Menú header / dashboard módulos / buscador dashboard | `header-vendedor.inc.php`, `dashboard-modulos.php` | UI Synap propia | P3 |
| Cliente rápido / domicilios (rediseño) | `mod-cliente-rapido.php` (+1.119), `abm-cliente-domicilios.php` | Parcial (`ecom` cliente relays) | P2 |

## Decisiones abiertas (a acordar)

1. ~~**Módulo objetivos:** ¿fuente única en `ventas/`+`reports/` (ya existente) o portar la lógica nueva de `relay-objetivos.php`?~~ **RESUELTO (02/07/2026):** fuente única = Synap (`ventas/` CRUD MySQL + informe `reports` `ventas-objetivos-vs-bo`). El PHP `modulo_objetivos` (objetivos en JSON, sin cumplimiento) **no se porta**. Cerrado el gap del `ReportDefinition` faltante en `reports/migrations/0036`. Comparativa: PHP granular por rubro/subrubro/marca/proveedor/cliente en JSON aislado vs Synap por cliente/período en MySQL con cumplimiento (BO); si a futuro se requiere granularidad rubro/marca, extender el modelo Synap (no reintroducir el JSON).
2. ~~**Productos destacados** y **medicamentos AMICO:** definir si entran en este alcance o se difieren.~~ **RESUELTO (02/07/2026): DIFERIR ambos.** Productos destacados depende del **catálogo/carrito mayorista** (motor de precios, jcart) aún no migrado → diferido con ese prerequisito. Medicamentos AMICO **no es trazabilidad ANMAT** sino baneo de artículos por PV fiscal/no fiscal (IDs hardcodeados). **RETOMADO E IMPLEMENTADO (03/07/2026, Fase P3):** rehecho como **restricciones de catálogo por PV con config en BD** (`EcomCatalogoRestriccionPV`, genérico, no atado a AMICO). Ver fila "Medicamentos AMICO" arriba y `docs/ecom/RESTRICCIONES_CATALOGO_PV_P3.md`.
3. ~~**Export PDF alto volumen:** en Synap ya hay runbook (`RUNBOOK_EXPORTACION_PDF.md`); confirmar umbrales `LP_PDF_MAX_*`.~~ **RESUELTO (02/07/2026):** el runbook **no existía** (afirmación previa inexacta); se **creó** en `docs/general/RUNBOOK_EXPORTACION_PDF.md` con los umbrales confirmados del legacy (`LP_PDF_MAX_ITEMS=2500`, `..._CON_IMAGEN=1800`, `LP_PDF_MAX_SECONDS=90`, `..._CON_IMAGEN=180`) + guardrails (corte por volumen/tiempo, shutdown handler) y mapeo a Synap (`reportlab`, `export_service`, background). El export de lista de precios en sí queda **diferido** con el catálogo/carrito mayorista (decisión #2); los `LP_PDF_MAX_SECONDS*` deben **re-medirse** en el entorno Synap al implementar.

## Primer entregable ejecutado

Change OpenSpec `informe-clientes-sin-ventas-vendedor` (P0) **implementado**: `relay-clientes-vendedor.php` → `reports` con UI canónica.
- Servicio: `reports/services/clientes_sin_ventas.py` (SQL parametrizado, tipos AdministraNET).
- Relay: `reports/clientes_sin_ventas_relay_views.py` (`/api/reports/clientes-sin-ventas/relay/` y `.../gerencia/`).
- UI: `reports/templates/reports/dashboard_clientes_sin_ventas_vendedor.html` (`/reports/dashboard/clientes-sin-ventas-vendedor/`).
- Migración: `reports/migrations/0032_add_clientes_sin_ventas_report.py` (ReportDefinition + checkpoint).
- Tests: `reports/tests/test_clientes_sin_ventas_relay.py` (18/18 OK en `Synap_app`).

## F0 Fundaciones Synap (04/07/2026) — change `ecom-migracion-completa`

| Entregable | Estado |
|------------|--------|
| Módulo `ecom` en MODULE_CONFIGS + ModuleConfig (`0026`) | **Migrado** ✅ |
| `menu_config.py` + permisos `ecom.*` | **Migrado** ✅ |
| Hub `/ecom/mayoristapp/` (7 cards PHP) | **Migrado** ✅ |
| API REST v1 piloto pedidos + deprecation legacy | **Migrado** ✅ |
| Checkpoint `mayoristapp_modulo_shell` (`0027`) | **Migrado** ✅ |

Docs: [INVENTARIO_HUB_MAYORISTAPP.md](./INVENTARIO_HUB_MAYORISTAPP.md), [API_REST_V1_MAPPING.md](./API_REST_V1_MAPPING.md).

## F1 Piloto pedidos (04/07/2026)

| Entregable | Estado |
|------------|--------|
| Matriz reutilización F1 | **Documentado** ✅ |
| UI pedidos vendedor + API v1 | **Migrado** ✅ |
| Framework listados genérico F1 | **Migrado** ✅ (`listado_mayoristapp`) |
| UI: remitos, FE, NC, recibos, devoluciones, promociones | **Migrado** ✅ |
| UI clientes (búsqueda/selección) | **Migrado** ✅ |
| API artículo-remito + UI | **Migrado** ✅ |
| API detalle pedido v1 + filtro `campoAnulado` | **Migrado** ✅ |
| F2 portal: consumos, ctacte, no cancelados, pedidos cliente | **Migrado** ✅ (shell) |
| Gaps: export PDF pedidos, alta recibo, IIBB DEV, pallet checkout | **Pendiente** |
| F3: premios, inventario SPA, tmobile | **Pendiente** (decisión producto) |

## Mantenimiento de este documento

Actualizar tras cada vertical/informe migrado (marcar estado → migrado, enlazar change OpenSpec y checkpoint `EcomMigrationCheckpoint`). Recalcular el diff base cuando el PHP avance: `git -C administraNET-ecom log --oneline -5`.
