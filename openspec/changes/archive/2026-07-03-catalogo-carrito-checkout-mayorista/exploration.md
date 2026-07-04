# Exploración — Catálogo, carrito y checkout mayorista

**Change:** `catalogo-carrito-checkout-mayorista`
**Fecha:** 02/07/2026
**Método:** 3 exploraciones paralelas (PHP catálogo/precios, PHP carrito/checkout, inventario Synap `ecom/`).

---

## 1. Legacy PHP — Catálogo y motor de precios

- **Búsqueda/listado** (`ajax-articulos.php`, `relay-art.php`): 11 filtros (categoria, rubro, subrubro, marca, modelo, laboratorio, proveedor, tacc, promo, consumo, texto/código, lista de precios, depósito, tipoCliente). SQL principal ~12 tablas (`articulo`, `ecom_info_articulo`, `rubro`, `subrubro`, `marca`, `modelo`, `rubro_categoria`, `iva`, `articulo_prov`, `stock/stockp`, `deposito`). Filtro de baneo por PV fiscal/no fiscal (AMICO).
- **Motor de precios** (corazón): precedencia **regla específica > masiva > general > promoción > descuento cliente**; 6 tipos de promoción con vigencia; impuesto interno ABM (4 tipos); corrección IVA incluido/no; presentación/bulto con multiplicadores. Depende de sesión (`clienteDetalle`, `lista_precio_defecto`, `usaReglaPrecio`, `muestra_precio`).
- **Lista de precios** (`lista_precio.php`): filtros UI + export Excel/PDF (`exporta_lista_pdf.php`, mPDF).
- 21 tablas involucradas, **todas read-only** en este flujo.

## 2. Legacy PHP — Carrito (jcart) y checkout

- **Carrito** = `$_SESSION['jcart']` (clase `Jcart`, ~5.4k líneas): items, precios netos/brutos, IVA 21/10.5, exento, descuentos, impuesto interno, percepciones, promociones, presentación (unidad/display/bulto/pallet). Totales acumulados. Checkout dispara modal de confirmación.
- **Selección de PV** (commit `c4642e20`): `$_SESSION['id_punto_venta_activo']` + `punto_venta_activo_cont` (Si=fiscal). Afecta numeración (`talonarios WHERE id_punto_venta+TipoComprobante`).
- **Alta de pedido** (`alta_pedido_confirmado.php`, ~970 líneas):
  - **TX1 — CodigoMovimiento:** bucle **optimistic lock** sobre `codmov` (SELECT +1, UPDATE ... WHERE CodigoMovimiento=viejo, revisar affected_rows).
  - **TX2 — alta:** número desde `talonarios` (**UPDATE Nro+1 SIN lock → riesgo de duplicado**), fecha entrega (saltando no laborables), INSERT `cliente_datos_adicionales`, INSERT `percep_cli` (por percepción), INSERT `comp_ped` (cabecera 40+ campos), loop INSERT `stockp` (renglón 50+ campos) + UPDATE `stock_deposito.saldo_pedido_cliente`. COMMIT/ROLLBACK con limpieza defensiva (DELETE).
- **Presupuesto** (`alta_presupuesto_confirmado.php`): igual sin bajar stock, `TipoComprobante='PRE'`.
- **Devolución** (`alta_devolucion_confirmado.php`): `TipoComprobante='DEV'`, suma stock (reverso).
- **Validaciones pre-commit:** stock (`saldo_pedido_cliente`), límite de crédito por días de atraso (`cuentacliente`), autorización (vendedor sin exceso → Autorizado; cliente → No Autorizado). Sin control de duplicados.
- **Tablas de ESCRITURA críticas:** `codmov`, `talonarios`, `comp_ped`, `stockp`, `stock_deposito`, `percep_cli`, `cliente_datos_adicionales`.

## 3. Inventario Synap `ecom/` (qué ya existe)

- **Catálogo lectura:** `catalogo_relay_views.py` (rubros, subrubros, marcas, laboratorios, proveedores, lotes, más vendidos, autocomplete) + servicios `catalogo_*.py`.
- **Motor de precios COMPLETO:** `price_calculator.py` + `price_rules_engine.py` (reglas particular/masiva/general, promos, intervalos, IVA, interno, descuentos, monto fijo) + `precio_relay_views.py` + tests (`test_price_*`).
- **Clientes:** búsqueda/selección/alta-edición rápida/domicilios/contactos.
- **Comprobantes:** listado (PED/PRE/REM) + **anulación** (`comprobantes_anulacion.py`). **NO hay alta.**
- **Sesión:** `mayoristapp_session.py` (idcliente, cliente, iva_incluido, formulario, filtros; solo `pop("jcart")`).
- **self_checkout/ (TPV):** `cart_service.py` (carrito Postgres synap: crear/agregar/quitar/limpiar/voucher/recalcular con validación de stock) + `confirmation_service.py` (**escritura legacy transaccional**: talonarios, `cuentacliente`, `stock_deposito`, `stock`, FE/CAE, audit) + `stock_service.py` + `talonarios_service.py`. **Patrones reutilizables para el checkout mayorista.**
- **Infra:** `core.mysql_pool`, `core.utils.administranet_types`, `ecom/permissions.py`.
- **Checkpoints existentes:** `mayoristapp_clientes`, `mayoristapp_comprobantes`, `mayoristapp_ctacte`, `mayoristapp_recibos`, `mayoristapp_fe`, `mayoristapp_informes_vn(_gerencia)`.

## 4. Conclusión de alcance

El componente más caro (motor de precios) y todo el catálogo de lectura + selección de cliente **ya existen**. El trabajo real es: **ficha/listado de producto (P0)**, **carrito mayorista (P1)** y **checkout/alta de comprobante (P2, alto riesgo por escrituras + numeración)**, más extras (P3). Se reutilizan intensamente `price_rules_engine`, `mayoristapp_session`, y los patrones de `self_checkout` (cart + confirmation + talonarios + stock).

## 5. Referencias
- PHP: `administraNET-ecom/mayoristapp/{ajax-articulos.php, relay-art.php, jcart/jcart.php, alta_pedido_confirmado.php, alta_presupuesto_confirmado.php, alta_devolucion_confirmado.php}`.
- Synap: `ecom/services/{price_calculator.py, price_rules_engine.py, catalogo_articulo.py, mayoristapp_session.py}`, `self_checkout/services/{cart_service.py, confirmation_service.py, talonarios_service.py, stock_service.py}`.
