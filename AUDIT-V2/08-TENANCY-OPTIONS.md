# 08 — Tenancy Options

**Estado:** COMPLETE — **REQUIERE DECISIÓN HUMANA** para selección  
**Fecha:** 25/08/2026

---

## Definiciones (NO son sinónimos)

| Término | Qué es en Synap hoy |
|---------|---------------------|
| **Installation** | Un deploy Synap (Docker compose, servidor cliente) |
| **Customer** | Cliente que contrata Synap (puede tener 1+ installations) |
| **Tenant** | Unidad de aislamiento lógico — **no formalizada** |
| **Company** | Empresa operativa dentro de AdministraNET (`base_empresa` / `id_empresa`) |
| **Database** | MySQL DB por empresa (AN) + PostgreSQL compartido (Synap) |

**Estado actual:** pseudo-multitenant — MySQL database-per-company; PostgreSQL shared sin row-level isolation.

---

## Option A: Dedicated deployment + DB per customer

| Aspecto | Evaluación |
|---------|------------|
| **Descripción** | 1 instalación Synap = 1 cliente enterprise; PG+MySQL dedicados |
| **Security** | **HIGH** — aislamiento físico |
| **Operational complexity** | HIGH — N deployments |
| **Backup/Restore** | Simple per customer |
| **On-premise** | **Ideal** — modelo actual |
| **SaaS** | No |
| **Migration from today** | **Trivial** — es el modelo actual |
| **Fit** | Clientes enterprise existentes AdministraNET |

---

## Option B: Shared application + DB per tenant (MySQL)

| Aspecto | Evaluación |
|---------|------------|
| **Descripción** | 1 app Synap; cada tenant = 1+ MySQL databases; PG shared o per-tenant |
| **Security** | MEDIUM-HIGH para MySQL; **LOW para PG** sin fix |
| **Operational complexity** | MEDIUM |
| **Scaling** | Horizontal app; MySQL per tenant |
| **Migration** | Requiere PG tenant isolation (middleware) |
| **Fit** | Managed cloud multi-empresa mismo cliente |

---

## Option C: Shared PostgreSQL + row-level tenant

| Aspecto | Evaluación |
|---------|------------|
| **Descripción** | PG con `tenant_id` en todas las tablas; RLS o middleware |
| **Security** | HIGH si RLS correcto; **actualmente NO** |
| **MySQL** | Sigue database-per-company (no cambia) |
| **Migration** | HIGH — 132 modelos + APIs a auditar |
| **Fit** | SaaS multi-tenant Synap-native data |

---

## Option D: Hybrid

| Aspecto | Evaluación |
|---------|------------|
| **Descripción** | ERP data per-company MySQL (como hoy) + Synap PG per-tenant o RLS |
| **Security** | Mejor de ambos si bien implementado |
| **Complexity** | HIGH |
| **Migration** | Incremental — recomendado por evidencia |
| **Fit** | **Recomendación técnica V2** sin imponer SaaS |

---

## Matriz comparativa

| Criterio | A | B | C | D |
|----------|:-:|:-:|:-:|:-:|
| Security | ★★★★★ | ★★★☆☆ | ★★★★☆ | ★★★★☆ |
| Ops complexity | ★★☆☆☆ | ★★★☆☆ | ★★★★☆ | ★★★★☆ |
| On-premise | ★★★★★ | ★★★☆☆ | ★★☆☆☆ | ★★★★☆ |
| SaaS viability | ★☆☆☆☆ | ★★★☆☆ | ★★★★★ | ★★★★☆ |
| Migration cost | ★★★★★ | ★★★☆☆ | ★★☆☆☆ | ★★★☆☆ |
| Compatible hoy | ★★★★★ | ★★★★☆ | ★★☆☆☆ | ★★★★☆ |

---

## Riesgos actuales cross-company (sin elegir opción)

| Vector | Evidencia | Severidad |
|--------|-----------|-----------|
| PG API sin filtro empresa | `factura_compra_captura/api/views.py:69-99` | HIGH |
| `?empresa=` param opcional | mismo archivo | HIGH |
| `DEFAULT_BASE_EMPRESA` | `query_runner.py:473-481` | HIGH |
| `get_empresa_actual()` fallback primera Empresa | `core/utils/utils.py:1863` | MEDIUM |
| Redis `core.active_modules.db` global | `module_manager.py:17` | LOW |
| Reports cache key sin base_empresa | `reports/cache.py:5-8` (mitigado: cache off) | MEDIUM |

---

## Recomendación V2 (no decisión)

1. **Corto plazo:** mantener Option A/D hybrid — no forzar SaaS.
2. **Prerequisito cualquier multi-tenant PG:** TenantContext middleware + API object-level checks.
3. **No mezclar** `id_empresa` MySQL con `core.Empresa.id` sin mapping explícito.

---

*No se selecciona arquitectura final — pendiente ADR humano.*
