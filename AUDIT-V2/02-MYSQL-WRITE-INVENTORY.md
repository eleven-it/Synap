# 02 — Inventario Total de Escrituras sobre AdministraNET

**Estado:** COMPLETE  
**Fecha:** 25/08/2026  
**Método:** ripgrep + parser Python sobre `INSERT INTO`, `UPDATE`, `DELETE FROM`, `REPLACE INTO` en `*.py` (excl. `migrations/`, `tests/`, `* 2.py`)

---

## Resumen ejecutivo

| Métrica | Valor |
|---------|------:|
| Escrituras SQL a tablas AdministraNET/SHARED | **587** |
| Tablas SHARED/ADMINISTRANET distintas | **98** |
| Módulo con más escrituras | **mpr** (239, ~41%) |
| `REPLACE INTO` en producción | **0** |
| `executemany` a tablas AN | **0** |
| `.save()` ORM a MySQL legacy | **0** (legacy_db .save → PG audit) |

**Excluido del conteo:** tablas SYNAP OWNED (`synap_*`, `mpr_*`, `self_checkout_*`, `inv_fisico_*`, `ecom_*` DDL).

---

## Taxonomía de acceso

| Clase | Descripción | Ejemplos |
|-------|-------------|----------|
| **MASTER/READ** | Maestros, solo lectura | `iva`, `rubro`, `deposito`, `bom` |
| **MASTER/WRITE** | Alta/modificación maestros | `articulo`, `cliente`, `proveedor` |
| **TRANSACTION/READ** | Comprobantes lectura | `comp_ped` SELECT, `recibo` |
| **TRANSACTION/WRITE** | Comprobantes escritura | `comp_ped`, `stockp`, `cuentacliente`, `cont_asiento` |
| **CONFIGURATION** | Estructura operativa | `sucursales`, `talonarios`, `punto_venta`, `codmov` |
| **IDENTITY** | Usuarios y permisos | `usuarios`, `permiso_sistema`, `puestos`, `sesion` |
| **ANALYTICS** | Solo SELECT | reports (1 write = seed) |
| **INTEGRATION** | Sync externo | tiendanube → `articulo`, `cliente`, `comp_ped` |

---

## Escrituras por módulo

| Módulo | Write refs | Tablas principales | Taxonomía dominante |
|--------|----------:|-------------------|---------------------|
| mpr | 239 | `stock`, `stock_deposito`, `movimiento_stock`, `lista_produccion*` | TRANSACTION/WRITE |
| core | 109 | `cuerpostock_mstock`, `usuarios`, `sucursales`, `stock_deposito` | MIXTO |
| ecom | 67 | `comp_ped`, `stockp`, `cuentacliente`, `caja`, `cliente` | TRANSACTION/WRITE |
| self_checkout | 58 | `cuentacliente`, `talonarios`, `punto_venta`, `stock` | TRANSACTION/WRITE |
| legacy_db | 41 | `cont_asiento`, `cont_ejercicio_saldo_cta` | TRANSACTION/WRITE |
| tiendanube_administranet | 28 | `articulo`, `cliente`, `comp_ped`, `stockp` | INTEGRATION + TRANSACTION |
| ventas | 11 | `comp_ped`, `stockp` | TRANSACTION/WRITE |
| mercadopago | 9 | `mercadopago_transaction`, `caja` | TRANSACTION/WRITE |
| fe_afip | 5 | `cuentacliente`, `imputacion` | TRANSACTION/WRITE |
| stock | 4 | `cuerpostock_mstock` | TRANSACTION/WRITE |
| login | 4 | `sesion`, `viajantes` | IDENTITY |
| logistica | 3 | `comp_ped` | TRANSACTION/WRITE |
| factura_compra_captura | 2 | `proveedor` | MASTER/WRITE |
| reports | 1 | seed artifact | — |

---

## Inventario detallado — tablas de alto impacto

### WR-001 — `articulo` (MASTER/WRITE, SHARED)

| Campo | Valor |
|-------|-------|
| **Module** | core, mpr, tiendanube |
| **File** | `core/services/administranet_articulo.py` |
| **Function** | `crear_articulo`, `completar_campos_alta_articulo` |
| **Lines** | 392 INSERT, 481 UPDATE |
| **Operation** | INSERT, UPDATE, DELETE |
| **Trigger** | User API / integration |
| **Tenant check** | `base_empresa` vía pool |
| **Permission** | `@tiene_permiso` en views |
| **Side effects** | `stock_deposito` INSERT en alta |
| **AN dependency** | Schema VB6 articulo |
| **Risk** | HIGH — maestro compartido VB6+Synap |
| **Future ownership** | ERP MasterDataPort |

### WR-002 — `cliente` (MASTER/WRITE, SHARED)

| Campo | Valor |
|-------|-------|
| **Module** | ecom, self_checkout, tiendanube |
| **File** | `ecom/services/cliente_rapido_escritura.py:123,212` |
| **Operation** | INSERT, UPDATE |
| **Trigger** | User checkout / TN webhook |
| **Tenant check** | session `base_empresa` |
| **Risk** | HIGH |
| **Future ownership** | CustomerPort |

### WR-003 — `comp_ped` (TRANSACTION/WRITE, SHARED)

