# 03 — Client Installation Matrix

**Estado:** COMPLETE | Identificadores neutros — evidencia en código y docs

---

## Identificación de clientes

| ID | Identidad real | MySQL `base_empresa` | Deployment típico |
|----|----------------|---------------------|-------------------|
| **CLIENT-A** | DABRA (mayorista) | `administranet89` | Synap Staging servers |
| **CLIENT-B** | Best Sox / BEST (manufactura) | `administranet`, `administranet92` (UAT) | Synap Staging servers |

**Nota:** No hay branching `if cliente` en Python de producción. La instalación se distingue por `.env` + estado DB + login `base_empresa`.

---

## CLIENT-A — DABRA

| Dimensión | Estado |
|-----------|--------|
| **Modules installed** | core, login, ecom, stock, reports, contabilidad_audit, ventas (parcial), self_checkout (si activo), fe_afip |
| **Modules NOT typical** | mpr (limitado), odoo_migracion, migracion-best |
| **Capabilities CRITICAL** | Pedidos mayorista, hub kanban, reports dashboards, auditoría contable piloto |
| **Capabilities HIGH** | Stock consulta, pedido masivo, export reportes |
| **Integrations** | AdministraNET MySQL; AFIP si FE activa |
| **Custom code** | `dabra-consolidado-remitos` report (CODIGO_CLIENTE=368) |
| **Custom config** | `SYNAP_PILOTO_CONT`, `configuracion_ecom` por base |
| **Reports seeds** | dabra-consolidado-remitos, reportes genéricos |
| **Workflows daily** | WF-02 pedidos, WF-07 reports, WF-09 auditoría |
| **Artifacts** | PDF pedidos, XLSX export reports, auditoría export |
| **Jobs** | contabilidad audit runs, mail queue ecom |

---

## CLIENT-B — Best Sox

| Dimensión | Estado |
|-----------|--------|
| **Modules installed** | core, login, mpr, stock, ecom, reports, ventas, self_checkout, tiendanube_administranet, odoo_migracion |
| **Modules HIGH use** | mpr (109 templates), reports (VMM, licenciatarios, BOM docenas) |
| **Capabilities CRITICAL** | Producción OPT (WF-04), parte operario (WF-05), pedidos, stock, TPV |
| **Capabilities HIGH** | Reports mensuales licenciatarios, migración BEST, TN sync |
| **Integrations** | Azure SQL BEST (read), AdministraNET MySQL, Tienda Nube, AFIP |
| **Custom code** | migracion-best routes, `_MARCA_ALIAS`, monthly reporting Best Sox templates |
| **Custom config** | `BEST_AZURE_*`, `MprEmpresaConfig`, `configuracion_ecom` |
| **Reports seeds** | ventas-marcas-mensual, ventas-mensuales-licenciatarios, ventas-bom-docenas |
| **Workflows daily** | WF-04, WF-05, WF-06 TPV, WF-02 pedidos, WF-07 reports |
| **Artifacts** | PDF OPT, ticket TPV, XLSX monthly pack, CSV MPR |

---

## Matriz comparativa

| Capability | CLIENT-A | CLIENT-B | Común |
|------------|:--------:|:--------:|:-----:|
| Login / sesión | CRITICAL | CRITICAL | ✅ |
| Pedidos mayorista | CRITICAL | CRITICAL | ✅ |
| Hub pedidos kanban | CRITICAL | HIGH | ✅ |
| Pedido masivo Excel | HIGH | MEDIUM | ✅ |
| Stock movimientos | HIGH | CRITICAL | ✅ |
| Inventario físico móvil | MEDIUM | HIGH | ✅ |
| Producción MPR | LOW/— | **CRITICAL** | ❌ |
| Parte operario móvil | — | **CRITICAL** | ❌ |
| TPV self-checkout | MEDIUM | **CRITICAL** | ✅ |
| Reports dashboards | CRITICAL | CRITICAL | ✅ |
| Report DABRA consolidado | **CRITICAL** | — | ❌ |
| Reports VMM/licenciatarios | — | **CRITICAL** | ❌ |
| Migración BEST | — | HIGH | ❌ |
| Auditoría contable | **CRITICAL** | LOW | ❌ |
| Tienda Nube | LOW | HIGH | ⚠️ |
| Captura factura compra | MEDIUM | MEDIUM | ✅ |
| Odoo migración | — | MEDIUM | ❌ |
| IA asistente | LOW | LOW | ✅ |

---

## Modelo de instalación actual (implícito)

```text
SynapDeployment (1 por servidor .env)
├── DB_NAME → default base_empresa
├── ModuleConfig (Postgres) → módulos activos
├── SystemConfiguration → flags runtime
├── MySQL base(s) → datos ERP por empresa login
└── ReportDefinition seeds → reportes instalados
```

**Gap:** No existe entidad `SynapInstallation` formal — ver propuesta en `SYNAP-V2-PRODUCT-BASELINE.md`.

---

*Evidence: subagent client audit, `docs/general/INFORME_DESARROLLO_FUNCIONAL_CLIENTE.md`, `docs/reports/INFORME_DABRA_CONSOLIDADO_REMITOS.md`, `docs/mpr/BEST_SOX_ITERACION1_VALIDACION.md`*
