# 04 — Mapa de Capacidades ERP

**Estado:** COMPLETE  
**Fecha:** 25/08/2026

---

## Capacidades identificadas desde código

| Capability | Current implementation | Tables involved | Synap modules | Read | Write | Business rules | AN-specific semantics | Portability | Future Port |
|------------|---------------------|-----------------|:-------------:|:----:|:-----:|----------------|----------------------|:-----------:|-------------|
| **Customer Management** | SQL directo + relays PHP | `cliente`, `cliente_domicilio`, `cliente_contacto` | ecom, sc, TN, reports | ✓ | ✓ | CUIT validation, saldo | `Codigo` PK legacy | MEDIUM | `CustomerPort` |
| **Product Catalog** | `administranet_articulo.py` | `articulo`, `rubro`, `bom` | core, ecom, mpr, TN | ✓ | ✓ | BOM ensamblados, codbarra | `IDArt` int, fechas INT | LOW | `ProductCatalogPort` |
| **Pricing** | Relays + `stockp` | `lista_precio`, `stockp`, `reglas_precio` | ecom, ventas | ✓ | ✓ | Listas por cliente/marca | Precio en múltiples tablas | LOW | `PricingPort` |
| **Inventory / Stock** | `administranet_stock.py`, `mpr/services.py` | `stock`, `stock_deposito`, `stockp`, `movimiento_stock` | mpr, core, ecom, sc, stock | ✓ | ✓ | Reserva, depósito, lote | `saldo_pedido_cliente` reserva | **VERY LOW** | `InventoryPort` |
| **Sales Orders** | Checkout services | `comp_ped`, `cuerpo_comp_ped`, `stockp` | ecom, mpr, ventas, TN, logistica | ✓ | ✓ | Aprobación crédito, estados | Estados VB6 específicos | LOW | `SalesOrderPort` |
| **POS / Retail Sale** | `confirmation_service.py` | `resumen_venta_cv`, `stock`, `cuentacliente`, `tc_comprobante` | self_checkout | ✓ | ✓ | FE integration | **No usa compventa** | LOW | `PointOfSalePort` |
| **Invoicing / FE** | `fe_afip`, invoice_service | `cuentacliente`, CAE tables | fe_afip, sc | ✓ | ✓ | AFIP WS, tipos comprobante | Argentina-specific | NONE (AR) | `ElectronicInvoicingPort` |
| **Accounts Receivable** | Recibo services | `cuentacliente`, `recibo_factura*`, `imputacion` | ecom, sc, TN | ✓ | ✓ | Imputación facturas | Numeración talonarios | LOW | `AccountsReceivablePort` |
| **Accounts Payable** | legacy_db, captura | `cuentaproveedor`, `proveedor` | legacy_db, captura | ✓ | Limited | — | — | MEDIUM | `AccountsPayablePort` |
| **Cash Register** | Caja services | `caja`, `caja_saldo`, `codmov` | ecom, sc, TN, mercadopago | ✓ | ✓ | Cierre caja VB6 | `codmov` secuencia | LOW | `CashManagementPort` |
| **Accounting** | `cont_recalculo_service.py` | `cont_asiento`, `cont_detalle`, saldos | legacy_db, contabilidad_audit, ecom | ✓ | ✓ | REI, ejercicios | Plan cuentas AN | **NONE** | `AccountingPort` |
| **Tax** | Catálogo `iva` | `iva`, percepciones | fe_afip, all | ✓ | — | IVA Argentina | Alícuotas fijas | LOW | `TaxPort` |
| **Users** | `administranet_users.py` | `usuarios` | core, login | ✓ | ✓ | AES password VB6 | `cod_usuario` lowercase | MEDIUM | `IdentityPort` |
| **Permissions** | synap + permiso_sistema | `synap_*`, `permiso_sistema*` | core | ✓ | ✓ | Puesto-based | Clavemenu VB6 mapping | MEDIUM | `AuthorizationPort` |
| **Organization** | sucursales service | `sucursales`, `punto_venta`, `deposito` | core, sc | ✓ | ✓ (sucursales) | PV por sucursal | — | MEDIUM | `OrganizationPort` |
| **Production (MPR)** | `mpr/services.py` | `mpr_*` (Synap) + `stock*` (AN) | mpr | ✓ | ✓ | OPT, armado, partes | Lista producción VB6-like | LOW | `ProductionPort` |
| **Logistics** | lista comprobantes | `comp_ped` (entrega) | logistica | ✓ | ✓ | Rutas, entregas | — | MEDIUM | `LogisticsPort` |
| **E-commerce integration** | adminet_service | múltiples SHARED | tiendanube | ✓ | ✓ | Sync bidireccional | Mappings TN↔AN | LOW | `CommerceIntegrationPort` |

---

## Capacidades read-only (ANALYTICS)

| Capability | Modules | Tables | Notes |
|------------|---------|--------|-------|
| Executive dashboards | reports | `caja`, `comp_ped`, `cliente`, … | SQL en `executive_dashboard/` |
| Operational reports | reports | 60+ tablas | query_runner + runners |
| Contabilidad audit read | contabilidad_audit | `cont_asiento` | Checks sin write |

---

## Adapter viability assessment

### AdministraNETAdapter

| Aspect | Assessment |
|--------|------------|
| **Viability** | **HIGH** — mismo schema ya usado |
| **Effort** | HIGH — 587 write paths to wrap |
| **Blockers** | Reglas VB6 implícitas en SQL disperso |

### OdooAdapter

| Capability | Odoo mapping | Semantic gap |
|------------|--------------|--------------|
| Inventory | `stock.quant` | Reserva `saldo_pedido_cliente` no 1:1 |
| Sales Order | `sale.order` | Estados comp_ped custom |
| Accounting | `account.move` | Plan cuentas distinto |
| POS | `pos.order` | resumen_venta_cv sin equivalente directo |
| **Overall viability** | **MEDIUM-LOW** | Contabilidad + stock semantics |

### NativeSynapAdapter

| Capability | Native candidate | Prerequisite |
|------------|-----------------|--------------|
| Reports metadata | ✓ Already PG | — |
| AI | ✓ Already PG | — |
| Captura documentos | ✓ Already PG | Posting via AccountingPort |
| Stock/Orders | ✗ Not viable short-term | Full ERP replacement |

---

## AdapterCapabilities (conceptual)

```text
supports_inventory_reservation:     AdministraNET=YES, Odoo=PARTIAL, Native=NO
supports_native_accounting:         AdministraNET=YES, Odoo=YES, Native=NO
supports_purchase_orders:           AdministraNET=YES, Odoo=YES, Native=NO
supports_tax_engine_ar:             AdministraNET=YES, Odoo=PARTIAL, Native=NO
supports_multi_warehouse:           AdministraNET=YES, Odoo=YES, Native=NO
supports_pos_retail:                AdministraNET=YES (resumen_venta_cv), Odoo=YES, Native=NO
supports_production_orders:         AdministraNET=PARTIAL (mpr_*), Odoo=YES, Native=NO
supports_reporting_metadata:        AdministraNET=N/A, Odoo=N/A, Native=YES
```

---

*Ports derivados en `05-PORTS-CATALOG.md`.*
