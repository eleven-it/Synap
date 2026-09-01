# 11 — Change Impact Matrix

**Estado:** COMPLETE  
**Fecha:** 25/08/2026

---

## Componentes críticos

### CI-01: `core.mysql_pool` / RequestScopedMysqlMiddleware

| Campo | Valor |
|-------|-------|
| **Direct deps** | ALL apps con MySQL |
| **Indirect** | Cada request autenticado |
| **Tables** | Todas MySQL |
| **APIs** | Todos endpoints que tocan AN |
| **Blast radius** | **TOTAL** — cambiar pool rompe todo |
| **Tests** | Parcial por módulo |

### CI-02: `session['user']` / AdministraNETUser

| Campo | Valor |
|-------|-------|
| **Direct deps** | login, core middleware, all @tiene_permiso |
| **Indirect** | mysql_pool base_empresa selection |
| **Blast radius** | **TOTAL** auth + tenant MySQL |
| **If changed** | Rompe login, permisos, reports filters |

### CI-03: `core/services/administranet_stock.py`

| Campo | Valor |
|-------|-------|
| **Consumers** | stock, mpr, self_checkout, ecom (indirect) |
| **Tables** | stock, stock_deposito, movimiento_stock, cuerpostock* |
| **Write refs** | 44 |
| **Blast radius** | HIGH — inventario transaccional |
| **Refactor target** | InventoryPort adapter |

### CI-04: `mpr/services.py`

| Campo | Valor |
|-------|-------|
| **Write refs** | 222 |
| **Tables** | stock*, lista_produccion*, mpr_* |
| **Blast radius** | HIGH — producción + stock |
| **Coupling** | stock module imports |

### CI-05: `reports/services/query_runner.py`

| Campo | Valor |
|-------|-------|
| **Consumers** | reports UI, API, ia report intent |
| **Tables** | 60+ read |
| **Blast radius** | MEDIUM-HIGH — analytics only |
| **Note** | No transaccional |

### CI-06: `legacy_db/services/cont_recalculo_service.py`

| Campo | Valor |
|-------|-------|
| **Tables** | cont_asiento, saldos |
| **Blast radius** | **CRITICAL** — integridad contable |
| **Business** | Cierre ejercicio, REI |

### CI-07: `login/administranet_auth.py`

| Campo | Valor |
|-------|-------|
| **Blast radius** | TOTAL — sin auth no hay sistema |
| **External** | MySQL empresas + usuarios |

### CI-08: `SYNAP_PERMISOS_SOURCE` / permisos

| Campo | Valor |
|-------|-------|
| **Blast radius** | TOTAL authorization |
| **Cutover risk** | Escalada / denegación masiva si mal configurado |

### CI-09: `factura_compra_captura` API

| Campo | Valor |
|-------|-------|
| **Blast radius** | LOW code; HIGH security |
| **Fix** | Añadir empresa filter — isolated change |

### CI-10: `core/services/legacy_mysql_schema/catalog.py`

| Campo | Valor |
|-------|-------|
| **Consumers** | setup commands, all DDL migrations |
| **Blast radius** | HIGH — schema todos los dominios |

---

## Matriz resumida

| Si cambio… | Se rompe… | Severidad |
|------------|-----------|-----------|
| mysql_pool API | Todo MySQL access | P0 |
| session structure | Auth, tenant, permisos | P0 |
| administranet_stock | mpr, sc, ecom checkout, stock | P0 |
| mpr/services stock paths | Producción + inventario | P0 |
| cont_recalculo | Contabilidad cliente | P0 |
| query_runner slug | Dashboards específicos | P1 |
| ReportDefinition schema | Builder + declarative reports | P1 |
| ModuleConfig | Module activation | P1 |
| ecom checkout service | Pedidos mayorista | P1 |

---

## Respuesta pregunta implícita

> Si desconecto AdministraNET MySQL, ¿qué se rompe?

**Todo excepto:** PG-only features (IA metadata, report definitions storage, WebAuthn prefs, TN config) — pero **sin login funcional** porque IdP es MySQL.

---

*Product boundary en `12-SYNAP-PRODUCT-BOUNDARY.md`.*
