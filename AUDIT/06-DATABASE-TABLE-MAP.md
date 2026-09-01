# 06 — Mapa de Tablas y Ownership

**Estado:** COMPLETE (Fase 6)  
**Fecha:** 25/08/2026

---

## Clasificación de ownership

| Categoría | Descripción | Ejemplos |
|-----------|-------------|---------|
| **SYNAP OWNED** | Synap es sistema de registro; DDL en `*/sql/` o `catalog.py` | `synap_*`, `mpr_*`, `self_checkout_*`, `inv_fisico_*`, tablas PG `reports_*`, `ia_*` |
| **ADMINISTRANET OWNED** | VB6 es sistema de registro; Synap lee (escritura rara o inexistente) | `iva`, `rubro`, `deposito`, `bom`, `remito`, `recibo`, `configuracion` |
| **SHARED** | Tabla VB6 original con escritura activa desde Synap | `articulo`, `cliente`, `comp_ped`, `stock*`, `cont_asiento`, `usuarios` |
| **DERIVED** | Calculado/cacheado, no fuente de verdad | Vistas dinámicas reports, `*_temp`, `fact_temporalp` |
| **CACHE** | Temporal | Redis keys, in-memory dicts |
| **UNKNOWN** | Referenciada en SQL sin doc en `docs/general/tablas/` | Requiere validación por empresa |

---

## PostgreSQL — Tablas SYNAP OWNED

| Tabla (db_table) | App | R/W Synap | R/W VB6 |
|------------------|-----|:---------:|:-------:|
| `core_empresa` | core | R+W | — |
| `core_usuarioextendido` | core | R+W | — |
| `core_rol`, `core_permiso` | core | R+W | — |
| `core_moduleconfig` | core | R+W | — |
| `core_backupsettings`, `core_backupjob` | core | R+W | — |
| `reports_reportdefinition` | reports | R+W | — |
| `reports_reportdashboard` | reports | R+W | — |
| `reports_reportwidget` | reports | R+W | — |
| `reports_reportexecutionlog` | reports | R+W | — |
| `reports_learnedrelationship` | reports | R+W | — |
| `ia_llmproviderconfig` | ia | R+W | — |
| `ia_agentdefinition` | ia | R+W | — |
| `ia_agentconversation` | ia | R+W | — |
| `mpr_opt`, `mpr_parte` | mpr | R+W | — |
| `ecom_ecomcart` | ecom | R+W | — |
| `factura_compra_captura_*` | captura | R+W | — |
| `contabilidad_audit_*` | contabilidad | R+W | — |
| `tiendanube_*` | tiendanube | R+W | — |
| `odoo_migracion_*` | odoo | R+W | — |
| `fe_afip_*` | fe_afip | R+W | — |

---

## MySQL — Tablas SYNAP OWNED (DDL propio)

Creadas por Synap en MySQL de empresa; no existen en VB6 original.

| Prefijo / tabla | DDL fuente | Apps que escriben |
|-----------------|------------|-------------------|
| `synap_permiso`, `synap_rol`, `synap_rol_permiso`, `synap_puesto_rol` | `core/sql/001_synap_permisos_tables.sql` | core |
| `mpr_*` (~20 tablas) | `mpr/sql/001_mpr_core_tables.sql`, `003_`, `006_`, `007_` | mpr |
| `self_checkout_*` (8 tablas) | `self_checkout/sql/001_self_checkout_tables.sql`, `008_` | self_checkout |
| `inv_fisico_campana`, `inv_fisico_linea`, `inv_fisico_evento`, `inv_fisico_ajuste_auditoria` | `stock/sql/001_`, `002_` | stock |
| `ecom_vendedor_cliente_marca`, `ecom_usuario_viajante` | `ecom/sql/001_ecom_vendedor_cliente_marca.sql` | ecom |
| `cont_audit_correccion_lote`, `cont_audit_correccion` | `contabilidad_audit/sql/cont_audit_correccion_log.sql` | contabilidad_audit |
| `cotizacion_historial` | `contabilidad_audit/sql/cotizacion_historial.sql` | core |

Catálogo central de migraciones: `core/services/legacy_mysql_schema/catalog.py` (proveedores `synap_permisos_tables`, `mpr_core_tables`, `self_checkout_core_tables`, etc.).

---

## MySQL — Tablas ADMINISTRANET OWNED (lectura principal)

Documentadas en `docs/general/tablas/` (~400+ archivos). Synap lee; escritura limitada o inexistente.

| Tabla | Apps que leen | Apps que escriben |
|-------|---------------|-------------------|
| `iva` | core, ecom, legacy_db, mpr, reports, self_checkout, tiendanube, ventas | — |
| `rubro`, `marca` | ecom, reports, tiendanube, ventas | — |
| `deposito` | core, ecom, mpr, reports, self_checkout, stock, tiendanube | — |
| `bom` | contabilidad_audit, core, mpr, reports | — |
| `remito`, `recibo` | core, ecom, mpr, reports, tiendanube | — |
| `lista_precio` | core, ecom, mpr, reports, self_checkout, tiendanube | — |
| `configuracion` | contabilidad_audit, core, ecom, self_checkout | — |
| `proveedor` | core, ecom, legacy_db, mpr, reports, tiendanube, ventas | — (lectura dominante) |
| `empresas` | login | — |
| `permiso_sistema` | ecom | core, self_checkout (seeds) |
| `puestos` | ecom, login | core |
| `viajantes` | core, ecom, reports, self_checkout, stock, ventas | login |
| `movstock` | core | — |
| `reglas_precio` | ecom | — |

