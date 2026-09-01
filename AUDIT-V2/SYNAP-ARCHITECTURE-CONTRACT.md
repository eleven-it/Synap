# SYNAP Architecture Contract

**Estado:** COMPLETE — **PENDIENTE APROBACIÓN HUMANA**  
**Versión:** 1.0-draft  
**Fecha:** 25/08/2026  
**Origen:** AUDIT-V2 validation against codebase

---

## Purpose

Normative rules for all future Synap code. Violations require **Architectural Deviation** documentation.

---

## Dependency Direction

- **MUST** follow dependency flow: `Domain Module → Port → Adapter → ERP/External`.
- **MUST NOT** import domain modules from `core/` (ecom, mpr, reports, stock, ventas, etc.).
- **MUST NOT** create circular imports between domain modules; shared contracts live in `ports/`.
- **SHOULD** depend on abstractions (Ports), not concrete adapters.

---

## Core

- **MUST** limit `core/` to: infrastructure (pool, middleware), module registry, Port interfaces, cross-cutting utilities (types, decorators).
- **MUST NOT** add new business logic to `core/services/administranet_*.py` — new logic goes in adapters.
- **MAY** retain existing `administranet_*` services until migrated behind Ports (legacy deviation).

---

## Domain Modules

- **MUST** be activatable via `ModuleConfig` without modifying other domain modules.
- **MUST NOT** access MySQL legacy tables directly in **new code** — use Ports.
- **SHOULD** keep PostgreSQL models scoped to module's own tables.
- **MUST** enforce permissions at API and view layer (`@tiene_permiso` or DRF permission class).

---

## Data Access

- **MUST** use `core.mysql_pool` (or successor) for all MySQL connections — no ad-hoc MySQLdb.
- **MUST** pass `base_empresa` / `CompanyContext` to every MySQL operation.
- **MUST** use `core.utils.administranet_types` for MySQL read/write type normalization.
- **MUST NOT** use Django ORM against AdministraNET tables except `legacy_db` unmanaged models and documented exceptions.
- **SHOULD** use parameterized queries (`%s`); **MUST NOT** interpolate user input into SQL identifiers without allowlist.

---

## ERP Integration

- **MUST** implement ERP access behind Port interfaces (`InventoryPort`, `SalesOrderPort`, etc.).
- **MUST** place AdministraNET-specific SQL in `adapters/administranet/` (or equivalent), not in domain modules.
- **MUST NOT** assume ERP table semantics in domain module — encapsulate in adapter.
- **MAY** support multiple ERP backends via adapter registry when product requires.

---

## Legacy Tables

- **MUST NOT** reference AdministraNET table names in new domain module code.
- **MUST** classify writes as MASTER/WRITE, TRANSACTION/WRITE, CONFIGURATION, or IDENTITY in deviation docs when adding ERP writes.
- **SHOULD** document new ERP writes in operational inventory.

---

## Tenant Context

- **MUST** resolve tenant/company context explicitly per request — no implicit globals.
- **MUST NOT** use `DEFAULT_BASE_EMPRESA` for authenticated user operations.
- **MUST** include company scope in PostgreSQL queries for multi-empresa resources.
- **MUST** include company scope in cache keys for tenant-scoped data.

---

## Company Context

- **MUST** use `CompanyContextPort` (once introduced) as single source for `erp_database` and `synap_empresa_id`.
- **MUST NOT** conflate `session['user']['id_empresa']` (MySQL) with `core.Empresa.id` (PostgreSQL) without explicit mapping.
- **SHOULD** set `empresa_activa_id` at login bootstrap for modules that need PG empresa.

---

## Identity

- **MUST** treat authentication, identity, authorization, and company context as separate concerns.
- **MUST NOT** assume Django `User` model for operational users — `AdministraNETUser` session is primary.
- **SHOULD** document any new auth path (WebAuthn, future IdP) in login module only.

---

## Permissions

- **MUST** check permissions on every API endpoint, not only HTML views.
- **MUST** use `@tiene_permiso` or equivalent DRF permission for mutating operations.
- **SHOULD** migrate toward `synap_*` permission tables per installation cutover plan.

---

## Reporting

- **MUST** execute reports through `ReportDataSourcePort` (once introduced).
- **MUST NOT** add new slug-dispatch branches in `query_runner.py` — use declarative-v1 or dedicated runner behind DataSource.
- **MUST** validate report config with `base_empresa` present.
- **SHOULD** use read-only MySQL credentials for report execution when infrastructure allows.

---

## AI Data Access

- **MUST** pass same permission context as user to AI tool invocations (`PolicyGate`).
- **MUST NOT** allow AI tools to query data beyond user's permissions.
- **SHOULD** log tool executions (`AgentToolExecution`).

---

## Cache

- **MUST** include `base_empresa` or `tenant_id` in cache keys for empresa-scoped data.
- **MUST NOT** cache cross-tenant data in global keys.
- **SHOULD** default report cache off until tenant isolation verified.

---

## Async Jobs

- **MUST** propagate `CompanyContext` to management commands and background jobs.
- **MUST** document idempotency for jobs that write ERP data.
- **MUST NOT** enqueue Celery tasks without active worker infrastructure.

---

## External Integrations

- **MUST** verify webhook signatures in production (`@csrf_exempt` only with HMAC/token).
- **MUST** use outbox/inbox patterns for unreliable external sync (tiendanube pattern).
- **SHOULD** isolate integration-specific mappings in integration module tables (PG).

---

## Security

- **MUST NOT** ship default secrets in code (`SECRET_KEY`, `ADMINISTRANET_MYSQL_AES_KEY`).
- **MUST** enforce `ENVIRONMENT=production` security settings (SSL, secure cookies).
- **MUST** apply object-level authorization on PG resources (empresa filter).
- **MUST NOT** use browser native `alert`/`confirm`/`prompt` in UI.

---

## Observability

- **SHOULD** log ERP write operations with company, user, capability, and correlation id.
- **SHOULD** use structured logging for Port/Adapter boundaries.

---

## Testing

- **MUST** add integration tests for new Port implementations against ERP test database.
- **SHOULD** test tenant isolation for new PG APIs.
- **MUST** run tests via `docker exec Synap_app python manage.py test <app>`.

---

## Architectural Deviations

Any code that violates this contract **MUST** be documented before merge:

```text
Deviation ID
Reason
Affected modules
Why no compliant alternative exists
Risk (LOW/MEDIUM/HIGH/CRITICAL)
Temporary or Permanent
Migration plan with target date
```

- **MUST NOT** introduce silent exceptions.
- **SHOULD** review deviations quarterly.

---

## Approval

| Role | Status | Date |
|------|--------|------|
| Engineering | PENDING | — |
| Product | PENDING | — |
| Security | PENDING | — |

**NO refactor authorized until this contract is approved.**

---

*Derived from AUDIT-V2/01 through AUDIT-V2/15.*