| Campo | Valor |
|-------|-------|
| **Module** | ecom, mpr, logistica, ventas, tiendanube |
| **File** | `ecom/services/mayorista_checkout_service.py:758` |
| **File** | `mpr/best_migration/pedido_loader.py:421,472` |
| **Operation** | INSERT, UPDATE |
| **Trigger** | User checkout, BEST migration, TN order |
| **Transaction** | `get_connection` + commit |
| **Risk** | **CRITICAL** — pedido core negocio |
| **Future ownership** | SalesOrderPort |

### WR-004 — `stock` / `stock_deposito` / `stockp` (TRANSACTION/WRITE, SHARED)

| Campo | Valor |
|-------|-------|
| **Module** | mpr (46+ via `{tbl_stock}`), core, ecom, self_checkout |
| **File** | `mpr/services.py` (dinámico), `core/services/administranet_stock.py` |
| **Operation** | INSERT, UPDATE |
| **Trigger** | Producción MPR, checkout, TPV, compras |
| **Risk** | **CRITICAL** — concurrencia VB6 |
| **Future ownership** | InventoryPort |

### WR-005 — `cont_asiento` (TRANSACTION/WRITE, SHARED)

| Campo | Valor |
|-------|-------|
| **Module** | legacy_db, ecom |
| **File** | `legacy_db/services/cont_recalculo_service.py` |
| **Lines** | 3056 INSERT, 437 UPDATE, 3639 UPDATE |
| **Operation** | INSERT, UPDATE, DELETE |
| **Trigger** | Job recálculo contable, recibo ecom |
| **Risk** | **CRITICAL** — integridad contable |
| **Future ownership** | AccountingPort |

### WR-006 — `cuentacliente` (TRANSACTION/WRITE, SHARED)

| Campo | Valor |
|-------|-------|
| **Module** | self_checkout, ecom, fe_afip, tiendanube |
| **File** | `self_checkout/services/confirmation_service.py:388,793` |
| **Operation** | INSERT, UPDATE |
| **Trigger** | TPV confirmación, recibos |
| **Risk** | HIGH |
| **Future ownership** | AccountsReceivablePort |

### WR-007 — `usuarios` (IDENTITY, SHARED)

| Campo | Valor |
|-------|-------|
| **Module** | core |
| **File** | `core/services/administranet_users.py:360,516,555` |
| **Operation** | INSERT, UPDATE (soft delete) |
| **Trigger** | Admin UI usuarios |
| **Risk** | HIGH — IdP coupling |
| **Future ownership** | IdentityPort (o Synap-native) |

### WR-008 — `sucursales` (CONFIGURATION, SHARED)

| Campo | Valor |
|-------|-------|
| **Module** | core |
| **File** | `core/services/administranet_sucursales.py:538,598+` |
| **Operation** | INSERT, UPDATE |
| **Future ownership** | OrganizationPort |

### WR-009 — `compventa` — **SIN ESCRITURAS**

| Campo | Valor |
|-------|-------|
| **Verificación** | 0 matches INSERT/UPDATE/DELETE en .py |
| **Nota** | TPV escribe `resumen_venta_cv`, `tc_comprobante`, `stock`, `cuentacliente` |
| **Evidencia** | `self_checkout/services/confirmation_service.py:529-709` |
| **Impacto** | Refuta supuesto V1 sobre modelo facturación TPV |

---

## Concentración por archivo

| Archivo | Write refs | Dominio |
|---------|----------:|---------|
| `mpr/services.py` | 222 | Producción / stock |
| `core/services/administranet_stock.py` | 44 | Stock / movimientos |
| `legacy_db/services/cont_recalculo_service.py` | 28 | Contabilidad |
| `core/services/administranet_compras.py` | 20 | Compras |
| `self_checkout/services/confirmation_service.py` | 17 | TPV |
| `ecom/services/mayorista_checkout_service.py` | 12 | Pedidos mayorista |

---

## Respuesta a la pregunta clave

> ¿Qué operaciones de negocio ejecuta Synap directamente sobre el modelo transaccional de AdministraNET?

| Capacidad | Operaciones | Módulos |
|-----------|-------------|---------|
| Crear/modificar pedidos | INSERT/UPDATE `comp_ped`, `stockp` | ecom, mpr, ventas, TN |
| Confirmar venta TPV | INSERT `cuentacliente`, UPDATE `stock`, INSERT `resumen_venta_cv` | self_checkout |
| Movimientos stock | UPDATE/INSERT `stock`, `stock_deposito`, `movimiento_stock` | mpr, core, ecom |
| Recibos y caja | INSERT `caja`, `cuentacliente`, `recibo_factura*` | ecom, TN, mercadopago |
| Contabilidad | INSERT/UPDATE/DELETE `cont_asiento`, saldos | legacy_db, ecom |
| Maestros | INSERT/UPDATE `articulo`, `cliente` | core, ecom, TN |
| Usuarios/sucursales | INSERT/UPDATE `usuarios`, `sucursales` | core |
| Sesión | INSERT `sesion` | login |

---

## Riesgos transversales

1. **Dual-write VB6+Synap** en `stockp`, `stock_deposito` sin locking distribuido documentado.
2. **Archivos duplicados** (`* 2.py`) duplican superficie de escritura.
3. **Management commands** con `--apply` (contabilidad, BOM) son herramientas operativas sin RBAC uniforme.
4. **Transacciones mixtas** PG+MySQL sin 2PC — inconsistencia posible en fallos parciales.

---

*Ver ownership en `03-DATA-OWNERSHIP-BOUNDARIES.md`. Ports en `05-PORTS-CATALOG.md`.*
