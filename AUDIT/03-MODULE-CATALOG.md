# 03 — Catálogo de Módulos Synap

**Estado:** COMPLETE (Fase 3)  
**Fecha:** 25/08/2026  
**Alcance:** 20 apps en `INSTALLED_APPS` + 4 legacy/huérfanas

---

## Resumen

| Categoría | Apps | Acceso MySQL | Modelos PG |
|-----------|-----:|:------------:|:----------:|
| Núcleo transversal | core, login, theme | Sí / Sí | Sí |
| Informes y analítica | reports, ia | Sí | Sí |
| Operaciones comerciales | ecom, ventas, self_checkout, stock, compras | Sí | Parcial |
| Producción | mpr | Sí (intenso) | Sí |
| Finanzas / fiscal | fe_afip, factura_compra_*, contabilidad_audit, legacy_db | Sí | Parcial |
| Integraciones | tiendanube_administranet, odoo_migracion | Sí | Sí |
| Logística | logistica | Sí | No |
| Legacy/stub | dashboard, factura_compra_posting | No / stub | Parcial |

---

## Módulo: core

| Atributo | Valor |
|----------|-------|
| **Path** | `core/` |
| **Estado** | Activo, requerido |
| **Tests** | 27 archivos |
| **Propósito** | Núcleo transversal: identidad, permisos, empresas, módulos, pool MySQL, backup DR, APIs búsqueda | CONFIRMADO POR CÓDIGO |

**Responsabilidad:** Infraestructura compartida de toda la plataforma. No es solo utilidades — contiene lógica de negocio (permisos, cotización BCRA, stock AdministraNET, DDL legacy).

**Entrada:** Sesión autenticada, requests HTTP, management commands.

**Salida:** Contexto global (menú, permisos), conexiones MySQL, APIs búsqueda, UI administración.

### Modelos propios (PostgreSQL)

`Empresa`, `Permiso`, `Rol`, `UsuarioExtendido`, `Branch`, `DeliveryLocation`, `Contact`, `Country`, `State`, `Currency`, `ExchangeRate`, `SystemConfiguration`, `ModuleConfig`, `NavbarMenuGlobal`, `FiscalResponsibility`, `CotizacionConfig`, `BackupSettings`, `BackupJob`, `BackupArtifact`

Fuente: `core/models/`, `core/backup/models.py`

### Tablas legacy utilizadas

Extensivo — `usuario`, `puestos`, `permiso_sistema*`, `synap_*`, `empresas`, `articulo`, `cliente`, `sucursales`, y cientos más vía servicios.

### APIs

- `/core/api/` — búsquedas (artículos, clientes, proveedores, geo)
- `/core/api/` DRF — usuarios, roles, branches (`views_api.py`)
- Rutas HTML — dashboard, usuarios, permisos, backup, schema MySQL

### Servicios clave

`mysql_pool.py`, `legacy_mysql_schema/catalog.py`, `administranet_permisos_usuario.py`, `administranet_stock.py`, `backup/services/orchestrator.py`

### Jobs

57 management commands (backup, permisos, schema, bootstrap)

### Dependencias internas

Ninguna (es el hub). Todas las apps dependen de core.

### Dependencias AdministraNET

**Críticas** — auth, permisos, pool MySQL, tipos `administranet_types`

### Riesgos

- Hub de acoplamiento universal
- Lógica de negocio mezclada con infraestructura
- Posible eclipse de `core.api.urls` por `core.urls`

---

## Módulo: login

| Atributo | Valor |
|----------|-------|
| **Path** | `login/` |
| **Tests** | 1 |
| **Propósito** | Autenticación contra MySQL AdministraNET, bootstrap sesión, WebAuthn | CONFIRMADO POR CÓDIGO |

**Modelos:** Credenciales WebAuthn (PostgreSQL)

**Tablas legacy:** `usuario`, `empresas` (catálogo), validación password AES AdministraNET

**Flujo:** `AdministraNETAuth.validate_user()` → `bootstrap_synap_session()` → `session["user"]`

**APIs:** `/login/` (form + AJAX), WebAuthn endpoints

**Dependencias:** core (mysql_pool), session store Django

---

## Módulo: dashboard

| Atributo | Valor |
|----------|-------|
| **Path** | `dashboard/` |
| **Estado** | **LEGACY** — stub Firebase, sustituido por `core/views` dashboard |
| **Tests** | 0 |

**Nota:** Instalado y en MODULE_CONFIGS pero funcionalidad real en `/core/dashboard/`.

---

## Módulo: reports

