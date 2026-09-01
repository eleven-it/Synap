# SYNAP-AUDIT-FINAL-REPORT

**Estado:** COMPLETE  
**Fecha:** 25/08/2026  
**Auditoría:** READ ONLY — ingeniería inversa del código

---

## Executive Summary

Synap es un monolito modular Django 4.2 con 20 apps activas, ~1.800 archivos Python y ~380 tests, que opera como plataforma web complementaria de AdministraNET (ERP VB6 + MySQL). Usa PostgreSQL para metadatos propios y acceso directo SQL a MySQL legacy para datos de negocio.

**Hallazgo principal:** Synap ha evolucionado más allá de una interfaz web hacia una plataforma con capacidades propias (reportes, TPV, e-commerce, producción, IA), pero mantiene **acoplamiento crítico (nivel 4/4)** con AdministraNET en identidad, permisos, datos y procesos.

**Recomendación:** Transformación incremental hacia Synap Platform con Anti-Corruption Layer, tenant isolation y formalización del core. No big-bang rewrite.

**Score global: 4.1/10** en preparación para productización independiente.

---

## 1. What Synap Is Today

Monolito Django modular con:
- 20 apps activas + 4 legacy/huérfanas
- Dual database: PostgreSQL (Synap) + MySQL (AdministraNET)
- Pseudo-multitenant database-per-tenant en MySQL
- 750+ endpoints HTTP
- Motor de reportes declarativo propio
- Sistema de módulos plugables (ModuleConfig)
- Proyecto satélite Support (Django+React+RAG)

## 2. Current Architecture

Ver `02-CURRENT-ARCHITECTURE.md`. Monolito hub-and-spoke con core como centro gravitacional.

## 3. Runtime Architecture

Docker Compose: app (Python 3.10) + PostgreSQL 13 + Redis 6. Sin Celery worker. WSGI via runserver (dev) / Gunicorn (prod inferido).

## 4. Data Architecture

Ver `05-DATA-ACCESS-ARCHITECTURE.md`. Pool MySQL canónico, 2300+ SQL crudo, 0 ORM multi-db.

## 5. Core

Ver `09-SYNAP-CORE.md`. Pool + auth + permisos + módulos + backup. Lógica de negocio mal ubicada (stock, DDL).

## 6. Modules

Ver `03-MODULE-CATALOG.md`. 20 módulos documentados con modelos, APIs, tests, riesgos.

## 7. Module Dependency Graph

Ver `04-MODULE-DEPENDENCY-GRAPH.md`. core hub (256 refs). Sin ciclos directos. Acoplamiento implícito por datos.

## 8. Data Access

SQL crudo dominante. legacy_db/repositories.py como mejor patrón existente.

## 9. Database Ownership

Ver `06-DATABASE-TABLE-MAP.md`. ~100 tablas PG Synap-owned. ~200+ MySQL AdministraNET-owned. ~30 shared.

## 10. Data Lineage

Ver `07-DATA-LINEAGE.md`. 10 procesos críticos documentados.

## 11. Multi-tenancy

Ver `08-MULTITENANCY.md`. Database-per-tenant MySQL. PG sin aislamiento. Riesgo cross-tenant ALTO.

## 12. Identity & Permissions

Ver `10-IDENTITY-ACCESS-MANAGEMENT.md`. Auth AdministraNET MySQL. Permisos dual legacy/synap.

## 13. APIs

Ver `11-API-CATALOG.md`. 750+ endpoints. Sin versionado. Sin OpenAPI.

## 14. Async Jobs

Ver `12-ASYNC-PROCESSING.md`. Celery dormido. 160 management commands. Threads para OCR.

## 15. Cache

Ver `13-CACHE-ARCHITECTURE.md`. Redis default. Reportes cache off. Riesgo tenant en keys.

## 16. Frontend

Ver `14-FRONTEND-ARCHITECTURE.md`. SSR + Tailwind + Alpine. Canon UI MPR/Reports.

## 17. Reporting

Ver `15-REPORTING-ENGINE.md`. Motor propio productizable (metadatos). Query runner acoplado.

## 18. AI

Ver `16-AI-ARCHITECTURE.md`. ia/ con OpenAI/Anthropic. Support RAG separado.

## 19. Integrations

Ver `17-INTEGRATIONS.md`. 14 integraciones externas.

## 20. AdministraNET Coupling

Ver `18-ADMINISTRANET-COUPLING.md`. Nivel 4/4 en data, identity, logic, process.

## 21. Security

