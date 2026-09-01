# 12 — Synap Product Boundary

**Estado:** COMPLETE  
**Fecha:** 25/08/2026

---

## ¿Qué es Synap?

**Evidencia-based definition:**

Synap es una **plataforma web modular** que extiende AdministraNET con capacidades que VB6 no soporta bien, usando PostgreSQL para estado propio y MySQL para operaciones ERP, con autenticación y permisos heredados del ERP.

**No es (hoy):** ERP independiente, SaaS multi-tenant, producto con IdP propio.

**Puede ser (futuro):** Plataforma con Ports/adapters donde AdministraNET es un backend opcional.

---

## Clasificación de capacidades

### SYNAP CORE (plataforma)

| Capacidad | Evidencia | Estado |
|-----------|-----------|--------|
| Module registry & activation | `core/module_registry.py`, `ModuleConfig` | Operativo |
| MySQL connection pool | `core/mysql_pool.py` | Operativo |
| Session & request middleware | `core/middleware/` | Operativo |
| Permission framework | `core/decorators.py`, `synap_permisos.py` | Operativo — acoplado AN |
| Legacy schema migration tool | `legacy_mysql_schema/catalog.py` | Operativo |
| Backup subsystem | `core/backup/` | Operativo |
| Global search APIs | `core/api/views.py` | Operativo |
| UI shell / context processors | `core/context_processors.py` | Operativo |

**Problema:** Core contiene lógica dominio (stock, usuarios, sucursales) — boundary violada.

### SYNAP DOMAIN MODULE (instalables)

| Módulo | Capacidad negocio | Dependencia ERP |
|--------|-------------------|-----------------|
| reports | Informes y dashboards | READ heavy MySQL |
| ecom | Pedidos, mayorista, catálogo | WRITE transaccional |
| mpr | Producción, OPT, armado | WRITE stock + mpr_* |
| self_checkout | TPV / self-checkout | WRITE venta + stock |
| stock | Inventario físico | WRITE stock |
| ventas | Presupuestos | WRITE comp_ped |
| factura_compra_captura | Captura documentos compra | PG native + posting |
| contabilidad_audit | Auditoría contable | READ + checks |
| logistica | Entregas | UPDATE comp_ped |
| tiendanube_administranet | Sync e-commerce | WRITE integration |
| fe_afip | Facturación electrónica AR | WRITE + AFIP |
| ia | Agentes IA | PG + LLM external |

### SYNAP DATA PLATFORM

| Componente | Synap-native | ERP coupling |
|------------|:------------:|:------------:|
| ReportDefinition/Widget/Dashboard | ✓ PG | Execution → MySQL |
| LearnedRelationship | ✓ PG | Table names AN |
| SemanticService / information_schema | — | MySQL only |
| AgentDefinition / conversations | ✓ PG | Tools may query MySQL |
| Monthly reporting packs | ✓ PG | Import .xlsb |

### SYNAP INTEGRATION

| Integración | Tipo |
|-------------|------|
| AdministraNET MySQL | **Primary ERP** — no es "integración", es backbone |
| Tienda Nube | Webhooks + sync |
| AFIP | WS FE |
| Azure SQL BEST | Read-only migration |
| Odoo | Migration tooling only |
| PHP relays (ecom) | HTTP → administraNET-ecom |
| OpenAI/Anthropic | LLM APIs |
| Support RAG | Separate stack |

### ERP PROVIDED (delegar al adapter)

- Stock quantities & movements
- Sales orders & invoicing (AN model)
- Accounting entries
- Master data (articulo, cliente, proveedor) — escritura
- Cash register / treasury
- Tax catalog (IVA)

### LEGACY COMPATIBILITY

| Item | Razón |
|------|-------|
| `permiso_sistema` legacy mode | VB6 permisos hasta cutover synap |
| PHP relays ecom | VB6 business rules not replicated |
| AES password VB6 | Auth compatibility |
| latin1 charset | VB6 schema |
| `resumen_venta_cv` vs compventa | VB6 TPV model divergence |

### REMOVE / DEPRECATE (candidatos)

| Item | Evidencia |
|------|-----------|
| Código muerto query_runner post-return | `query_runner.py:~3840+` |
| Archivos `* 2.py` duplicados | repo-wide |
| Google OAuth stubs | No implementado |
| Celery tasks sin worker | TN tasks orphaned |
| `UsuarioExtendido` Firebase path | Legacy no primario |
| Dashboard stub `/dashboard/` legacy | Si sin consumidores |

---

## Respuesta pregunta 30

> ¿Qué es exactamente Synap como producto?

**Hoy:** Plataforma de extensión web AdministraNET con módulos de reporting, comercio, producción, TPV, IA e integraciones.

**Frontera producto objetivo (evidencia-supported):**
- **Synap owns:** UX web, workflows modernos, analytics metadata, IA, integraciones externas, captura documentos.
- **ERP owns:** Libros contables, stock ledger, maestros transaccionales, identidad operativa.
- **Boundary:** Ports entre ambos — no repositorios de tablas.

---

*Seams en `13-LEGACY-EXTRACTION-SEAMS.md`. Contrato en `SYNAP-ARCHITECTURE-CONTRACT.md`.*
