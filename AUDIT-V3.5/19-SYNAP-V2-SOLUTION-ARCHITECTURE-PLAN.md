# SYNAP v2 — Plan de Arquitectura de Solución

**Rol:** Solution Architect  
**Fecha:** 02/09/2026  
**Estado:** PROPUESTA APROBABLE — backend y cambios estructurales primero  
**Precedentes:** `AUDIT/`, `AUDIT-V2/`, `AUDIT-V3/`, `AUDIT-V3.5/`

---

## 0. Decisiones de producto ya tomadas (inputs)

| Decisión | Valor | Implicación |
|----------|-------|-------------|
| Módulos actuales | **KEEP todos** por ahora | No deprecar; v2 R1 carga superficie completa vía Ports gradual |
| UI target | **shadcn/ui** (React) | v2 = **API-first backend** + SPA; no migrar templates Django a shadcn |
| Navegación | **Sidebar vertical** | Shell React; menú por capabilities + permisos (no APPS_MENU Django) |
| Versionado | **Ramas v2 separadas** (Option B) | Repo `Synap-v2` + `develop` / `staging` / `main` + `feature/*` |
| v1 | **Sigue recibiendo actualizaciones pequeñas** | Todo cambio post-kickoff entra al **V1 Change Ledger** y se evalúa para v2 (§2.5, `20-V1-CHANGE-LEDGER`) |
| Arranque | **Backend + estructura primero** | UI shadcn en fase posterior sobre contratos API estables |
| Auth | Session cookie same-site | ADR-003 |
| Frontend stack | Vite + React + shadcn | ADR-002 cerrado |
| Repo | Nuevo `Synap-v2` | Option B |

> **Cambio respecto a AUDIT-V3 TARGET/03:** se abandona “mantener Django Templates + Alpine” como UI permanente. El stack UI v2 es **React + shadcn + Tailwind**. Django permanece como **plataforma de aplicación y API**.

---

## 1. Visión de solución

```text
┌─────────────────────────────────────────────────────────────┐
│  Synap v2 Frontend (React + shadcn)                         │
│  Sidebar shell · Design System · Screens by capability      │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTPS / JSON (API v1)
┌───────────────────────────▼─────────────────────────────────┐
│  Synap v2 Application (Django + DRF)                        │
│  Auth · ExecutionContext · PolicyGate · Use Cases           │
└───────────────────────────┬─────────────────────────────────┘
                            │ Ports
┌───────────────────────────▼─────────────────────────────────┐
│  Domain Services (sin ERP types)                            │
└───────────────────────────┬─────────────────────────────────┘
                            │ Adapters
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   PostgreSQL          AdministraNET         Integraciones
   (Synap-owned)       MySQL Adapter         AFIP / TN / …
```

**Principio rector:** Synap v2 es un **producto API-first**. La UI shadcn es un cliente; no es dueña de reglas de negocio ni de autorización.

---

## 2. Topología de repositorio y ramas

### 2.1 Repositorio

| Repo | Rol |
|------|-----|
| `eleven-it/Synap` | **v1** — maintenance desde snapshot Staging; clientes actuales |
| `eleven-it/Synap-v2` | **v2** — source of truth del producto nuevo |

> Si por política de org se prefiere monorepo temporal: **único compromiso aceptable** es carpeta `v2/` aislada + CI separado. **Recomendación firme:** repo nuevo (Option B).

### 2.2 Ramas v2 (GitFlow adaptado)

```text
feature/*  ──PR──►  develop  ──release──►  staging  ──tag──►  main
hotfix/*   ──────────────────────────────►  main (+ back-merge develop)
```

| Rama | Ambiente | Quién mergea |
|------|----------|--------------|
| `develop` | DEV | PRs de `feature/*` |
| `staging` | Preprod / pilot | Release desde `develop` |
| `main` | Production v2 | Solo desde `staging` + tag SemVer `v2.x.y` |
| `feature/*` | local | Nunca directo a `main` |
| `hotfix/*` | prod fix | `main` → back-merge `develop` |