| Atributo | Valor |
|----------|-------|
| **Path** | `reports/` |
| **Tests** | 38 |
| **Propósito** | Motor de informes declarativos, dashboards, workspaces, monthly reporting | CONFIRMADO POR CÓDIGO |

### Modelos propios (PostgreSQL) — 22 clases

`ReportDefinition`, `ReportWidget`, `ReportDefinitionVersion`, `ReportDashboard`, `ReportExecutionLog`, `ReportWorkspace`, `ReportTemplate`, `LearnedRelationship`, `TableClusterAssignment`, `RelationshipAuditLog`, `PuntoVentaCanalEjecutivo`, `SucursalCanalEjecutivo`, `MonthlyReportingPack`, `MonthlyReportingImportBatch`, `MonthlyReportingClientMatch`, `MonthlyReportingClientMatchAudit`, `MonthlyReportingSeedRow`, `MonthlyReportingSuperArtCatalogVersion`, `MonthlyReportingSuperArtCatalogEntry`, `MonthlyReportingSuperArtQAPending`

### Tablas legacy

Principal consumidor MySQL — `cuentacliente`, `cuentaproveedor`, `articulo`, `compventa`, `stock*` y cientos de tablas vía `query_runner.py` y runners específicos.

### Servicios clave

`query_runner.py`, `connection_pool.py`, runners por informe (`ventas_*_runner.py`), `sql_validator.py`, `declarative-v1/`

### APIs

`/reports/` (HTML dashboards), `/api/reports/` (REST)

### Cache

`REPORTS_CACHE_ENABLED` (default false en settings)

### Dependencias

core (pool, permisos), MySQL legacy (lectura masiva)

### Riesgos

SQL dinámico en query builder; fallback `DEFAULT_BASE_EMPRESA` sin sesión

---

## Módulo: ia

| Atributo | Valor |
|----------|-------|
| **Path** | `ia/` |
| **Tests** | 3 |
| **Propósito** | Asistentes IA persistentes con memoria, herramientas y aprendizaje | CONFIRMADO POR CÓDIGO |

### Modelos (PostgreSQL) — 14 clases

`LlmProviderConfig`, `AgentDefinition`, `AgentConversation`, `AgentMessage`, `AgentExecution`, `AgentToolExecution`, `AgentMemoryItem`, `AgentMemoryFeedback`, `AgentLearningExample`

### Proveedores

OpenAI, OpenAI-compatible, Anthropic — vía `ia/services/llm_gateway.py` (requests HTTP directos, no langchain en app principal)

### APIs

`/ia/` (UI), `/api/ia/` (REST)

### Permisos

Hereda sesión AdministraNET; acceso a datos según herramientas del agente

### Riesgos

IA puede ejecutar herramientas que consultan MySQL — validar boundary en fase 16

---

## Módulo: ecom

| Atributo | Valor |
|----------|-------|
| **Path** | `ecom/` |
| **Tests** | 80 (mayor cobertura) |
| **Propósito** | E-commerce mayorista B2B, pedidos, carrito, relays PHP legacy | CONFIRMADO POR CÓDIGO |

### Modelos (PostgreSQL)

`EcomMigrationCheckpoint`, `EcomMailQueue`, `EcomCart`, `EcomCartItem`, `EcomCatalogoRestriccionPV`, `EcomPedidoMasivoDraft`, `EcomPedidoMasivoDraftCelda`

### Tablas legacy

Intenso — pedidos, clientes, artículos, precios, crédito, NC, recibos vía SQL + relays HTTP a `administraNET-ecom/`

### Servicios

50+ en `ecom/services/` — relays, catálogo, pedidos masivos, aprobación crédito, devoluciones

### APIs

`/ecom/` (extenso — hub pedidos, compra mayorista, vendedor operativo)

### Dependencias

fe_afip, core, stock (indirecto), PHP ecom externo

### Riesgos

Mayor superficie de código; acoplamiento dual SQL + HTTP relays

---

## Módulo: self_checkout

| Atributo | Valor |
|----------|-------|
| **Path** | `self_checkout/` |
| **Tests** | 3 |
| **Propósito** | TPV / autoservicio, facturación, caja | CONFIRMADO POR CÓDIGO |

**Modelos Django:** No (SQL directo)

**Tablas legacy:** `compventa`, `cuerpocompventa`, caja, stock, FE — 216 `cursor.execute`

**APIs:** `/self_checkout/`, `/api/self-checkout/`

**Dependencias:** fe_afip (CAE/CAEA), core (mysql_cursor)

**SQL DDL:** `self_checkout/sql/` (7 archivos)

---

## Módulo: fe_afip

