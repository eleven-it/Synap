# ARCHITECTURE-DECISIONS-REQUIRED

**Estado:** COMPLETE  
**Fecha:** 25/08/2026

---

## ADR-PENDING-001: Acceso a MySQL AdministraNET

**¿Synap seguirá accediendo directamente a MySQL de AdministraNET?**

| Alternativa | Pros | Contras |
|-------------|------|---------|
| A: Acceso directo (status quo) | Sin esfuerzo | No productizable, acoplamiento 4/4 |
| B: Integration Layer (ACL) | Desacoplamiento gradual | Esfuerzo XL, 2 sistemas en transición |
| C: AdministraNET API (VB6 expone API) | Separación limpia | Requiere desarrollo VB6 |

**Recomendación auditoría:** B — ACL incremental  
**Impacto:** Afecta 15+ apps, timeline 12-18 meses

---

## ADR-PENDING-002: Modelo de tenancy

**¿Qué modelo de multi-tenancy adoptar?**

| Alternativa | Descripción |
|-------------|-------------|
| A: Database-per-tenant (status quo MySQL) | Mantener, agregar PG tenant |
| B: Schema-per-tenant | Un MySQL, schemas separados |
| C: Row-level tenant | Filtro tenant_id en todas las tablas |
| D: Híbrido | PG row-level + MySQL database-per-tenant |

**Recomendación auditoría:** D — híbrido pragmático  
**Impacto:** Middleware PG, keys Redis, validación APIs

---

## ADR-PENDING-003: Fuente de permisos

**¿Cuándo hacer cutover de permiso_sistema* a synap_*?**

| Alternativa | Riesgo |
|-------------|--------|
| A: Mantener legacy indefinidamente | Dos fuentes, inconsistencia |
| B: Cutover synap con rollback | Medio — requiere validación dual previa |
| C: Permisos independientes Synap | Alto — rompe paridad VB6 |

**Recomendación:** B — validar en dual, cutover con rollback  
**Impacto:** core/permisos, todos los módulos

---

## ADR-PENDING-004: Celery vs alternatives

**¿Activar Celery o usar alternativa para async?**

| Alternativa | Pros | Contras |
|-------------|------|---------|
| A: Activar Celery en compose | Tasks ya escritas | Infra adicional |
| B: Management commands + cron | Simple, funciona hoy | No real-time |
| C: Django-Q / Huey | Más ligero | Migrar tasks |
| D: Eliminar async, todo sync | Simplest | Performance |

**Recomendación:** A para tiendanube; B para backup/cron  
**Impacto:** docker-compose, tiendanube tasks

---

## ADR-PENDING-005: Identidad independiente

**¿Synap tendrá su propio sistema de identidad?**

| Alternativa | Timeline |
|-------------|----------|
| A: Mantener auth AdministraNET | Indefinido |
| B: Auth Synap + adapter AdministraNET | 12+ meses |
| C: OIDC/SSO externo (Keycloak, etc.) | 6-12 meses |

**Recomendación:** B a largo plazo, A durante transición  
**Impacto:** login/, core/, todos los módulos

---

## ADR-PENDING-006: Producto vs extensión AdministraNET

**¿Synap es producto independiente o extensión AdministraNET?**

| Alternativa | Implicación |
|-------------|-------------|
| A: Extensión AdministraNET | Status quo, menor inversión |
| B: Producto complementario | ACL, branding propio |
| C: Producto independiente (SaaS) | Identity, tenant, billing, multi-ERP |

**Recomendación auditoría:** B→C incremental  
**Impacto:** Estratégico — define todo el roadmap

---

*Generado por auditoría READ ONLY. Requieren decisión humana.*