### 2.3 Reglas de gobernanza

1. **Nadie** commit directo a `develop` / `staging` / `main`.
2. **CODEBASE ≠ ENVIRONMENT** — diferencias solo por config/secrets/flags.
3. Docs **permanecen** en el repo v2 (no se remueven en staging).
4. v1 **no** recibe merges de v2; cambios v2→v1 solo según policy de seguridad.
5. Branch protection + required checks desde el día 1.
6. **Todo cambio en v1 post-kickoff** se registra en el V1 Change Ledger y genera decisión v2 (APPLY / DEFER / N/A).

### 2.4 Estructura inicial del repo Synap-v2

```text
Synap-v2/
├── backend/                 # Django project (API + domain)
│   ├── manage.py
│   ├── config/              # settings, urls, asgi/wsgi
│   ├── apps/
│   │   ├── platform/        # ExecutionContext, auth, perms, installation
│   │   ├── ports/           # interfaces (Protocols / ABCs)
│   │   ├── adapters/        # administranet, afip, tn, …
│   │   ├── sales/           # domain + use cases (ecom parity)
│   │   ├── inventory/
│   │   ├── production/      # mpr
│   │   ├── pos/             # self_checkout
│   │   ├── reporting/
│   │   └── …                # un bounded context por capability group
│   ├── tests/
│   └── pyproject.toml / requirements
├── frontend/                # React + Vite + shadcn (fase UI)
│   ├── src/
│   │   ├── app/             # routes, providers
│   │   ├── components/ui/   # shadcn primitives
│   │   ├── features/        # feature modules
│   │   └── layouts/         # AppShell + Sidebar
│   └── package.json
├── docs/
│   ├── architecture/
│   ├── adr/
│   └── runbooks/
├── docker/
├── .github/workflows/
└── README.md
```

**Backend-first:** en las primeras sprints `frontend/` puede ser scaffold vacío o shell mínimo; el trabajo real está en `backend/`.

---

## 2.5 V1 Change Ledger — sincronización continua v1 → v2

**Problema:** v1 seguirá recibiendo actualizaciones pequeñas (bugs, hotfixes, ajustes operativos) mientras se construye v2. Sin un proceso explícito, v2 diverge en silencio y la migración pierde parity.

**Regla absoluta post-kickoff:**

> Ningún cambio mergeado a v1 (Desarrollo → Staging / maintenance) puede considerarse “cerrado” hasta tener una **entrada en el V1 Change Ledger** con decisión para v2.

Detalle operativo: [`20-V1-CHANGE-LEDGER.md`](./20-V1-CHANGE-LEDGER.md).

### Kickoff baseline

| Artefacto | Valor |
|-----------|-------|
| Tag v1 | `v1-kickoff-v2` (commit Staging en fecha de kickoff) |
| Ledger | `Synap-v2/docs/migration/V1_CHANGE_LEDGER.md` (fuente de verdad) |
| Espejo opcional en v1 | `docs/general/V1_CHANGE_LEDGER.md` o link al repo v2 |

### Flujo obligatorio por cada PR/cambio v1

```text
1. Desarrollar fix/ajuste en v1 (feat/fix/hotfix → Desarrollo → Staging)
2. En el PR v1: completar checklist "Impacto Synap v2"
3. Al merge: crear/actualizar fila en V1 Change Ledger
4. Asignar decisión v2:
     APPLY NOW     → ticket feature/* en Synap-v2 (mismo sprint o siguiente)
     APPLY WHEN PORT READY → ticket linked a capability / Port
     DEFER         → justificado; revisar en grooming mensual
     N/A           → solo docs v1, cosmético UI v1, infra v1-only
5. Revisión semanal del backlog "v1→v2 pending"
6. Antes de declarar capability migrada: ledger de esa capability = 0 pendientes APPLY
```

### Clasificación de impacto (v1 → v2)

