# Propuesta — Catálogo, carrito y checkout mayorista (ecom)

**Change:** `catalogo-carrito-checkout-mayorista`
**Fecha:** 02/07/2026
**Modo:** Migration Mode (nuevas capacidades) + Evolution Mode (reutiliza infra `ecom/` y `self_checkout/` existente, sin romper contratos)
**Origen legacy:** `administraNET-ecom/mayoristapp` (catálogo, `jcart/`, `alta_pedido*.php`, `alta_presupuesto*.php`, `alta-devolucion*.php`)
**Skill:** `adminnet-module-migration` (DISCOVER→AUDIT→SPEC→DESIGN→TEST→IMPLEMENT→INTEGRATE; escrituras legacy controladas)

---

## 1. Intención

Completar el vertical de **compra mayorista B2B** en Synap: que un vendedor (o cliente) pueda **navegar el catálogo con precios**, **armar un carrito** y **confirmar un pedido/presupuesto** (alta de comprobante en MySQL AdministraNET), con paridad funcional respecto al `mayoristapp` PHP. Esto además **desbloquea** ítems diferidos del DELTA (Productos destacados, Export lista de precios PDF, restricciones AMICO, promociones dentro del pedido).

---

## 2. Estado actual (hallazgo de la exploración)

**Ya migrado en Synap (reutilizar, NO reconstruir):**

- **Catálogo lectura:** rubros, subrubros, marcas, laboratorios, proveedores, lotes, más vendidos, autocomplete de artículos, filtros en sesión (`ecom/services/catalogo_*.py`, `ecom/catalogo_relay_views.py`).
- **Motor de precios COMPLETO:** `ecom/services/price_calculator.py` + `price_rules_engine.py` (reglas particular/masiva/general, promociones, intervalos por cantidad, IVA, impuesto interno, descuento cliente, monto fijo TTC) + relays `precio_relay_views.py` + tests. **Este era el componente más complejo y ya existe.**
- **Clientes:** búsqueda, selección en sesión, alta/edición rápida, domicilios, contactos (`ecom/services/cliente_*.py`).
- **Comprobantes:** listado pedidos/presupuestos/remitos y **anulación** (`comprobantes_relay.py`, `comprobantes_anulacion.py`).
- **Carrito + confirmación con escritura legacy (TPV):** `self_checkout/services/cart_service.py` + `confirmation_service.py` (INSERT a `stock`/`cuentacliente`/talonarios, numeración, transacción atómica) — **patrón reutilizable**.
- **Infra:** `core.mysql_pool`, `core.utils.administranet_types`, `ecom/permissions.py` (`EcomMayoristappSessionPermission`), sesión mayorista (`mayoristapp_session.py`).

**Falta (alcance de este change):**

1. **Ficha y listado paginado de producto** (detalle con precio calculado + stock + imagen + promos; listado por rubro/subrubro/filtros, no solo autocomplete).
2. **Carrito mayorista** (persistencia, alta/quita/cantidad, totales con motor de precios, validación de stock).
3. **Checkout mayorista = alta de pedido/presupuesto** (INSERT `comp_ped` + `stockp` + numeración `talonarios`/`codmov` + `stock_deposito.saldo_pedido_cliente` + `percep_cli` + `cliente_datos_adicionales`, con validaciones de crédito/autorización, selección de punto de venta y promociones).

---

## 3. Alcance por fases

| Fase | Entregable | Riesgo | Escritura legacy |
|------|-----------|--------|------------------|
| **P0 — Catálogo producto** | Ficha de artículo (precio motor + stock + imagen + promos) y listado paginado por filtros. Reutiliza motor de precios. | Bajo | No (solo lectura) |
| **P1 — Carrito mayorista** | Modelo/servicio de carrito (Postgres `synap`), agregar/quitar/actualizar, totales con motor de precios, validación stock (reutiliza `self_checkout.StockService`). | Medio | No (carrito en Synap) |
| **P2 — Checkout (alta PED/PRE)** | Confirmación transaccional: INSERT `comp_ped` + `stockp` + numeración + `stock_deposito` + `percep_cli` + `cliente_datos_adicionales`; validaciones crédito/autorización; selección de PV; promociones. | **Alto** | **Sí (controlada, solo en commit)** |
| **P3 — Extras** | Alta de devolución (DEV), export lista de precios PDF (runbook), restricciones de catálogo por PV (ex-AMICO, config BD), UI web completa. | Medio | Parcial |