| Atributo | Valor |
|----------|-------|
| **Path** | `fe_afip/` |
| **Tests** | 0 |
| **Propósito** | Facturación electrónica AFIP/ARCA — certificados, WSAA, WSFE, CAEA | CONFIRMADO POR CÓDIGO |

**Modelos:** `AFIPConfig`, `CAEACode` (PostgreSQL)

**Integración:** pyafipws (SOAP), certificados en volumen Docker `synap_afip_secrets`

**URLs:** Montadas vía `url_registry` → `/fe_afip/`

**Consumidores:** self_checkout, ecom

---

## Módulo: stock

| Atributo | Valor |
|----------|-------|
| **Path** | `stock/` |
| **Tests** | 19 |
| **Propósito** | Movimientos stock, inventario físico, depósitos AdministraNET | CONFIRMADO POR CÓDIGO |

**Modelos Django:** No

**Servicios:** `core/services/administranet_stock.py` + servicios propios

**APIs:** `/stock/` — alta movimiento, inventario, sincronización depósitos

---

## Módulo: ventas

| Atributo | Valor |
|----------|-------|
| **Path** | `ventas/` |
| **Tests** | 4 |
| **Propósito** | Objetivos de venta, presupuestos, precios terminados | CONFIRMADO POR CÓDIGO |

**Modelos Django:** No (MySQL legacy)

**APIs:** `/ventas/objetivos-venta/`, `/ventas/presupuestos/`

**Nota UI:** Excluido del canon UI según `.cursorrules` hasta levantamiento explícito

---

## Módulo: compras

| Atributo | Valor |
|----------|-------|
| **Path** | `compras/` |
| **Tests** | 0 |
| **Propósito** | Remitos de compra, hub comprobantes proveedor (PRemito.frm) | CONFIRMADO POR CÓDIGO |

**Modelos Django:** No

**APIs:** `/compras/`

**Riesgo:** Sin tests automatizados

---

## Módulo: factura_compra_captura

| Atributo | Valor |
|----------|-------|
| **Path** | `factura_compra_captura/` |
| **Tests** | 36 |
| **Propósito** | Workflow captura factura compra — expediente, OCR, revisión, posting | CONFIRMADO POR CÓDIGO |

**Modelos (PostgreSQL):** `ExpedienteFacturaCompra`, `LineaExpedienteCompra`, `DocumentoFuente`, `EventoAuditoriaInterno`

**APIs:** `/compras/captura/` (web), `/api/compras/` (REST)

**OCR:** Tesseract + OpenCV (heuristic/structured modes)

**Dependencias:** factura_compra_posting, legacy_db (fase posterior)

---

## Módulo: factura_compra_posting

| Atributo | Valor |
|----------|-------|
| **Path** | `factura_compra_posting/` |
| **Tests** | 10 |
| **Propósito** | Contrato + stub posting hacia MySQL legacy | CONFIRMADO POR CÓDIGO |

**Sin URLs propias** — librería consumida por factura_compra_captura

**Backend:** `FACTURA_COMPRA_POSTING_BACKEND` = fake|noop|legacy

---

## Módulo: legacy_db

| Atributo | Valor |
|----------|-------|
| **Path** | `legacy_db/` |
| **Tests** | 6 |
| **Propósito** | Capa escritura compatible VB6 — repositorios SQL parametrizados | CONFIRMADO POR CÓDIGO |

**Router:** `LegacyDbRouter` → alias `mysql`

**Repositorios:** `repositories.py` — sucursales, proveedores, operaciones contables

**Servicios:** `cont_recalculo_service.py`, `orden_pago_service.py`, `cont_eliminacion_asientos_service.py`

**APIs:** `/api/legacy-hub/`

**Riesgo:** Escritura directa en tablas compartidas con VB6

---

## Módulo: contabilidad_audit

| Atributo | Valor |
|----------|-------|
| **Path** | `contabilidad_audit/` |
| **Tests** | 7 |
| **Propósito** | Auditoría imputación contable (F1 lectura, recálculo planificado) | CONFIRMADO POR CÓDIGO |

**Modelos (PostgreSQL):** `PoliticaAuditoriaContable`, `CorridaAuditoria`, `PlanCorreccion`, `HistorialPoliticaAuditoria`, `AprobacionREI`

**Servicios:** `checks/` — compras_pagos, ventas_cobros, etc. (SQL contra MySQL)

**APIs:** `/contabilidad/`

---

## Módulo: mpr

| Atributo | Valor |
|----------|-------|
| **Path** | `mpr/` |
| **Tests** | 73 |
| **Propósito** | Manufacturing / Producción — OPT, partes, armado, trazabilidad, tablero | CONFIRMADO POR CÓDIGO |