| Tipo de cambio v1 | Decisión típica v2 |
|-------------------|---------------------|
| SECURITY / DATA CORRUPTION | **APPLY NOW** (aunque Port no exista: parche temporal o adapter) |
| Regla de negocio / cálculo / validación | **APPLY WHEN PORT READY** o APPLY NOW si capability ya en v2 |
| Fix funcional en capability R1 | **APPLY WHEN PORT READY** (ticket obligatorio) |
| UX / template / Alpine solo v1 | **N/A** (v2 es shadcn; no portar markup) |
| Nueva feature grande en v1 | **Evitar**; si inevitable → **APPLY WHEN PORT READY** + product review |
| Schema MySQL / legacy catalog | **APPLY NOW** en adapter + docs ownership |
| Config / feature flag v1 | **APPLY** en Installation model cuando exista |
| Docs / runbook v1 | **N/A** o espejo docs v2 si aplica |

### Ownership

| Rol | Responsabilidad |
|-----|-----------------|
| Autor del PR v1 | Completar checklist impacto + proponer clasificación |
| Reviewer v1 | No aprobar PR sin checklist |
| Tech lead / Solution Architect | Decisión final APPLY/DEFER/N/A; priorizar tickets v2 |
| Equipo v2 | Cerrar tickets APPLY; grooming semanal del ledger |

### Gate de capability migrada (ampliado)

Además de parity tests (`13-MIGRATION-ACCEPTANCE-CRITERIA`):

- [ ] Todas las entradas del ledger que tocan esa capability están **CLOSED** (aplicadas en v2) o **N/A** justificado
- [ ] No hay `APPLY NOW` o `APPLY WHEN PORT READY` abiertos > SLA (ver ledger)

### Relación con backport policy

| Dirección | Documento |
|-----------|-----------|
| v1 → v2 (forward-port / contemplar) | **Este §2.5 + `20-V1-CHANGE-LEDGER`** |
| v2 → v1 (excepciones) | `17-V1-V2-BACKPORT-POLICY` |

---

## 3. Arquitectura backend objetivo

### 3.1 Capas (obligatorias)

| Capa | Responsabilidad | MUST NOT |
|------|-----------------|----------|
| **Presentation (API)** | Serializers, views DRF, OpenAPI | Reglas de negocio, SQL ERP |
| **Application** | Use cases / orchestrators | Importar adapters concretos |
| **Domain** | Entidades, invariantes | `base_empresa`, nombres de tabla MySQL |
| **Ports** | Contratos | Referenciar AdministraNET / Odoo |
| **Adapters** | Implementaciones ERP/API | Ser importados por domain |
| **Platform** | Auth, context, modules, audit | Lógica de dominio de pedidos/stock |

### 3.2 ExecutionContext (entregable estructural #1)

```text
ExecutionContext
├── PrincipalContext   { principal_id, identity_provider, roles[], permissions[] }
├── TenantContext      { tenant_id }          # instalación / operador
├── CompanyContext     { company_id, external_ref }  # ≠ base_empresa en domain
├── SecurityContext    { authz decisions, scopes }
├── CorrelationContext { request_id, operation_id, idempotency_key? }
└── LocaleContext      { locale=es-AR, date_format=dd/MM/yyyy }
```

**Resolución:** middleware/DRF authentication → builder inmutable → inyectado en use cases.

**Prohibido en domain:** `request.session['user']`, `AdministraNETUser`, `base_empresa` literal.

### 3.3 Modelo de instalación (entregable estructural #2)

```text
SynapInstallation
├── enabled_modules[]
├── enabled_capabilities[]
├── feature_flags{}
├── business_policies{}
├── erp_adapter config
├── integration_adapters{}
└── extension_packs[]   # DABRA report, Best monthly — NO if client_a
```

Persistencia: PostgreSQL (Synap-owned). Sustituye el modelo implícito v1 (`.env` + ModuleConfig + tablas ad-hoc).