Ver `21-SECURITY-ASSESSMENT.md`. 2 CRITICAL, 6 HIGH. AES key, SQL dinámico, IDOR.

## 22. Performance

Pool MySQL limitado (5 conn). query_runner sin paginación universal. REPORTS_CACHE off. N+1 en algunos runners.

## 23. Testing

Ver `24-TESTING-ASSESSMENT.md`. 380 tests. Gaps: fe_afip (0), self_checkout (3), login (1).

## 24. Observability

Ver `22-OBSERVABILITY.md`. Solo console logging. No metrics/tracing/Sentry.

## 25. Technical Debt

Ver `27-TECHNICAL-DEBT.md`. 7 categorías, 25+ items documentados.

## 26. Productization

Ver `29-PRODUCTIZATION-ASSESSMENT.md`. No SaaS-ready. Componentes parcialmente productizables.

## 27. Reusability

Ver `32-REUSABILITY-MATRIX.md`. theme, ia, fe_afip, tiendanube REUSE AS IS.

## 28. Target Architecture

Ver `30-TARGET-ARCHITECTURE.md`. Synap Platform + ACL + domain modules.

## 29. Domain Boundaries

Ver `31-DOMAIN-BOUNDARIES.md`. 14 bounded contexts. Invasiones detectadas.

## 30. Migration Strategy

Ver `34-PRODUCT-TRANSFORMATION-ROADMAP.md`. 8 fases incrementales, 24+ meses.

## 31. Risk Matrix

Ver `33-REFACTOR-RISK-MATRIX.md`. self_checkout, ecom, mpr = mayor riesgo.

## 32. Critical Findings

Ver `CRITICAL-FINDINGS.md`. 10 hallazgos P0-P2.

## 33. Architecture Decisions Required

Ver `ARCHITECTURE-DECISIONS-REQUIRED.md`. 6 ADRs pendientes.

## 34. Final Recommendation

Synap tiene **valor significativo como plataforma** pero requiere inversión arquitectónica sustancial para independizarse de AdministraNET. La ruta es incremental:

1. Seguridad y tests (inmediato)
2. Tenant isolation PG (corto plazo)
3. Anti-Corruption Layer (medio plazo)
4. Bounded contexts (largo plazo)
5. Productización SaaS (estrategico)

**No desechar código existente** — refactorizar y encapsular. Los módulos reports (metadatos), ia, fe_afip, tiendanube y theme son semillas de producto.

---

## Respuestas a las 30 preguntas del master prompt

| # | Pregunta | Respuesta |
|---|----------|-----------|
| 1 | ¿Qué es Synap? | Monolito Django modular complementario AdministraNET |
| 2 | ¿Módulos? | 20 activos — ver catálogo 03 |
| 3 | ¿Core? | Pool MySQL + auth + permisos + módulos — ver 09 |
| 4 | ¿Comunicación? | Imports Python directos + datos MySQL compartidos |
| 5 | ¿Dónde vive cada dato? | PG=Synap, MySQL=AdministraNET, ver 06 |
| 6-8 | ¿Tablas por módulo? | Ver 06, 03 |
| 9 | ¿Datos AdministraNET? | Maestros, transacciones, permisos, config |
| 10 | ¿Datos Synap? | Reportes, IA, captura, módulos, synap_*, mpr_*, sc_* |
| 11 | ¿Multiempresa? | base_empresa en sesión → MySQL database — ver 08 |
| 12-13 | ¿Auth/Authz? | AdministraNET MySQL + permisos — ver 10 |
| 14 | ¿Conexión AdministraNET? | Pool MySQL directo — ver 05, 18 |
| 15 | ¿Lógica legacy? | Stock, permisos, contabilidad, ventas, formato datos |
| 16-18 | ¿Reutilizable/refactor/eliminar? | Ver 32, 28, 27 |
| 19 | ¿Dependencias circulares? | No en imports directos — ver 04 |
| 20-22 | ¿Riesgos? | Seguridad, tenant, datos — ver 21, 08, CRITICAL |
| 23-24 | ¿Separable/Core? | Ver 29, 09 |
| 25-27 | ¿SaaS/sin AdministraNET/otro ERP? | No/No/Sí con ACL — ver 29, 30 |
| 28 | ¿Adapter Odoo? | Viable — odoo_migracion como precedente |
| 29-30 | ¿Arquitectura futura/orden? | Ver 30, 34 |

---

## Documentos de la auditoría

Índice completo en `AUDIT/README.md` — 35+ documentos generados.

---

*Auditoría técnica integral Synap — READ ONLY — 25/08/2026*
