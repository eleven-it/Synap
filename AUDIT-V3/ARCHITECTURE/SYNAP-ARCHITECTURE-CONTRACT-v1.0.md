# SYNAP Architecture Contract v1.0

**Estado:** PENDIENTE APROBACIÓN HUMANA  
**Versión:** 1.0  
**Fecha:** 25/08/2026

Normative rules for Synap as **product platform**. Transition and AdministraNET-specific rules live in `02-TARGET-VS-TRANSITION-RULES.md`.

---

## Dependency Direction

- Application and domain code **MUST** depend on Port abstractions, not concrete adapters or ERP types.
- Domain modules **MUST NOT** import other domain modules' implementation details; shared contracts **MUST** live in `ports/`.
- `core/` **MUST NOT** import domain modules (ecom, mpr, reports, stock, ventas, etc.).
- Adapters **MUST NOT** be imported by domain modules except via dependency injection at application boundary.

## Core

- `core/` **MUST** contain only platform infrastructure: connection management, middleware, module registry, Port interfaces, cross-cutting utilities.
- `core/` **MUST NOT** accumulate new domain business logic.
- New ERP-specific code **MUST NOT** be added to `core/services/administranet_*`.

## Domain Modules

- Domain modules **MUST** be activatable via `ModuleConfig` without modifying other domain modules.
- New code in domain modules **MUST NOT** reference ERP table or column names.
- Domain modules **MUST** enforce authorization at every API and mutating view entry point.

## Data Access

- All ERP data access **MUST** go through Ports implemented by Adapters.
- Synap-owned data **MUST** use PostgreSQL via Django ORM (or documented Synap MySQL DDL via schema catalog).
- Cross-system operations **MUST NOT** assume distributed ACID; **MUST** use documented saga/outbox/idempotency patterns.

## Data Ownership

- Each business datum **MUST** have one logical System of Record declared before write access is added.
- **MUST NOT** write the same logical field from multiple systems without ownership contract.

## Execution Context

- Every request and background job **MUST** resolve `ExecutionContext` (Principal, Tenant, Company, Security, Correlation).
- Domain code **MUST NOT** read `session['user']`, `base_empresa`, or `AdministraNETUser` directly.
- **MUST NOT** use implicit tenant/company fallbacks for authenticated operations.

## Identity & Authorization

- Authentication, Identity, Authorization, Tenant, and Company **MUST** remain separate concerns.
- UI permission checks **MUST NOT** be the sole authorization layer; APIs **MUST** enforce equivalent checks.
- Authorization decisions **SHOULD** converge on Synap permission model (`synap_*`) per installation policy.

## Reporting

- Report execution **MUST** use `ReportDataSourcePort`; **MUST NOT** embed new ERP table knowledge in domain modules.
- `declarative-v1` **MUST** remain supported until semantic-v2 migration is complete.
- **MUST NOT** add new slug-dispatch branches in `query_runner.py` for new reports.

## AI

- AI tools **MUST** inherit the invoking Principal's permission scope (`PolicyGate`).
- **MUST NOT** expose data through AI that the Principal could not access via normal UI/API.

## Cache & Async

- Tenant/company-scoped cache keys **MUST** include company or tenant identifier.
- Background jobs **MUST** carry `ExecutionContext` and document idempotency for ERP writes.

## Integrations

- Inbound webhooks **MUST** verify authenticity (HMAC/signature) in production.
- Unreliable outbound sync **SHOULD** use outbox pattern.

## Security

- **MUST NOT** ship default cryptographic secrets in source code.
- Production **MUST** enforce TLS, secure cookies, and object-level authorization on multi-company resources.

## Presentation (structural only)

- Screens **SHOULD** consume shared design-system primitives when available.
- Feature modules **MUST NOT** redefine global design tokens.
- Business logic **MUST NOT** live in templates or presentation-only JavaScript.
- Navigation **SHOULD** reflect product capabilities, not Django package structure.

## Observability

- Port and Adapter boundaries **SHOULD** emit structured logs with correlation and company context.

## Testing

- New Port implementations **MUST** include integration tests against ERP test fixtures.
- Tenant isolation **SHOULD** be tested for new PostgreSQL APIs.

## Architectural Deviations

- Any violation **MUST** be documented before merge (reason, modules, risk, temporary/permanent, removal plan).
- **MUST NOT** introduce silent exceptions.

---

**Approval required before refactor.** Transition rules: `ARCHITECTURE/02-TARGET-VS-TRANSITION-RULES.md`.