### 3.4 Identidad y autorización (entregable estructural #3)

| Concepto v1 | Concepto v2 |
|-------------|-------------|
| `cod_usuario` + session | Principal + token (session cookie o JWT short-lived) |
| `id_puesto` → permisos | Grants de capability permissions |
| `SYNAP_PERMISOS_SOURCE` dual | Un store: `capability.action` |
| Menú filtra UI | API **siempre** enforce; UI solo UX |

**API authz rule:** todo endpoint mutante y todo GET sensible → `PolicyGate.require("sales.order.view")`.  
**Cierre de gaps v1:** no bypassear `/api/`; no confiar en botón oculto.

Nomenclatura target (migración gradual desde 244 códigos):

```text
sales.order.view | sales.order.create | sales.order.approve
inventory.movement.create | inventory.count.execute
production.order.release | production.timesheet.submit
reports.view | reports.export
pos.sale.execute
system.superuser
```

### 3.5 Ports iniciales (entregable estructural #4)

Prioridad por R1 MUST + acoplamiento:

| Port | Adapter v1 bridge | Primera capability |
|------|-------------------|--------------------|
| `IdentityPort` | AdministraNET users/puestos | Login |
| `PermissionPort` | synap_* store | Authz |
| `CustomerPort` | cliente MySQL | Pedidos |
| `ProductCatalogPort` | articulo/stock read | Catálogo / reports |
| `InventoryPort` | stock movements | Stock |
| `SalesOrderPort` | comp_ped | Pedidos + hub |
| `ReportDataSourcePort` | declarative-v1 runner | Reports execute |
| `AuditTrailPort` | PG events | Cross-cutting |

**Regla:** un Port **no** es un mirror de tabla. Si huele a `CompPedPort`, rediseñar a capability.

### 3.6 Cross-system (entregable estructural #5)

Patrones obligatorios desde foundation:

| Pattern | Uso |
|---------|-----|
| `operation_id` | Toda escritura multi-sistema |
| `idempotency_key` | POST de pedidos, stock, TPV, AFIP |
| Outbox | Integraciones outbound (TN, email) |
| Correlation ID | Logs + traces |
| Compensation doc | Por use case (no ACID distribuido) |

### 3.7 API surface

```text
/api/v2/auth/*
/api/v2/me
/api/v2/navigation          # sidebar tree filtrado por permisos
/api/v2/installations/current
/api/v2/sales/...
/api/v2/inventory/...
/api/v2/production/...
/api/v2/reports/...
/api/v2/pos/...
```

- Versionado URL `/api/v2/` desde día 1.
- OpenAPI generado (drf-spectacular o equivalente).
- Contratos estables **antes** de pantallas shadcn.

### 3.8 Estrategia de bridge hacia v1 (sin contaminar)

Durante transición, adapters pueden:

1. Llamar servicios existentes de v1 **solo desde `adapters/`** (código copiado o paquete interno versionado), **o**
2. Reimplementar SQL/ORM limpio en adapter.

**Prohibido:** importar `ecom.views` o templates v1 desde domain v2.

Recomendación: **copiar/adaptar** lógica de servicios críticos a `adapters/administranet/` + characterization tests; no depender del árbol de templates v1.

---

## 4. Frontend (contrato, no implementación aún)

Aunque el arranque es backend, la arquitectura debe **anticipar** shadcn:

| Decisión | Valor |
|----------|-------|
| Stack | React 19 + Vite (o Next.js App Router — **decidir en kickoff UI**) |
| UI kit | **shadcn/ui** + Tailwind |
| Layout | `AppShell` + **Sidebar vertical** (collapsible) |
| Routing | Por capability (`/sales/orders`, `/inventory/...`) — no por app Django |
| Auth | Cookie session same-site o Bearer; refresh policy definida en backend |
| Data | TanStack Query (recomendado) sobre OpenAPI client |
| i18n | Español UI; fechas `dd/MM/yyyy` |