Este proposal cubre las 4 fases; **spec + design detallados se entregan por fase**. Se inicia con **spec/design de P0**.

---

## 4. Principios (adminnet-module-migration)

- **Separación estricta app/legacy:** UI/carrito/validaciones en Synap; escritura MySQL solo vía adapter transaccional en P2.
- **Escrituras legacy controladas:** solo en la acción de confirmar (commit), nunca en borrador de carrito, siempre `transaction`/BEGIN-COMMIT-ROLLBACK.
- **Validación pre-commit:** stock disponible, límite de crédito del cliente, autorización (vendedor vs cliente), y **numeración segura bajo concurrencia** (ver §5).
- **Consistencia de endpoints:** una sola ruta canónica de alta por tipo (PED/PRE/DEV); mismo comportamiento que TPV donde aplique.
- **Trazabilidad:** persistir estado de validaciones y `CodigoMovimiento` generado; checkpoint `EcomMigrationCheckpoint`.
- **UI canónica:** seguir `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md` (patrones reports/MPR), NO las pantallas excluidas.

---

## 5. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| **Numeración duplicada** (`talonarios.Nro` en PHP NO usa lock; `codmov` sí usa optimistic lock) | En Synap: `SELECT ... FOR UPDATE` sobre `talonarios` dentro de la transacción, o optimistic lock con reintento (paridad `codmov`). Reutilizar patrón de `self_checkout/services/talonarios_service.py`. |
| **Escritura parcial** (comp_ped sin stockp) | Transacción atómica única con rollback + limpieza defensiva (paridad PHP DELETE). |
| **Doble alta (doble submit)** | Idempotencia por token de carrito + verificación de estado del carrito antes de commit. |
| **Stock comprometido inconsistente** (`stock_deposito.saldo_pedido_cliente`) | UPDATE dentro de la misma transacción; `FOR UPDATE` por artículo. |
| **Divergencia de precios carrito↔checkout** | Recalcular precios en el commit con el motor (`price_rules_engine`), no confiar en el precio del carrito. |
| **Alcance excesivo** | Entrega incremental por fases; P0/P1 sin escritura legacy dan valor y reducen riesgo antes de P2. |

---

## 6. Fuera de alcance

- Pasarela de pago / facturación electrónica mayorista (el pedido nace `Pendiente`, se factura desde AdministraNET/otro flujo).
- Reescritura del motor de precios (ya existe).
- Migración del carrito PHP `jcart` en sí (se reemplaza por carrito Synap).
- TPV self_checkout (ya existe; solo se reutilizan patrones).

---

## 7. Criterios de éxito

1. Un vendedor puede: buscar/ver artículos con precio correcto → agregar al carrito → confirmar pedido → se crea `comp_ped` + `stockp` correctos y numerados, sin duplicar números bajo concurrencia.
2. Ninguna escritura legacy ocurre fuera del commit ni fuera de transacción.
3. Validaciones de crédito/autorización/stock replican el legacy.
4. Tests en contenedor: `docker exec Synap_app python manage.py test ecom` (servicios + checkout con mocks/concurrencia).
5. Checkpoint `mayoristapp_catalogo_carrito` registrado; DELTA actualizado.

---

## 8. Decisiones (resueltas 02/07/2026 — defaults recomendados)

1. **Persistencia del carrito:** tabla propia `ecom_cart`/`ecom_cart_item` en Postgres `synap` (no acopla TPV con B2B).
2. **Numeración:** `SELECT ... FOR UPDATE` sobre `talonarios` dentro de `transaction.atomic()` (corrige el bug de concurrencia del PHP).
3. **Alcance inicial:** solo **vendedor** (selecciona cliente y arma el pedido); cliente autogestión en iteración posterior.
4. **Arranque:** Fase **P0** (catálogo producto, lectura, bajo riesgo).

---

*Propuesta lista para fase **spec** + **design** (P0). Sin implementación de código en esta entrega.*