---

## MySQL — Tablas SHARED (VB6 original + escritura Synap)

| Tabla | Lectura (apps) | Escritura (apps) | Evidencia write |
|-------|----------------|------------------|-----------------|
| `articulo` | ecom, reports, stock, ventas, self_checkout, legacy_db | **core, mpr, tiendanube** | `core/services/administranet_stock.py` |
| `cliente` | core, mpr, reports, stock, ventas, legacy_db, login | **ecom, self_checkout, tiendanube** | `ecom/services/cliente_rapido_escritura.py` |
| `comp_ped` | core, reports | **ecom, mpr, tiendanube, ventas** | `mpr/best_migration/pedido_loader.py:421` |
| `cuentacliente` | contabilidad_audit, legacy_db, reports, ventas | **ecom, self_checkout, tiendanube** | `self_checkout/services/confirmation_service.py` |
| `stock` / `stock_deposito` / `stockp` | reports, stock, ecom | **core, mpr, self_checkout, ecom, tiendanube** | `core/services/administranet_stock.py` |
| `cont_asiento` | contabilidad_audit, core | **ecom, legacy_db** | `legacy_db/services/cont_recalculo_service.py` |
| `caja` | core, legacy_db, reports, self_checkout | **ecom, tiendanube** | relays ecom |
| `punto_venta` | core, ecom, legacy_db, reports, tiendanube | **self_checkout** | `self_checkout/services/pv_service.py` |
| `usuarios` | ecom, login, mpr, reports, stock, tiendanube | **core** | `core/services/administranet_users.py` |
| `sucursales` | contabilidad_audit, ecom, legacy_db, reports, self_checkout | **core** | `core/services/administranet_sucursales.py` |
| `serie_entrada` | — | **core, self_checkout** | stock/series |
| `cuerpostock_mstock` | — | **core, stock** | `stock/services/inventario_fisico.py` |
| `compventa` / `cuerpocompventa` | self_checkout, reports | self_checkout | TPV |
| `cuentaproveedor` | reports, compras, legacy_db | legacy_db | — |
| `talonarios` | self_checkout, mpr, core | self_checkout, mpr | — |

---

## Tablas MySQL por app consumidora

| App | ~Tablas únicas | Tablas principales |
|-----|---------------:|-------------------|
| **core** | 80+ | `articulo`, `stock*`, `deposito`, `usuarios`, `sucursales`, `synap_*`, `configuracion`, `cont_asiento` |
| **reports** | 60+ | `comp_ped`, `cliente`, `cuentacliente`, `articulo`, `stock*`, `caja`, `cont_asiento`, `iva`, `rubro` |
| **ecom** | 55+ | `comp_ped`, `cliente`, `cuentacliente`, `articulo`, `caja`, `ecom_*`, `lista_precio` |
| **mpr** | 45+ | `mpr_*`, `comp_ped`, `stock*`, `articulo`, `bom` |
| **self_checkout** | 35+ | `self_checkout_*`, `cliente`, `cuentacliente`, `stock*`, `caja`, `punto_venta` |
| **stock** | 15+ | `inv_fisico_*`, `stock_deposito`, `cuerpostock_mstock` |
| **ventas** | 20+ | `comp_ped`, `stockp`, `cliente`, `viajantes_objetivos_*` |
| **legacy_db** | 15+ | `cont_asiento`, `proveedor`, `sucursales`, `punto_venta`, `cliente` |
| **tiendanube_administranet** | 25+ | `cliente`, `comp_ped`, `stock*`, `caja`, `articulo`, `rubro` |
| **login** | 8 | `usuarios`, `viajantes`, `puestos`, `sesion` |
| **contabilidad_audit** | 10 | `cont_asiento`, `sucursales`, `punto_venta`, `configuracion` |

---

## Tablas con mayor riesgo de escritura concurrente VB6+Synap

| Tabla | Escritores Synap | Escritores VB6 | Riesgo |
|-------|-----------------|----------------|:------:|
| `stockp` | stock, mpr, core, self_checkout | VB6 ventas/compras | **4** |
| `stock_deposito` | stock, mpr, core | VB6 | **4** |
| `compventa` | self_checkout | VB6 TPV | **3** |
| `cont_asiento` | legacy_db | VB6 contabilidad | **3** |
| `talonarios` | self_checkout, mpr | VB6 | **3** |
| `articulo` | core (unificar BOM) | VB6 maestros | **2** |

---

## Resumen por base de datos

| Base | Tablas Synap-owned | Tablas AdministraNET | Tablas Shared |
|------|-------------------:|---------------------:|:-------------:|
| PostgreSQL | **132 modelos** (~100+ tablas migradas) | 0 | 0 |
| MySQL (por empresa) | ~30 (`synap_*`, `mpr_*`, `sc_*`, `inv_fisico_*`, `ecom_*`) | ~200+ | ~15 tablas VB6 con write Synap |

**Limitaciones del escaneo:** conteos por regex sobre strings SQL (no AST); archivos `* 2.py` excluidos pero presentes en repo; `support/backend/` tiene modelos PG propios pero no está en `INSTALLED_APPS`.

---

*Linaje de datos por proceso en `07-DATA-LINEAGE.md`.*