**Sidebar data contract (backend provee):**

```json
{
  "sections": [
    {
      "id": "comercial",
      "label": "Comercial",
      "items": [
        { "id": "sales.orders", "label": "Pedidos", "href": "/sales/orders", "permission": "sales.order.view" }
      ]
    }
  ]
}
```

IA de menú = **capabilities** (`AUDIT-V3.5` + `TARGET/02`), no `INSTALLED_APPS`.

---

## 5. Plan por fases (backend / estructural primero)

### Fase 0 — Gobernanza y bootstrap (1–2 semanas)

**Objetivo:** repo y CI listos; cero features de negocio.

| # | Entregable | Criterio de done |
|---|------------|------------------|
| 0.1 | Crear `Synap-v2` (vacío o scaffold) | Remoto + branch protection |
| 0.2 | Ramas `develop` / `staging` / `main` | Policies + CODEOWNERS |
| 0.3 | Snapshot v1 `maintenance` / baseline kickoff desde Staging | Tag `v1-kickoff-v2` + runbook |
| 0.4 | **Activar V1 Change Ledger** (proceso + plantilla + checklist PR) | Ver §2.5 y `20-V1-CHANGE-LEDGER.md` |
| 0.5 | Docker Compose DEV (PG + Redis + app) | `make up` verde |
| 0.6 | CI: lint + test vacío + OpenAPI stub | PR checks required |
| 0.7 | ADR-001: monorepo backend/frontend | Aprobado |
| 0.8 | ADR-002: Vite+React (cerrado) | Documentado |
| 0.9 | Actualizar baseline: UI=shadcn, keep modules, ledger | Docs v2 |

**Exit:** equipo trabaja solo en `feature/*` → PR a `develop`; **todo PR a v1 exige entrada de ledger**.

---

### Fase 1 — Platform kernel (2–3 semanas)

**Objetivo:** esqueleto Django + ExecutionContext + health.

| # | Entregable | Detalle |
|---|------------|---------|
| 1.1 | Proyecto `config/` settings por ambiente | `ENVIRONMENT`, secrets, 12-factor |
| 1.2 | App `platform` | models mínimos Installation, AuditEvent |
| 1.3 | `ExecutionContext` + middleware/DRF | Tests unitarios |
| 1.4 | Correlation ID en logs (structlog) | Header `X-Request-ID` |
| 1.5 | Health/readiness endpoints | `/api/v2/health` |
| 1.6 | Paquete `ports/` vacío con Protocols | Sin implementaciones |
| 1.7 | Regla CI: domain no importa adapters | import-linter / custom check |

**Exit:** request autenticado mock → context resuelto; tests verdes.

---

### Fase 2 — Identity & Permissions (3–4 semanas)

**Objetivo:** login/empresa/permisos como API; cierra gaps de seguridad estructurales.

| # | Entregable | Detalle |
|---|------------|---------|
| 2.1 | `IdentityPort` + `AdministraNETIdentityAdapter` | Validate user, list companies |
| 2.2 | `POST /api/v2/auth/login` + select company | Session/JWT decisión en ADR-003 |
| 2.3 | `GET /api/v2/me` | Principal + permissions + company |
| 2.4 | Permission catalog seed (capability codes) | Mapping doc desde v1 244 codes |
| 2.5 | `PolicyGate` + DRF permission class | Deny by default |
| 2.6 | `GET /api/v2/navigation` | Árbol sidebar filtrado |
| 2.7 | Characterization: WF-01 login vs v1 | Parity tests |
| 2.8 | Tests negativos: sin permiso → 403 | Incl. API |

**Exit:** cliente HTTP puede autenticarse y obtener menú; sin UI aún.

---

### Fase 3 — Installation & configuration model (2 semanas)

| # | Entregable |
|---|------------|
| 3.1 | Modelo `Installation` + modules + flags + policies |
| 3.2 | Bootstrap command (seed DEV) |
| 3.3 | `GET /api/v2/installations/current` |
| 3.4 | Extension pack registry (vacío + stubs DABRA/Best) |
| 3.5 | Feature flag evaluation API interna |