**Modelos (PostgreSQL):** 16+ clases — `Opt`, `OptLinea`, `MprArmadoLote`, `MprParte`, `MprTurno`, `MprEmpresaConfig`, etc.

**Modelos BEST (Azure):** `BestArticuloMap`, `BestClienteMap`, etc. en `mpr/best_migration/`

**SQL crudo:** 787 `cursor.execute` — mayor consumidor MySQL del sistema

**APIs:** `/mpr/wizard/`, `/mpr/opt/`, tablero KPI

**DDL:** `mpr/sql/`, providers en `legacy_mysql_schema/catalog.py`

---

## Módulo: odoo_migracion

| Atributo | Valor |
|----------|-------|
| **Path** | `odoo_migracion/` |
| **Tests** | 6 |
| **Propósito** | Migración/sincronización AdministraNET → Odoo 19 | CONFIRMADO POR CÓDIGO |

**Modelos:** `OdooConnection`, `MigrationJob`, `MigrationEntityMapping`

**APIs:** `/odoo-migracion/`

---

## Módulo: tiendanube_administranet

| Atributo | Valor |
|----------|-------|
| **Path** | `tiendanube_administranet/` |
| **Tests** | 27 |
| **Propósito** | Integración Tienda Nube ↔ AdministraNET — sync productos, clientes, pedidos, webhooks | CONFIRMADO POR CÓDIGO |

**Modelos:** 20+ clases — mappings, webhooks, outbox, sync logs

**Async:** Celery tasks presentes (`tasks/sync_tasks.py`, `webhook_tasks.py`) — requiere broker

**APIs:** `/tiendanube_administranet/`, `/api/tiendanube_administranet/`

**Feature flags:** `TIENDANUBE_SYNC_ENABLED`, `TIENDANUBE_WEBHOOKS_ENABLED`

---

## Módulo: logistica

| Atributo | Valor |
|----------|-------|
| **Path** | `logistica/` |
| **Tests** | 4 |
| **Propósito** | Operación entregas logística | CONFIRMADO POR CÓDIGO |

**Modelos Django:** No (MySQL compartido con Reports)

**APIs:** `/logistica/`

---

## Módulo: theme

| Atributo | Valor |
|----------|-------|
| **Path** | `theme/` |
| **Propósito** | Tailwind CSS, plantillas base UI, input.css | CONFIRMADO POR CÓDIGO |

**Sin lógica de negocio.** Referencia UI canónica en `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`

---

## Módulos legacy / huérfanos (no en runtime activo)

| Módulo | Path | Estado |
|--------|------|--------|
| sia | `sia/` | Código completo, no instalado — FODA/CAME |
| mercadopago | `mercadopago/` | Comentado en settings, activable vía ModuleConfig |
| mtrix | `mtrix/` | Huérfano — solo `__pycache__` |
| support | `support/` | Proyecto Django+React separado |

---

## Matriz resumen

| Módulo | Tests | URLs | Models PG | MySQL R/W | APIs REST | Management cmds |
|--------|------:|------|:---------:|:---------:|:---------:|:---------------:|
| core | 27 | ✓ | ✓ | R+W | ✓ | 57 |
| login | 1 | ✓ | ✓ | R | — | — |
| reports | 38 | ✓ | ✓ | R | ✓ | 3+ |
| ecom | 80 | ✓ | ✓ | R+W | parcial | — |
| mpr | 73 | ✓ | ✓ | R+W | parcial | — |
| self_checkout | 3 | ✓ | — | R+W | ✓ | — |
| stock | 19 | ✓ | — | R+W | ✓ | — |
| factura_compra_captura | 36 | ✓* | ✓ | validación | ✓ | — |
| tiendanube | 27 | ✓ | ✓ | R+W | ✓ | 2+ |
| contabilidad_audit | 7 | ✓ | ✓ | R | — | — |
| legacy_db | 6 | ✓ | — | R+W | ✓ | scripts |
| ia | 3 | ✓ | ✓ | parcial | ✓ | 1 |
| odoo_migracion | 6 | ✓ | ✓ | R | — | — |
| fe_afip | 0 | ✓* | ✓ | R+W | — | — |
| ventas | 4 | ✓ | — | R+W | — | — |
| compras | 0 | ✓ | — | R+W | — | — |
| logistica | 4 | ✓ | — | R | — | — |

\* URLs vía `url_registry` o paths alternativos

---

*Generado por auditoría READ ONLY. Detalle de dependencias en `04-MODULE-DEPENDENCY-GRAPH.md`.*
