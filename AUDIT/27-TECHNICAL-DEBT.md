# 27 — Deuda Técnica

**Estado:** COMPLETE (Fase 27)  
**Fecha:** 25/08/2026

---

## Architecture debt

| Issue | Evidencia | Impact | Severity | Action | Effort |
|-------|-----------|--------|:--------:|--------|:------:|
| Sin Anti-Corruption Layer | 15+ apps SQL directo | Imposible cambiar ERP | Critical | ACL incremental | XL |
| core como god module | 256 imports entrantes | Cuello de botella | High | Extraer dominios | L |
| Dos registros módulos | INSTALLED_APPS vs MODULE_CONFIGS | Inconsistencia | Medium | Unificar | M |
| Sin API versioning | 750+ endpoints | Breaking changes | Medium | /api/v1/ | M |
| Celery sin worker | tasks definidas, no worker | Jobs perdidos | High | Activar o eliminar | S |

## Data debt

| Issue | Evidencia | Impact | Severity | Action | Effort |
|-------|-----------|--------|:--------:|--------|:------:|
| PG sin tenant isolation | Modelos globales | Cross-tenant leak | Critical | Tenant middleware | L |
| SQL disperso 2300+ execute | 15 apps | Mantenibilidad | High | Repository layer | XL |
| latin1 charset | settings mysql | Encoding bugs | Medium | UTF-8 migration | L |
| Permisos dual legacy/synap | SYNAP_PERMISOS_SOURCE | Inconsistencia | High | Cutover synap | M |

## Code debt

| Issue | Evidencia | Impact | Severity | Action | Effort |
|-------|-----------|--------|:--------:|--------|:------:|
| query_runner 4000 líneas | reports/services/ | Untestable | High | Split + refactor | L |
| mpr/services 8000+ líneas | mpr/ | Untestable | High | Domain services | L |
| Archivos * 2.py duplicados | Varios módulos | Confusión | Low | Cleanup | S |
| Firebase legacy code | login, dashboard | Dead code | Low | Remove | S |
| Apps comentadas en settings | 12 apps | Confusión | Low | Remove/archive | S |

## Security debt

| Issue | Impact | Severity | Action | Effort |
|-------|--------|:--------:|--------|:------:|
| AES key default | Password compromise | Critical | Remove default | S |
| SQL dinámico reportes | SQL injection | Critical | Sandbox | L |
| API sin permisos granulares | Privilege escalation | High | Audit endpoints | M |

## Testing debt

| Issue | Impact | Severity | Action | Effort |
|-------|--------|:--------:|--------|:------:|
| fe_afip 0 tests | Regresión FE | High | Add tests | M |
| self_checkout 3 tests | Regresión TPV | High | Add tests | L |
| Sin E2E | Regresión UI | Medium | Playwright/Cypress | L |

## Documentation debt

| Issue | Impact | Action | Effort |
|-------|--------|--------|:------:|
| Docs divergen de código | Confusión equipos | Esta auditoría + sync | M |
| Sin OpenAPI | Integración difícil | Generate schema | M |
| 57 commands sin docs cron | Ops risk | Documentar runbook | S |

## Product debt

| Issue | Impact | Action | Effort |
|-------|--------|--------|:------:|
| No multi-tenant SaaS | No productizable | Tenant platform | XL |
| Acoplamiento AdministraNET 4/4 | No vendible standalone | ACL + adapter | XL |
| UI no unificada | UX inconsistente | Canon UI enforcement | L |

---

*Generado por auditoría READ ONLY.*