**Exit:** mismo binario, dos installations (A/B) solo por config — **sin if cliente**.

---

### Fase 4 — Ports piloto + primer bounded context (4–6 semanas)

**Orden recomendado (riesgo vs valor):**

```text
1. ReportDataSourcePort (read-only)  → reports execute
2. InventoryPort (read)              → stock consult
3. SalesOrderPort (read)             → list/detail pedidos
4. SalesOrderPort (write)            → create/checkout (idempotent)
5. InventoryPort (write)             → movimientos
```

Por cada Port:

1. Contract + fake adapter (tests)
2. AdministraNET adapter + integration tests (fixtures MySQL)
3. Use cases + API endpoints
4. Characterization vs v1 (parity matrix fila)
5. OpenAPI publicado

**Exit R1 backend slice:** pedidos read + stock read + report execute vía API.

---

### Fase 5 — Cross-cutting hardening (paralelo a Fase 4)

| # | Entregable |
|---|------------|
| 5.1 | Outbox table + worker stub |
| 5.2 | Idempotency middleware para POST |
| 5.3 | Audit trail en escrituras |
| 5.4 | Object-level company checks (anti-IDOR) |
| 5.5 | Rate limit login |
| 5.6 | Observability: metrics básicas |

---

### Fase 6 — UI Shell shadcn (después de contratos estables)

*Fuera del “backend first”, pero planificada:*

| # | Entregable |
|---|------------|
| 6.1 | Scaffold Vite/React + shadcn |
| 6.2 | `AppShell` + **Sidebar vertical** consumiendo `/navigation` |
| 6.3 | Auth pages (login, empresa) |
| 6.4 | Primera pantalla: lista pedidos (read) |
| 6.5 | Design tokens alineados a shadcn + brand Synap |

**Regla:** no construir pantallas sin OpenAPI del endpoint.

---

### Fase 7 — Expansion R1 (post-shell)

Según `14-V2-RELEASE-1-SCOPE.md`: hub, masivo, writes stock, luego SHOULD (MPR, TPV, AFIP, extensions).

---

## 6. Mapeo módulos v1 → bounded contexts v2

Todos se **mantienen** como capabilities; la estructura de carpetas **no** copia 1:1 las apps Django.

| App v1 | Bounded context v2 | Prioridad Port |
|--------|--------------------|----------------|
| `login` + parte `core` | `platform` (identity) | P0 |
| `core` (users, modules) | `platform` (admin) | P0 |
| `ecom` | `sales` | P0 |
| `stock` | `inventory` | P0 |
| `reports` | `reporting` | P0 |
| `mpr` | `production` | P1 |
| `self_checkout` | `pos` | P1 |
| `ventas` | `sales` (objectives subdomain) | P2 |
| `compras` + captura + posting | `purchasing` | P2 |
| `contabilidad_audit` | `accounting` | P1 (CLIENT-A) |
| `fe_afip` | `tax` / fiscal | P1 |
| `logistica` | `logistics` | P2 |
| `tiendanube_administranet` | `integrations/ecommerce` | P2 |
| `odoo_migracion` | `integrations/odoo` | P3 |
| `ia` | `assistant` | P3 |
| `mtrix` | `integrations/mtrix` | P2 |
| `legacy_db` | **solo** dentro de `adapters/administranet` | Transition |
| `dashboard` / `theme` | Reemplazados por frontend shell | — |

---

## 7. Calidad y readiness gates

### Gate A — Foundation ready (fin Fase 1–2)

- [ ] ExecutionContext en todos los requests autenticados
- [ ] PolicyGate en endpoints
- [ ] Import-linter: domain ↛ adapters
- [ ] OpenAPI auth/me/navigation publicado
- [ ] WF-01 characterization verde

### Gate B — First business slice (fin Fase 4)

- [ ] ≥1 Port write con idempotency
- [ ] Parity tests pedidos list/detail
- [ ] Company scoping tests (anti-IDOR)
- [ ] Staging v2 deployable

### Gate C — UI shell (fin Fase 6)

- [ ] Sidebar vertical + login shadcn
- [ ] Una capability end-to-end (login → listado)
- [ ] Visual baseline inicial

### Gate D — Customer pilot

Según `13-MIGRATION-ACCEPTANCE-CRITERIA.md`.

---

## 8. Riesgos del plan y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Reescritura total vs strangle | Ports + adapters bridge; no big-bang UI |
| shadcn implica SPA; ERP density | Tablas densas con TanStack Table; no “minimalismo” |
| Doble mantenimiento v1/v2 | **V1 Change Ledger** + grooming semanal; no freeze total |
| Olvidar portar un fix v1 | Checklist PR v1 obligatorio; gate en capability migrada |
| Shared MySQL durante pilot | operation_id + ownership; writes controlados |
| Equipo sin React profundo | Backend first compra tiempo; Vite+React cerrado |
| Scope creep (todos los módulos KEEP) | R1 MUST primero; resto detrás de flags |

---

## 9. Equipo y orden de trabajo sugerido

| Rol | Foco inmediato |
|-----|----------------|
| Solution / Platform | Fases 0–2 (kernel, authz) + **owner del ledger** |
| Backend domain | Ports inventario + sales (Fase 4) |
| DevOps | Repo, CI, environments |
| Frontend | Stand-by hasta OpenAPI auth+navigation; luego shell shadcn |
| QA | Characterization harness desde Fase 2 |
| Todo el equipo v1 | Checklist impacto v2 en cada PR |

---

## 10. Primeros tickets concretos (Sprint 0–1)

1. Crear repo `Synap-v2` + ramas + branch protection  
2. Scaffold `backend/` Django + Docker PG/Redis  
3. ADR-001 estructura monorepo backend/frontend  
4. Tag `v1-kickoff-v2` + crear **V1 Change Ledger** + checklist PR v1  
5. Implementar `ExecutionContext` + tests  
6. Implementar `IdentityPort` (fake) + login stub API  
7. Import-linter + CI  
8. Documento mapping permisos v1→v2 (seed catalog)  
9. Snapshot/runbook coexistencia + grooming semanal ledger en calendario  
10. Plantilla issue GitHub: `[v1→v2] <titulo>` linkeada al ledger  

---

## 11. Lo que NO se hace en esta etapa

- Migrar pantallas shadcn masivas  
- Deprecar módulos  
- Implementar semantic-v2 reports completo  
- Cambiar clientes / Staging v1  
- Backportear Ports a v1  

---

## 12. Aprobaciones — estado

| # | Pregunta | Decisión |
|---|----------|----------|
| 1 | Repo nuevo `Synap-v2` | ✅ Aprobado |
| 2 | Auth session cookie same-site | ✅ Aprobado |
| 3 | Vite+React + shadcn | ✅ Aprobado |
| 4 | v1 sigue con updates pequeñas + **V1 Change Ledger** | ✅ Aprobado (02/09/2026) |

---

## 13. Criterio de éxito del plan

Al completar Fases 0–4 sin UI completa:

> Un cliente HTTP autenticado puede **login → company → navigation → listar pedidos/stock/report** contra AdministraNET vía Ports, con permisos backend, sin `if cliente`, con Operation ID en escrituras, sobre ramas `feature/*` → `develop` del repo v2 — mientras v1 sigue sirviendo clientes y **cada cambio v1 queda contemplado en el ledger para v2**.

Eso es el **cimiento** sobre el cual shadcn + sidebar vertical se montan sin rehacer el backend.

---

*Documento vivo — actualizar ADRs al cerrar cada decisión. Siguiente paso tras aprobación: ejecutar Fase 0 (crear repo + scaffold + activar ledger).*
